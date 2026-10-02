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
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import redis.asyncio as aioredis

from app.agents.hyperflow.schema import FlowDefinition, FlowNode, NodeType
from app.broski_operator.tools import LOCAL_TOOLS
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

# How often a parked approval gate re-checks Postgres for a decision that was written
# while this process was down (or by another process). Seconds.
APPROVAL_POLL_SECONDS = float(os.getenv("HYPERFLOW_APPROVAL_POLL_SECONDS", "2"))

# In-process registry of live runners so the /resume endpoint can signal a gate.
# MVP runs hypercode-core single-worker; multi-worker resume is future work.
_ACTIVE: dict[str, "HyperFlowRunner"] = {}

_TERMINAL = (
    HyperFlowRunStatus.COMPLETED.value,
    HyperFlowRunStatus.FAILED.value,
    HyperFlowRunStatus.CANCELLED.value,
)


def _strip_data(entry: dict[str, Any]) -> dict[str, Any]:
    """Copy of a history entry without ``result.data``/``result.context``/``result.by`` (operator-API only)."""
    result = entry.get("result")
    if isinstance(result, dict) and ("data" in result or "context" in result or "by" in result):
        return {**entry, "result": {k: v for k, v in result.items() if k not in ("data", "context", "by")}}
    return entry


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


# ── Safety Shepherd integration (P0-2 ↔ P0-1) ─────────────────────────────────
def _safety_mode() -> str:
    """off → never consult · monitor → record decision, always proceed · enforce → gate."""
    return os.getenv("SAFETY_SHEPHERD_MODE", "monitor").strip().lower()


def _safety_url() -> str:
    return os.getenv("SAFETY_SHEPHERD_URL", "http://safety-shepherd:8096").rstrip("/")


def _safety_key() -> str:
    key = settings.API_KEY or os.getenv("API_KEY") or ""
    if key:
        return key
    for path in (os.getenv("API_KEY_FILE"), "/run/secrets/api_key"):
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except OSError:
                pass
    return "dev-master-key"


class HyperFlowRunner:
    def __init__(
        self,
        flow: FlowDefinition,
        run_id: str,
        *,
        user_id: Optional[int] = None,
        history: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self.flow = flow
        self.run_id = run_id
        self.user_id = user_id
        self._history: list[dict[str, Any]] = list(history or [])
        self._approval_event = asyncio.Event()
        self._approval_result: Optional[bool] = None
        self._task: Optional[asyncio.Task] = None
        self._cancel_reason: Optional[str] = None
        self.parked_gate: Optional[str] = None  # node id while parked at a human gate
        self._last_decision_meta: dict[str, Any] = {}  # {"by", "plan_hash"} of the last consumed decision
        self._cache_url = cache_redis_url()

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> "HyperFlowRunner":
        _ACTIVE[self.run_id] = self
        await self._persist(HyperFlowRunStatus.RUNNING, self.flow.entry)
        self._task = asyncio.create_task(self._run())
        return self

    async def start_at(self, node_id: str) -> "HyperFlowRunner":
        """Re-attach to a persisted run (see recovery.recover_runs) and continue from ``node_id``."""
        _ACTIVE[self.run_id] = self
        self._task = asyncio.create_task(self._run(node_id))
        return self

    def resume(self, approved: bool) -> None:
        """Satisfy a pending human_approval_gate (called from the resume endpoint)."""
        self._approval_result = approved
        self._approval_event.set()

    async def cancel(self, reason: str = "cancelled") -> bool:
        """Cancel a live run. Returns False when it is not running in this process."""
        task = self._task
        if task is None or task.done():
            return False
        self._cancel_reason = reason
        task.cancel()
        await asyncio.wait({task}, timeout=5.0)
        return True

    # ── graph walk ───────────────────────────────────────────────────────────

    async def _run(self, start_at: Optional[str] = None) -> None:
        loop_counts: dict[tuple[str, str], int] = {}
        node_id: Optional[str] = start_at or self.flow.entry
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
                if node.type is NodeType.TOOL and node.tool in LOCAL_TOOLS and "data" in result:
                    emit_result["data"] = result["data"]
                if node.type is NodeType.HUMAN_APPROVAL_GATE:
                    for key in ("approved", "by", "plan_hash"):
                        if result.get(key) is not None:
                            emit_result[key] = result[key]
                await self._emit(node, "completed", emit_result, HyperFlowRunStatus.RUNNING)
                node_id = self._next_node(node, success, loop_counts)

            await self._finish(HyperFlowRunStatus.COMPLETED)
        except _FlowFailed as exc:
            await self._finish(HyperFlowRunStatus.FAILED, error=str(exc))
        except asyncio.CancelledError:
            if self._cancel_reason is None:
                # Event-loop shutdown, not an operator cancel: leave the run 'running'
                # so recover_runs() can resume it after the restart.
                raise
            await self._finish(HyperFlowRunStatus.CANCELLED, error=self._cancel_reason)
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
        # P0-2: consult Safety Shepherd before any agent/tool dispatch.
        await self._safety_gate(node)
        if node.type is NodeType.TOOL and node.tool in LOCAL_TOOLS:
            return await self._run_local_tool(node)
        return await self._dispatch(node)

    async def _run_local_tool(self, node: FlowNode) -> dict[str, Any]:
        """Run an in-core tool. No orchestrator hop and no mocked-OK fallback."""
        ctx = {"run_id": self.run_id, "history": list(self._history)}
        if node.params.get("with_arguments"):
            # Read from Postgres (not memory) so a run resumed after a restart still has them.
            ctx["arguments"] = await asyncio.to_thread(self._load_arguments_sync)
        data = await LOCAL_TOOLS[node.tool](node.params, ctx)
        ok = bool(data.get("ok"))
        result: dict[str, Any] = {"ok": ok, "green": ok, "data": data}
        if node.success_key in data:
            # Lets a node's `success_key` (e.g. has_proposal) drive conditional edges.
            result[node.success_key] = data[node.success_key]
        return result

    def _load_arguments_sync(self) -> dict[str, Any]:
        """``state.context.arguments`` written when the operator API started this run."""
        db = SessionLocal()
        try:
            run = db.get(HyperFlowRun, self.run_id)
            ctx = ((run.state or {}).get("context") or {}) if run is not None else {}
            args = ctx.get("arguments")
            return dict(args) if isinstance(args, dict) else {}
        except Exception:  # pragma: no cover — missing arguments fail closed in the tool
            logger.exception("hyperflow %s argument read failed", self.run_id)
            return {}
        finally:
            db.close()

    # ── Safety Shepherd gate ─────────────────────────────────────────────────

    def _safety_request(self, node: FlowNode) -> dict[str, Any]:
        actor = node.agent or node.tool or node.id
        hint = node.safety
        ctx = {"flow": self.flow.name, "run_id": self.run_id, "node": node.id}
        if hint is not None:
            return {
                "agent": actor,
                "category": hint.category,
                "tool": hint.tool,
                "target": hint.target,
                "domain": hint.domain,
                "context": ctx,
            }
        return {"agent": actor, "category": "generic", "tool": None,
                "target": None, "domain": None, "context": ctx}

    async def _safety_evaluate(self, req: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Call Safety Shepherd /evaluate. Returns None if unreachable (fail-open)."""
        try:
            # Short timeout — Safety Shepherd is in the agents profile (up whenever
            # flows meaningfully dispatch); fail-open fast if it is unreachable.
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(
                    f"{_safety_url()}/evaluate",
                    headers={"X-Agent-Key": _safety_key(), "Content-Type": "application/json"},
                    json=req,
                )
            if resp.status_code != 200:
                logger.warning("safety evaluate %s for run %s", resp.status_code, self.run_id)
                return None
            data = resp.json()
            return data if isinstance(data, dict) else None
        except Exception:
            logger.info("safety shepherd unreachable for run %s — failing open", self.run_id)
            return None

    async def _safety_gate(self, node: FlowNode) -> None:
        """ALLOW → proceed · BLOCK → raise · ESCALATE → wait for human approval.

        monitor mode records the decision but always proceeds; off mode skips
        the call entirely; an unreachable Shepherd fails open (records + proceeds).
        """
        mode = _safety_mode()
        if mode == "off":
            return

        data = await self._safety_evaluate(self._safety_request(node))
        if data is None:
            await self._emit(node, "safety_skipped", {"mode": mode}, HyperFlowRunStatus.RUNNING)
            return

        decision = str(data.get("decision", "ALLOW")).upper()
        approval_id = data.get("approval_id")
        await self._emit(
            node, f"safety_{decision.lower()}",
            {"reason": data.get("reason"), "rule": data.get("rule"),
             "approval_id": approval_id, "mode": mode},
            HyperFlowRunStatus.RUNNING,
        )

        if mode == "monitor":
            return  # observe only

        # enforce
        if decision == "ALLOW":
            return
        if decision == "BLOCK":
            raise RuntimeError(f"safety blocked: {data.get('reason')}")
        if decision == "ESCALATE":
            approved = await self._wait_safety_approval(node, approval_id)
            if not approved:
                raise RuntimeError(f"safety escalation denied: {data.get('reason')}")
            return

    async def _wait_safety_approval(
        self,
        node: FlowNode,
        approval_id: Optional[str],
        timeout: Optional[int] = None,
    ) -> bool:
        """Block until a human resolves the Shepherd-raised approval (redis), else deny on timeout."""
        if not approval_id:
            return False
        timeout = timeout or int(os.getenv("SAFETY_APPROVAL_TIMEOUT", "300"))
        await self._persist(HyperFlowRunStatus.AWAITING_APPROVAL, node.id)
        deadline = time.time() + timeout
        approved = False
        try:
            r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
            try:
                while time.time() < deadline:
                    raw = await r.get(f"approval:{approval_id}:response")
                    if raw:
                        approved = str(json.loads(raw).get("status")) == "approved"
                        break
                    await asyncio.sleep(2)
            finally:
                await r.aclose()
        except Exception:
            logger.warning("safety approval wait failed for %s", approval_id, exc_info=True)
        await self._emit(
            node, "safety_resolved",
            {"approved": approved, "approval_id": approval_id},
            HyperFlowRunStatus.RUNNING,
        )
        return approved

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
            # Respect the orchestrator's verdict — it returns HTTP 200 with
            # status:"error" when a downstream agent fails. Don't mask it.
            if data.get("status") == "error":
                raise RuntimeError(f"orchestrator task error: {str(data.get('message'))[:200]}")
            data.setdefault("ok", True)
            return data
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError, httpx.ReadTimeout) as exc:
            # Lean mode — orchestrator not running. Mock a green result so the graph completes.
            logger.info(
                "hyperflow %s node %s: orchestrator unavailable (%s) — mocking OK",
                self.run_id, node.id, exc,
            )
            return {"ok": True, "green": True, "mocked": True}

    def _last_tool_data(self, node_id: str) -> Optional[dict[str, Any]]:
        """`result.data` of the most recent completed entry of ``node_id`` (or None)."""
        for entry in reversed(self._history):
            if entry.get("node") == node_id and entry.get("status") == "completed":
                data = (entry.get("result") or {}).get("data")
                return data if isinstance(data, dict) else None
        return None

    def _take_persisted_decision(self, node_id: Optional[str] = None) -> Optional[bool]:
        """Read and clear ``state.context.pending_decision`` written by the operator API.

        If ``node_id`` is given, the decision must be scoped to that node (stale decisions
        for other nodes are discarded). Decision shape: {"approved": bool, "by": str, "ts": iso, "node": <id>}.
        With ``node_id`` given, a decision whose "node" is missing or different is stale.
        """
        db = SessionLocal()
        try:
            run = db.get(HyperFlowRun, self.run_id, with_for_update=True)
            if run is None:
                return None
            state = dict(run.state or {})
            ctx = dict(state.get("context") or {})
            decision = ctx.pop("pending_decision", None)
            if decision is None:
                return None
            # Guard: decision must be a dict, not malformed data
            if not isinstance(decision, dict):
                state["context"] = ctx
                run.state = state
                db.commit()
                return None
            # Scope to node: if node_id given, a decision naming a different (or no) node is stale
            decision_node = decision.get("node")
            if node_id is not None and decision_node != node_id:
                # Stale decision for a different gate, discard it
                state["context"] = ctx
                run.state = state
                db.commit()
                return None
            state["context"] = ctx
            run.state = state
            db.commit()
            self._last_decision_meta = {
                "by": decision.get("by"),
                "plan_hash": decision.get("plan_hash"),
            }
            return bool(decision.get("approved"))
        except Exception:  # pragma: no cover — a DB blip must not kill the run
            db.rollback()
            logger.exception("hyperflow %s decision read failed", self.run_id)
            return None
        finally:
            db.close()

    async def _await_approval(self, node: FlowNode) -> dict[str, Any]:
        self._approval_event.clear()
        self._approval_result = None
        self._last_decision_meta = {}
        prompt = node.params.get("prompt", f"Approve step '{node.id}'?")
        entry_result: dict[str, Any] = {"prompt": prompt}
        show_from = node.params.get("show_from")
        if show_from:
            shown = self._last_tool_data(str(show_from))
            if shown is not None:
                entry_result["context"] = shown
                plan_hash = (shown.get("proposal") or {}).get("plan_hash")
                if plan_hash:
                    entry_result["plan_hash"] = plan_hash
        await self._emit(node, "awaiting_approval", entry_result,
                         HyperFlowRunStatus.AWAITING_APPROVAL)
        await self._publish_approval_request(node, prompt)
        self.parked_gate = node.id
        try:
            while True:
                # A decision may already be waiting (written while this process was down).
                persisted = await asyncio.to_thread(self._take_persisted_decision, node.id)
                if persisted is not None:
                    self._approval_result = persisted
                    break
                try:
                    await asyncio.wait_for(self._approval_event.wait(), timeout=APPROVAL_POLL_SECONDS)
                except asyncio.TimeoutError:
                    continue
                # Woken by the in-memory resume(): drop any duplicate persisted decision.
                await asyncio.to_thread(self._take_persisted_decision, node.id)
                break
        finally:
            self.parked_gate = None
        if not self._approval_result:
            raise _ApprovalRejected(node.id)
        out: dict[str, Any] = {"ok": True, "approved": True}
        for key in ("by", "plan_hash"):
            if self._last_decision_meta.get(key):
                out[key] = self._last_decision_meta[key]
        return out

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
        entry = {"node": None, "type": "terminal", "status": status.value,
                 "result": {"error": error} if error else {},
                 "ts": datetime.now(timezone.utc).isoformat()}
        self._history.append(entry)
        await self._persist(status, None, completed=True, error=error)
        await self._publish(entry, status)

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
        db = SessionLocal()
        try:
            run = db.get(HyperFlowRun, self.run_id, with_for_update=True)
            if run is not None and run.status in _TERMINAL and status.value not in _TERMINAL:
                db.rollback()  # never un-terminate a row (late write after cancel/finish)
                return
            if run is None:
                state: dict[str, Any] = {"history": self._history}
                if error:
                    state["error"] = error
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
                # Merge: keep everything else in state (e.g. ``context`` written by the
                # operator API) and only refresh history / error.
                state = dict(run.state or {})
                state["history"] = self._history
                if error:
                    state["error"] = error
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
        message = json.dumps({"run_id": self.run_id, "flow": self.flow.name, **_strip_data(entry)})
        snapshot = json.dumps({
            "run_id": self.run_id,
            "flow": self.flow.name,
            "status": run_status.value,
            "current_node": entry.get("node"),
            "history": [_strip_data(e) for e in self._history],
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
