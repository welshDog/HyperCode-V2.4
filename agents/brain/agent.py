"""
Brain Agent for HyperCode V2.4
Swarm memory: semantic recall + storage over ChromaDB. Other agents' completed
tasks get stored here as they happen; future tasks can query this agent for
relevant prior context before acting. Responses respect ADHD_MODE/DYSLEXIA_MODE
(short, chunked, bulleted output) when either is set.

Not the same thing as hyper-brain (docker-compose.brain.yml) — that's the
Obsidian-vault knowledge system. This is the crew-orchestrator-integrated
short-term/working memory for the agent swarm itself, backed by the `chroma`
service already provisioned in docker-compose.observability.yml.
"""
import os
import sys
from typing import Any, Dict

sys.path.append("/app")
from base_agent import BaseAgent, AgentConfig


class BrainAgent(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.role = "Swarm Memory"
        self._chroma_host = os.getenv("CHROMA_HOST", "chroma")
        self._chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
        self._adhd_mode = os.getenv("ADHD_MODE", "false").lower() == "true"
        self._dyslexia_mode = os.getenv("DYSLEXIA_MODE", "false").lower() == "true"
        self._collection_name = "hypercode_swarm_memory"
        self._chroma_client = None
        self._collection = None

    def build_system_prompt(self) -> str:
        style_rules = ""
        if self._adhd_mode or self._dyslexia_mode:
            style_rules = """
STYLE (ADHD_MODE/DYSLEXIA_MODE active):
- Short sentences, bullet points, no walls of text.
- Bold the key term in each bullet.
- Chunk output into small sections with clear headers.
"""
        return f"""You are {self.config.name} ({self.config.role}) in the HyperCode agent swarm.

RESPONSIBILITIES:
- Recall relevant prior swarm activity (from the MEMORY SNAPSHOT below) when answering
- Never invent memory that isn't in the snapshot — say "no relevant memory found" if empty
- Keep answers grounded and short
{style_rules}"""

    async def process_task(self, task: str, context: Dict[str, Any], requires_approval: bool = False) -> Any:
        memory_snapshot = await self._recall(task)

        system = self.build_system_prompt()
        user = f"""TASK:
{task}

CONTEXT:
{context or {}}

MEMORY SNAPSHOT (semantic recall, may be empty):
{memory_snapshot}
"""
        response = await self._llm_text(system=system, user=user)
        await self._remember(task, response)
        return response

    async def _get_collection(self):
        if self._collection is not None:
            return self._collection
        try:
            import asyncio
            import chromadb
            from chromadb.utils import embedding_functions

            def _connect():
                client = chromadb.HttpClient(host=self._chroma_host, port=self._chroma_port)
                collection = client.get_or_create_collection(
                    name=self._collection_name,
                    embedding_function=embedding_functions.DefaultEmbeddingFunction(),
                    metadata={"hnsw:space": "cosine"},
                )
                return client, collection

            self._chroma_client, self._collection = await asyncio.to_thread(_connect)
        except Exception as exc:
            self.logger.warning("chroma_connect_failed", error=str(exc))
            self._collection = None
        return self._collection

    async def _recall(self, task: str, n_results: int = 5) -> str:
        """Read-only semantic search over prior swarm activity. Never raises."""
        collection = await self._get_collection()
        if collection is None:
            return "Chroma unavailable — no memory recall possible for this request."
        try:
            import asyncio

            def _query():
                return collection.query(query_texts=[task], n_results=n_results)

            results = await asyncio.to_thread(_query)
            documents = results.get("documents", [[]])[0] if results.get("documents") else []
            if not documents:
                return "No relevant memory found."
            return "\n".join(f"- {doc}" for doc in documents)
        except Exception as exc:
            self.logger.warning("chroma_query_failed", error=str(exc))
            return "Memory recall failed — proceeding without it."

    async def _remember(self, task: str, response: str) -> None:
        """Store this task+response pair as new memory. Best-effort, never raises."""
        collection = await self._get_collection()
        if collection is None:
            return
        try:
            import asyncio
            import uuid

            entry = f"TASK: {task}\nRESPONSE: {response}"
            doc_id = f"{self.config.name}_{uuid.uuid4().hex[:12]}"

            def _add():
                collection.add(documents=[entry], metadatas=[{"source": self.config.name}], ids=[doc_id])

            await asyncio.to_thread(_add)
        except Exception as exc:
            self.logger.warning("chroma_ingest_failed", error=str(exc))


if __name__ == "__main__":
    config = AgentConfig()
    # Override defaults for this specific agent — port comes from AGENT_PORT,
    # baked into the Dockerfile as 8080 to match agents-full.yml's healthcheck.
    config.name = os.getenv("AGENT_NAME", "brain-agent")
    config.role = os.getenv("AGENT_ROLE", "Swarm Memory")

    agent = BrainAgent(config)
    agent.run()
