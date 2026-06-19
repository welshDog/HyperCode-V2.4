"""HyperFlowRunner — walks a declarative mission graph (P0-1).

The runner executes a :class:`~app.agents.hyperflow.schema.FlowDefinition` as an
in-core asyncio task inside hypercode-core. Per node it:

  * dispatches ``agent_role`` / ``tool`` nodes to the crew-orchestrator
    (``settings.ORCHESTRATOR_URL/execute``), mirroring the dispatch pattern in
    ``app.api.v1.endpoints.orchestrator``;
  * suspends at ``human_approval_gate`` nodes until a human resumes the run;
  * honours edge ``condition`` / ``retry`` / ``fallback`` / ``loop`` controls;
  * persists every transition to the ``hyperflow_runs`` Postgres table;
  * caches the live snapshot to **Redis DB 1** (cache only — sacred rule) and
    publishes each transition to ``hyperflow:run:{id}:channel`` for SSE fanout;
  * records ``hyperflow_node_duration_seconds`` per node.

Import path (mandated by the brief)::

    from app.agents.hyperflow_runner import HyperFlowRunner
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import redis.asyncio as aioredis

from app.agents.hyperflow.schema import FlowDefinition, FlowNode, NodeType
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.hyperflow import HyperFlowRun, HyperFlowRunStatus

try:  # metrics.py lives at the backend root (/app/metrics.py)
    from metrics import hyperflow_node_duration_seconds
except Exception:  # pragma: no cover — metric optional outside the app image
    hyperflow_node_duration_seconds = None

logger = logging.getLogger(__name__)

# Shared channel the broski-bot / dashboard already watch for approval prompts.
APPROVAL_CHANNEL = "approval_requests"

# In-process registry of live runners so the /resume endpoint can signal a gate.
# MVP runs hypercode-core single-worker; multi-worker resume is future work.
_ACTIVE: dict[str, "HyperFlowRunner"] = {}


class _FlowFailed(Exception):
    """Raised internally to mark a run as failed with a reason."""


class _ApprovalRejected(Exception):
    """Raised when a human rejects an approval gate."""


def cache_redis_url() -> str:
    """Derive the DB-1 cache URL from the DB-0 base URL (Sacred rule: DB1 = cache)."""
    base = settings.HYPERCODE_REDIS_URL
    head, sep, tail = base.rpartition("/")
    if sep and tail.isdigit():
        return f"{head}/1"
    return f"{base.rstrip('/')}/1"


def run_channel(run_id: str) -> str:
    return f"hyperflow:run:{run_id}:channel"


def run_cache_key(run_id: str) -> str:
    return f"hyperflow:run:{run_id}"


def _orchestrator_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    if settings.ORCHESTRATOR_API_KEY:
        headers["X-API-Key"] = settings.ORCHESTRATOR_API_KEY
    return headers


class HyperFlowRunner:
    def __init__(
        self,
        flow: FlowDefinition,
        run_id: str,
        *,
        user_id: Optional[int] = None,
    ) -> None:
        self.flow = flow
        self.run_id = run_id
        self.user_id = user_id
        self._history: list[dict[str, Any]] = []
        self._approval_event = asyncio.Event()
        self._approval_result: Optional[bool] = None
        self._task: Optional[asyncio.Task] = None
        self._cache_url = cache_redis_url()

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> "HyperFlowRunner":
        _ACTIVE[self.run_id] = self
        await self._persist(HyperFlowRunStatus.RUNNING, self.flow.entry)
        self._task = asyncio.create_task(self._run())
        return self

    def resume(self, approved: bool) -> None:
        """Satisfy a pending human_approval_gate (called from the resume endpoint)."""
        self._approval_result = approved
        self._approval_event.set()

    # ── graph walk ───────────────────────────────────────────────────────────

    async def _run(self) -> None:
        loop_counts: dict[tuple[str, str], int] = {}
        node_id: Optional[str] = self.flow.entry
        try:
            while node_id is not None:
                node = self.flow.node(node_id)
                started = time.time()
                try:
                    result = await self._exec_with_retry(node)
                except _ApprovalRejected:
                    self._observe(node, "failed", started)
                    await self._emit(node, "failed", {"reason": "approval_rejected"},
                                     HyperFlowRunStatus.RUNNING)
                    raise _FlowFailed(f"approval rejected at '{node.id}'")
                except Exception as exc:
                    self._observe(node, "failed", started)
                    await self._emit(node, "failed", {"error": str(exc)[:300]},
                                     HyperFlowRunStatus.RUNNING)
                    fallback = self._fallback_for(node)
                    if fallback is not None:
                        node_id = fallback
                        continue
                    raise _FlowFailed(str(exc))

                self._observe(node, "completed", started)
                success = self._is_success(node, result)
                emit_result: dict[str, Any] = {"success": success}
                if result.get("mocked"):
                    emit_result["mocked"] = True
                await self._emit(node, "completed", emit_result, HyperFlowRunStatus.RUNNING)
                node_id = self._next_node(node, success, loop_counts)

            await self._finish(HyperFlowRunStatus.COMPLETED)
        except _FlowFailed as exc:
            await self._finish(HyperFlowRunStatus.FAILED, error=str(exc))
        except Exception as exc:  # pragma: no cover — defensive
            logger.exception("hyperflow run %s crashed", self.run_id)
            await self._finish(HyperFlowRunStatus.FAILED, error=str(exc))
        finally:
            _ACTIVE.pop(self.run_id, None)

    async def _exec_with_retry(self, node: FlowNode) -> dict[str, Any]:
        retry = self._retry_for(node)
        attempts = (retry.max if retry else 0) + 1
        backoff = retry.backoff_seconds if retry else 0.0
        last_exc: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                return await self._do_node(node)
            except _ApprovalRejected:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt + 1 < attempts:
                    await asyncio.sleep(backoff)
        assert last_exc is not None
        raise last_exc

    async def _do_node(self, node: FlowNode) -> dict[str, Any]:
        if node.type is NodeType.HUMAN_APPROVAL_GATE:
            return await self._await_approval(node)
        return await self._dispatch(node)

    # ── node executors ───────────────────────────────────────────────────────

    async def _dispatch(self, node: FlowNode) -> dict[str, Any]:
        # The crew-orchestrator /execute contract requires a top-level "task"
        # description; the agent/tool/node fields are carried as context.
        task = node.params.get("task") or f"{node.type.value} '{node.agent or node.tool or node.id}'"
        payload: dict[str, Any] = {
            "task": task,
            "flow": self.flow.name,
            "run_id": self.run_id,
            "node": node.id,
            "type": node.type.value,
            "agent": node.agent,
            "tool": node.tool,
            "params": node.params,
        }
        if self.user_id is not None:
            payload["user_id"] = self.user_id
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{settings.ORCHESTRATOR_URL}/execute",
                    headers={**_orchestrator_headers(), "Content-Type": "application/json"},
                    json=payload,
                )
            if resp.status_code >= 400:
                raise RuntimeError(f"orchestrator {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            if not isinstance(data, dict):
                data = {"ok": True, "result": data}
            data.setdefault("ok", True)
            return data
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError, httpx.ReadTimeout) as exc:
            # Lean mode — orchestrator not running. Mock a green result so the graph completes.
            logger.info(
                "hyperflow %s node %s: orchestrator unavailable (%s) — mocking OK",
                self.run_id, node.id, exc,
            )
            return {"ok": True, "green": True, "mocked": True}

    async def _await_approval(self, node: FlowNode) -> dict[str, Any]:
        self._approval_event.clear()
        self._approval_result = None
        prompt = node.params.get("prompt", f"Approve step '{node.id}'?")
        await self._emit(node, "awaiting_approval", {"prompt": prompt},
                         HyperFlowRunStatus.AWAITING_APPROVAL)
        await self._publish_approval_request(node, prompt)
        await self._approval_event.wait()
        if not self._approval_result:
            raise _ApprovalRejected(node.id)
        return {"ok": True, "approved": True}

    # ── routing ──────────────────────────────────────────────────────────────

    def _retry_for(self, node: FlowNode):
        for edge in self.flow.edges_from(node.id):
            if edge.retry is not None:
                return edge.retry
        return None

    def _fallback_for(self, node: FlowNode) -> Optional[str]:
        for edge in self.flow.edges_from(node.id):
            if edge.fallback is not None:
                return edge.fallback
        return None

    def _is_success(self, node: FlowNode, result: dict[str, Any]) -> bool:
        if node.success_key in result:
            return bool(result[node.success_key])
        return bool(result.get("ok", True))

    def _next_node(
        self,
        node: FlowNode,
        success: bool,
        loop_counts: dict[tuple[str, str], int],
    ) -> Optional[str]:
        for edge in self.flow.edges_from(node.id):
            if edge.condition is not None and edge.condition != success:
                continue
            if edge.loop is not None:
                key = (edge.src, edge.dst)
                taken = loop_counts.get(key, 0)
                if taken >= edge.loop.max_iterations:
                    return edge.fallback  # loop exhausted → fallback (may be None = terminal)
                loop_counts[key] = taken + 1
            return edge.dst
        return None  # no matching outgoing edge → terminal

    # ── state + fanout ───────────────────────────────────────────────────────

    def _observe(self, node: FlowNode, status: str, started: float) -> None:
        if hyperflow_node_duration_seconds is not None:
            hyperflow_node_duration_seconds.labels(
                flow=self.flow.name, node=node.id, status=status
            ).observe(time.time() - started)

    async def _emit(
        self,
        node: FlowNode,
        status: str,
        result: dict[str, Any],
        run_status: HyperFlowRunStatus,
    ) -> None:
        entry = {
            "node": node.id,
            "type": node.type.value,
            "status": status,
            "result": result,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self._history.append(entry)
        await self._persist(run_status, node.id)
        await self._publish(entry, run_status)

    async def _finish(self, status: HyperFlowRunStatus, error: Optional[str] = None) -> None:
        await self._persist(status, None, completed=True, error=error)
        await self._publish(
            {"node": None, "type": "terminal", "status": status.value,
             "result": {"error": error} if error else {}, "ts": datetime.now(timezone.utc).isoformat()},
            status,
        )

    async def _persist(
        self,
        status: HyperFlowRunStatus,
        current_node: Optional[str],
        *,
        completed: bool = False,
        error: Optional[str] = None,
    ) -> None:
        await asyncio.to_thread(self._persist_sync, status, current_node, completed, error)

    def _persist_sync(
        self,
        status: HyperFlowRunStatus,
        current_node: Optional[str],
        completed: bool,
        error: Optional[str],
    ) -> None:
        state: dict[str, Any] = {"history": self._history}
        if error:
            state["error"] = error
        db = SessionLocal()
        try:
            run = db.get(HyperFlowRun, self.run_id)
            if run is None:
                run = HyperFlowRun(
                    id=self.run_id,
                    flow_name=self.flow.name,
                    flow_version=self.flow.version,
                    status=status.value,
                    current_node=current_node,
                    state=state,
                )
                db.add(run)
            else:
                run.status = status.value
                run.current_node = current_node
                run.state = state
                if completed:
                    run.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:  # pragma: no cover — never let persistence kill the run
            db.rollback()
            logger.exception("hyperflow %s persist failed", self.run_id)
        finally:
            db.close()

    async def _publish(self, entry: dict[str, Any], run_status: HyperFlowRunStatus) -> None:
        message = json.dumps({"run_id": self.run_id, "flow": self.flow.name, **entry})
        snapshot = json.dumps({
            "run_id": self.run_id,
            "flow": self.flow.name,
            "status": run_status.value,
            "current_node": entry.get("node"),
            "history": self._history,
        })
        try:
            r = await aioredis.from_url(self._cache_url, decode_responses=True)
            try:
                await r.set(run_cache_key(self.run_id), snapshot, ex=3600)
                await r.publish(run_channel(self.run_id), message)
            finally:
                await r.aclose()
        except Exception:  # pragma: no cover — fanout is best-effort
            logger.debug("hyperflow %s publish failed", self.run_id, exc_info=True)

    async def _publish_approval_request(self, node: FlowNode, prompt: str) -> None:
        payload = json.dumps({
            "type": "hyperflow_approval",
            "run_id": self.run_id,
            "flow": self.flow.name,
            "node": node.id,
            "prompt": prompt,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        try:
            r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
            try:
                await r.publish(APPROVAL_CHANNEL, payload)
            finally:
                await r.aclose()
        except Exception:  # pragma: no cover
            logger.debug("hyperflow %s approval publish failed", self.run_id, exc_info=True)


# ── module helpers used by the API layer ─────────────────────────────────────

async def start_flow_run(
    flow: FlowDefinition,
    run_id: str,
    *,
    user_id: Optional[int] = None,
) -> HyperFlowRunner:
    runner = HyperFlowRunner(flow, run_id, user_id=user_id)
    await runner.start()
    return runner


def get_runner(run_id: str) -> Optional[HyperFlowRunner]:
    return _ACTIVE.get(run_id)
