# pylint: disable=import-error, no-name-in-module, broad-exception-caught, logging-fstring-interpolation
# pyright: reportMissingImports=false
import logging
import httpx  # type: ignore
from app.core.config import settings  # type: ignore
from app.llm.ollama import OllamaModelResolver  # type: ignore
from app.core.model_routes import ModelRouteContext, openrouter_chat, select_model_route  # type: ignore

logger = logging.getLogger(__name__)


class Brain:
    """
    The cognitive core of the HyperCode agent system.
    Powered by Perplexity AI (Sonar Pro) with fallback to Ollama + OpenRouter.

    Memory modes (inter-agent memory — Phase 1):
      none   — stateless, no memory read/write (default, backward-compatible)
      self   — reads + writes own conversation history only
      shared — reads handoff inbox + own history; writes both
    """

    def __init__(self):
        self.api_key = settings.PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar-pro"
        preferred_patterns = [p.strip() for p in settings.OLLAMA_MODEL_PREFERRED.split(",") if p.strip()]
        self._ollama_model_resolver = OllamaModelResolver(
            ollama_host=settings.OLLAMA_HOST,
            preferred_patterns=preferred_patterns,
            max_size_mb=settings.OLLAMA_MAX_MODEL_SIZE_MB,
            refresh_seconds=settings.OLLAMA_MODEL_REFRESH_SECONDS,
        )

    # ------------------------------------------------------------------
    # Memory helpers
    # ------------------------------------------------------------------

    async def recall_context(self, query: str = None, limit: int = 5) -> str:
        """
        Retrieves context using Vector Search (RAG) if available,
        falling back to recent files.
        """
        context = []

        # 1. Try Vector Search (Semantic)
        try:
            from app.core.rag import rag  # type: ignore
            if query:
                # Privacy-first: never log raw user prompts/queries.
                logger.info("[BRAIN] Semantic searching (chars=%s, limit=%s)", len(query), limit)
                rag_results = rag.query(query, n_results=limit)
                if rag_results:
                    context.append("--- Semantic Memory (RAG) ---")
                    context.extend(rag_results)
                    return "\n\n".join(context)
        except Exception as e:
            logger.warning(f"[BRAIN] RAG search failed: {e}")

        # 2. Fallback to Recent Files (Temporal)
        # Privacy-first: do not pull arbitrary bucket content into prompts by default.
        # If file-based recall is desired, it must be explicitly enabled.
        if not getattr(settings, "BRAIN_ALLOW_FILE_FALLBACK", False):
            return ""

        try:
            from app.core.storage import get_storage  # type: ignore

            storage = get_storage()
            file_keys = storage.list_files(limit=max(1, int(limit)))
            if not file_keys:
                return ""

            context.append("--- Recent Files ---")
            for key in file_keys[: max(1, int(limit))]:
                context.append(f"Recent File: {key}")
                content = storage.get_file_content(key)
                if content:
                    # Hard-cap so we don't accidentally inject huge documents.
                    context.append(content[:2000])

            return "\n\n".join(context).strip()
        except Exception as e:
            logger.warning(f"[BRAIN] File fallback failed: {e}")
            return ""

    def _build_memory_context(
        self,
        conversation_id: str | None,
        agent_id: str,
        memory_mode: str,
        rag_context: str,
    ) -> str:
        """
        Assembles injected memory block in the correct order:
          1. Handoff inbox  (if shared mode)
          2. RAG snippets   (if available)
          3. Conversation history (if self or shared mode)

        Hard-capped to avoid prompt token overflow.
        Fails closed: if anything errors, returns empty string.
        """
        MAX_HANDOFF_CHARS = 1_500
        MAX_RAG_CHARS = 2_000
        MAX_HISTORY_CHARS = 2_000

        if memory_mode == "none" or not conversation_id:
            return rag_context  # preserve existing RAG behaviour

        try:
            from app.core.agent_memory import read_handoffs, get_history  # type: ignore
            blocks: list[str] = []

            # 1. Handoff inbox
            if memory_mode == "shared":
                handoffs = read_handoffs(agent_id, limit=5, consume=False)
                if handoffs:
                    handoff_text = "\n".join(
                        f"- [{h['from_agent_id']}] {h['summary']}" for h in handoffs
                    )
                    handoff_text = handoff_text[:MAX_HANDOFF_CHARS]
                    blocks.append(f"--- Handoff Notes for {agent_id} ---\n{handoff_text}")

            # 2. RAG snippets (pass-through from caller)
            if rag_context:
                blocks.append(rag_context[:MAX_RAG_CHARS])

            # 3. Conversation history
            history = get_history(conversation_id, last_n=10)
            if history:
                history_lines = []
                for turn in history:
                    line = f"[{turn['agent_id']}|{turn['role']}] {turn['content']}"
                    history_lines.append(line)
                history_text = "\n".join(history_lines)[:MAX_HISTORY_CHARS]
                blocks.append(f"--- Conversation History ---\n{history_text}")

            return "\n\n".join(blocks)

        except Exception as exc:
            logger.warning(f"[BRAIN] _build_memory_context failed (failing closed): {exc}")
            return rag_context  # fall back to RAG only, never crash

    # ------------------------------------------------------------------
    # Core think() — stateful + backward-compatible
    # ------------------------------------------------------------------

    async def think(
        self,
        role: str,
        task_description: str,
        use_memory: bool = False,
        route_context: dict | None = None,
        # --- Phase 1: inter-agent memory ---
        conversation_id: str | None = None,
        agent_id: str = "brain",
        memory_mode: str = "none",  # none | self | shared
    ) -> str:
        """
        Process a task description and return a plan or code.

        Supports:
          1. Local LLM (Ollama)                    — Zero Cost
          2. Perplexity Session Auth (Comet/Spaces) — Zero Cost
          3. Cloud API (Perplexity/PERPLEXITY)       — Paid Fallback

        Memory modes (new — Phase 1):
          none   — stateless, original behaviour (default)
          self   — reads + writes conversation history
          shared — reads handoffs + history; writes both
        """
        # Privacy-first: never log raw prompts/task descriptions (may contain secrets or personal data).
        conv_hint = (conversation_id[:8] + "…") if conversation_id else None
        logger.info(
            "[BRAIN] think(role=%s, prompt_chars=%s, use_memory=%s, memory_mode=%s, conversation_id=%s)",
            role,
            len(task_description or ""),
            use_memory,
            memory_mode,
            conv_hint,
        )

        # ------------------------------------------------------------------
        # 1. Recall long-term context (existing RAG / file fallback)
        # ------------------------------------------------------------------
        rag_context = ""
        if use_memory:
            logger.info("[BRAIN] Accessing Long-Term Memory...")
            rag_context = await self.recall_context(query=task_description)

        # ------------------------------------------------------------------
        # 2. Build injected memory block (new Phase 1 — fails closed)
        # ------------------------------------------------------------------
        memory_block = self._build_memory_context(
            conversation_id=conversation_id,
            agent_id=agent_id,
            memory_mode=memory_mode,
            rag_context=rag_context,
        )

        # ------------------------------------------------------------------
        # 3. Compose final prompt
        # ------------------------------------------------------------------
        if memory_block:
            full_prompt = f"Context:\n{memory_block}\n\nTask: {task_description}"
        else:
            full_prompt = task_description

        # ------------------------------------------------------------------
        # 4. Persist the user turn BEFORE we call the LLM
        #    (so history is consistent even if LLM errors)
        # ------------------------------------------------------------------
        if memory_mode != "none" and conversation_id:
            try:
                from app.core.agent_memory import append_turn  # type: ignore
                append_turn(
                    conversation_id=conversation_id,
                    agent_id=agent_id,
                    role="user",
                    content=task_description,
                )
            except Exception as exc:
                logger.warning(f"[BRAIN] Failed to persist user turn: {exc}")

        # ------------------------------------------------------------------
        # 5. LLM routing (unchanged from original)
        # ------------------------------------------------------------------
        result = await self._route_llm(role=role, prompt=full_prompt, route_context=route_context)

        # ------------------------------------------------------------------
        # 6. Persist assistant response turn
        # ------------------------------------------------------------------
        if memory_mode != "none" and conversation_id:
            try:
                from app.core.agent_memory import append_turn  # type: ignore
                append_turn(
                    conversation_id=conversation_id,
                    agent_id=agent_id,
                    role="assistant",
                    content=result,
                )
            except Exception as exc:
                logger.warning(f"[BRAIN] Failed to persist assistant turn: {exc}")

        return result

    # ------------------------------------------------------------------
    # LLM routing — extracted so think() stays readable
    # ------------------------------------------------------------------

    def validate_perplexity_key(self, api_key: str | None) -> bool:
        """Validate the format of the Perplexity API key."""
        if not api_key:
            return False
        if not api_key.startswith('pplx-'):
            logger.warning("[BRAIN] Invalid Perplexity API key format: must start with 'pplx-'")
            return False
        if len(api_key) <= 20:
            logger.warning("[BRAIN] Invalid Perplexity API key format: key is too short")
            return False
        return True

    async def _route_llm(
        self,
        role: str,
        prompt: str,
        route_context: dict | None = None,
    ) -> str:
        """Try Perplexity API (if key) → Ollama → Perplexity Session → OpenRouter."""

        # 1. Perplexity API (primary if key exists)
        if self.validate_perplexity_key(self.api_key):
            logger.info("[BRAIN] Routing to Perplexity API...")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a {role}. Provide a detailed, step-by-step plan or code solution.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            }
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        body_preview = (response.text or "")[:300]
                        logger.error(
                            "[BRAIN] Perplexity API error: status=%s body=%s… Falling back.",
                            response.status_code,
                            body_preview,
                        )
            except Exception as e:
                logger.error(f"[BRAIN] Perplexity API exception: {e}. Falling back...")

        # 2. Local LLM (Ollama)
        if settings.OLLAMA_HOST:
            try:
                system_prompt = (
                    f"You are a {role}.\n"
                    "Always respond in two phases:\n"
                    "1) TL;DR (1-3 lines)\n"
                    "2) Details (headings + bullets)\n"
                    "Break work into micro-tasks and propose the next single step.\n\n"
                    f"Task:\n{prompt}"
                )
                async with httpx.AsyncClient(timeout=120.0) as client:
                    model = settings.DEFAULT_LLM_MODEL
                    if model.strip().lower() == "auto":
                        resolved = await self._ollama_model_resolver.resolve(client)
                        if resolved:
                            model = resolved
                    logger.info(f"[BRAIN] Routing to Local LLM (Ollama: {model})...")
                    response = await client.post(
                        f"{settings.OLLAMA_HOST}/api/generate",
                        json={
                            "model": model,
                            "prompt": system_prompt,
                            "stream": False,
                            "options": settings.ollama_generate_options(),
                        }
                    )
                    if response.status_code == 200:
                        return response.json()["response"]
                    logger.warning(f"[BRAIN] Local LLM failed ({response.status_code}), falling back...")
            except Exception as e:
                logger.warning(f"[BRAIN] Local LLM error: {e}. Falling back...")

        # 3. Perplexity Session Auth (Comet/Spaces)
        if settings.PERPLEXITY_SESSION_AUTH:
            logger.info("[BRAIN] Using Perplexity Session Auth (Simulated)...")
            return "Perplexity Session Auth is active. (Simulated Response)"

        # 4. OpenRouter fallback
        if route_context is not None and settings.OPENROUTER_API_KEY:
            try:
                ctx = ModelRouteContext(**route_context)
            except TypeError:
                ctx = ModelRouteContext(kind=str(route_context.get("kind", "general")))
            route = select_model_route(ctx, settings)
            if route is not None:
                try:
                    return await openrouter_chat(
                        base_url=route.base_url,
                        api_key=settings.OPENROUTER_API_KEY,
                        model=route.model,
                        max_tokens=route.max_tokens,
                        privacy_mode=route.privacy_mode,
                        messages=[
                            {"role": "system", "content": f"You are a {role}."},
                            {"role": "user", "content": prompt},
                        ],
                    )
                except Exception as e:
                    logger.warning(f"[BRAIN] OpenRouter route {route.name} failed: {e}. Falling back...")

        return "Error: No valid LLM provider available (Perplexity API, Local, Session, or OpenRouter)."


# Global instance
brain = Brain()
