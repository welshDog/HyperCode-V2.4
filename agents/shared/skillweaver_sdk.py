"""
SkillWeaver Agent SDK
====================

Easy integration for agents to use SkillWeaver.

FastAPI server runs on the `agents-net` Docker network at `http://skillweaver:8051`.
Agents should import this via the shared mount at `/app/shared/skillweaver_sdk.py`.

Usage:
    from shared.skillweaver_sdk import SkillWeaverClient, register_agent_skills

    client = SkillWeaverClient("http://skillweaver:8051")

    # Register skills on startup (one RTT via /register_batch)
    await register_agent_skills(client, "my-agent", [
        {
            "skill_id": "task_execution",
            "name": "Execute Core Tasks",
            "description": "Execute core backend tasks end-to-end",
            "category": "orchestration",
            "inputs": {"task": "str"},
            "outputs": {"result": "dict"},
            "timeout_seconds": 60,
            "examples": ["build a /users endpoint"],
            "version": "1.0.0",
        },
    ])

    # Discover skills when handling novel tasks
    matches = await client.discover_skills("optimize costs")

    # Compose them
    composite = await client.compose_skills([m["skill_id"] for m in matches])

    # On agent shutdown (best effort, ignores failures):
    await client.deregister_agent("my-agent")
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx


class SkillWeaverClient:
    """Async client for interacting with the SkillWeaver server."""

    def __init__(
        self,
        base_url: str = "http://skillweaver:8051",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------ basic

    async def health(self) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    async def root(self) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(self.base_url + "/")
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------- register

    async def register_skill(
        self,
        *,
        skill_id: str,
        agent_id: str,
        name: str,
        description: str,
        category: str,
        inputs: Dict[str, str],
        outputs: Dict[str, str],
        timeout_seconds: float = 30.0,
        examples: Optional[List[str]] = None,
        version: str = "1.0.0",
    ) -> Dict[str, Any]:
        """Register a single skill. Prefer :meth:`register_skill_batch` when
        registering more than one skill so we only pay one RTT."""
        client = await self._get_client()
        payload: Dict[str, Any] = {
            "skill_id": skill_id,
            "agent_id": agent_id,
            "name": name,
            "description": description,
            "category": category,
            "inputs": inputs,
            "outputs": outputs,
            "timeout_seconds": timeout_seconds,
            "examples": examples or [],
            "version": version,
        }
        resp = await client.post(
            f"{self.base_url}/api/v1/skills/register", json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    async def register_skill_batch(
        self,
        *,
        skills: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Register many skills in one RTT via the batch endpoint.

        ``skills`` is a list of dicts — same shape as the kwargs to
        :meth:`register_skill` (skill_id/agent_id/name/description/category
        /inputs/outputs + optional timeout_seconds/examples/version). The
        agent_id field is required on each skill row individually so one
        batch *could* span multiple agents if that's ever useful.

        Returns the server's per-skill results array so callers can tell
        which rows were fresh vs. replaced a previous version.
        """
        if not skills:
            return {"status": "completed", "registered": 0, "total": 0, "results": []}
        client = await self._get_client()
        resp = await client.post(
            f"{self.base_url}/api/v1/skills/register_batch",
            json={"skills": skills},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_skill(self, skill_id: str) -> Dict[str, Any]:
        """Fetch a single registered skill by id (404 if missing)."""
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/api/v1/skills/{skill_id}")
        resp.raise_for_status()
        return resp.json()

    async def deregister_agent(self, agent_id: str) -> Dict[str, Any]:
        """Best-effort shutdown hook: remove every skill registered by
        ``agent_id``. Idempotent — returns ``removed=0`` for unknown agents
        instead of raising."""
        client = await self._get_client()
        resp = await client.delete(
            f"{self.base_url}/api/v1/skills/agent/{agent_id}",
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------- discover

    async def discover_skills(
        self,
        query: str,
        *,
        category: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        payload = {"query": query, "category": category, "top_k": top_k}
        resp = await client.post(
            f"{self.base_url}/api/v1/skills/discover", json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------- compose

    async def compose_skills(
        self,
        skill_ids: List[str],
        strategy: str = "linear",
    ) -> Dict[str, Any]:
        client = await self._get_client()
        payload = {"skill_ids": skill_ids, "strategy": strategy}
        resp = await client.post(
            f"{self.base_url}/api/v1/skills/compose", json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    async def list_skills(
        self,
        agent_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        params: Dict[str, Any] = {}
        if agent_id:
            params["agent_id"] = agent_id
        if category:
            params["category"] = category
        resp = await client.get(f"{self.base_url}/api/v1/skills/list", params=params)
        resp.raise_for_status()
        return resp.json()

    async def composition_history(self, limit: int = 10) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(
            f"{self.base_url}/api/v1/compositions/history",
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json()

    async def stats(self) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/api/v1/stats")
        resp.raise_for_status()
        return resp.json()


async def register_agent_skills(
    client: SkillWeaverClient,
    agent_id: str,
    skills: List[Dict[str, Any]],
    *,
    best_effort: bool = True,
) -> List[str]:
    """Register all skills for ``agent_id`` in one RTT.

    Each entry in ``skills`` is a dict with keys:

    - ``skill_id``, ``name``, ``description``, ``category``, ``inputs``,
      ``outputs`` — required.
    - ``timeout_seconds``, ``examples``, ``version`` — optional, with
      sensible defaults when omitted.

    ``agent_id`` is injected on every row so callers don't need to repeat
    it. Duplicate registration is harmless (SkillWeaver returns
    ``replaced_previous_version: true`` and the Redis sets dedupe
    naturally). Returns the list of skill_ids that were successfully
    registered.

    With ``best_effort=True`` (the default) any failure on the server
    side is logged to stdout and swallowed. For the startup path this is
    the right trade-off — an unavailable SkillWeaver shouldn't prevent
    the agent from booting. Set ``best_effort=False`` when the caller
    wants full visibility into failures.
    """
    if not skills:
        return []

    enriched: List[Dict[str, Any]] = []
    for row in skills:
        entry: Dict[str, Any] = dict(row)
        entry.setdefault("agent_id", agent_id)
        entry.setdefault("timeout_seconds", 30.0)
        entry.setdefault("examples", [])
        entry.setdefault("version", "1.0.0")
        enriched.append(entry)

    try:
        result = await client.register_skill_batch(skills=enriched)
    except Exception as exc:
        if best_effort:
            print(f"[skillweaver_sdk] register_agent_skills failed "
                  f"(best-effort, swallowing): {exc!r}")
            return []
        raise

    results = result.get("results", []) if isinstance(result, dict) else []
    registered_ids: List[str] = [
        r["skill_id"]
        for r in results
        if isinstance(r, dict) and r.get("registered")
    ]
    print(f"[skillweaver_sdk] agent={agent_id!r} registered "
          f"{len(registered_ids)}/{len(skills)} skills via batch")
    return registered_ids


async def discover_and_compose(
    client: SkillWeaverClient,
    query: str,
    *,
    top_k: int = 3,
    category: Optional[str] = None,
    strategy: str = "linear",
) -> Optional[str]:
    """Discover the top ``top_k`` relevant skills and compose them.

    Returns the composite_id on success, or ``None`` if no skills matched
    or the composition step raised. Writes progress to stdout.
    """
    matches = await client.discover_skills(query, top_k=top_k, category=category)
    if not matches:
        print(f"[skillweaver_sdk] No skills matched query={query!r}")
        return None

    print(f"[skillweaver_sdk] Matched {len(matches)} skills for {query!r}:")
    for m in matches:
        print(f"   - {m.get('name')} "
              f"(score={m.get('relevance_score', 0):.2f}, id={m.get('skill_id')})")

    skill_ids = [m["skill_id"] for m in matches[:top_k]]
    try:
        composite = await client.compose_skills(skill_ids, strategy=strategy)
    except Exception as exc:
        print(f"[skillweaver_sdk] Compose failed: {exc!r}")
        return None

    composite_id = composite.get("composite_id")
    print(f"[skillweaver_sdk] Composed -> {composite_id}")
    return composite_id


__all__ = [
    "SkillWeaverClient",
    "register_agent_skills",
    "discover_and_compose",
]
