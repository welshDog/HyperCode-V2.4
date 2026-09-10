# 🏗️ Studio First Successful Agent Run — Full Report

**Date:** 2026-09-10  
**Run ID:** `cs_7d86f`  
**Surface:** HyperCode IDE Studio (`/ide`)  
**Model:** Sonnet 5 · Balanced (cloud)  
**Verdict:** ✅ **First end-to-end governed Studio run** — stream, diff, and review all populated. **Merge pending** — two code-level findings to resolve first.

---

## 1. Executive Summary

On 2026-09-09/10, the HyperCode IDE Studio completed its first fully successful agent run. Previous sessions on 2026-09-09 saw two consecutive `fetch failed` errors — the run died before the agent stream started (first with a large self-improvement prompt, then with a minimal `/healthz` test prompt, proving the failure was submission-path, not prompt-size).

Run `cs_7d86f` changed that completely:

| Signal | Value |
|---|---|
| Task | Extract retry/backoff logic in the worker into a helper + unit tests |
| Elapsed | 4m 38s |
| Shepherd decisions | 8 ALLOW · 0 WARN · 1 BLOCK |
| Cost | $1.45 |
| Diff size | +284 / −41 across 4 files |
| Outcome | Run complete, diff reviewable, Discard/Merge pending |

This is the first observed run where every part of the Studio loop worked in sequence: task submission → governed sandbox → agent stream → tests executed → diff produced → human review gate.

---

## 2. What the Run Did (Agent Stream)

The stream shows a textbook governed workflow:

1. **Discovery** — `Grep(retry)`, `Read(worker.py)`, `Glob(src/**/*)`, `Glob(**/utils/**)`, `Read(base_agent.py)`
2. **Creation** — `Write(retry_helper.py)` → ALLOW
3. **Refactor** — multiple `Edit(worker.py)` and `Edit(retry_helper.py)` → all ALLOW
4. **Testing** — `Write(test_retry_helper.py)` → ALLOW, then `Bash(cd /workspace && python -m pytest ...)`
5. **Governance event** — `Write(/tmp/summary.md)` → **BLOCK** ("resolves outside the worktree")
6. **Recovery** — agent rewrote the summary inside the worktree (`summary.md`) → ALLOW
7. **Completion** — run complete, cost $1.4492

### Governance verdict

The single BLOCK is the most important line in the stream. The Safety Shepherd stopped an out-of-worktree write, and the agent adapted without breaking the run. This is the Aug-24 lesson (unauthorized scope creep) demonstrably enforced in the UI — **the governance model is not just documented, it's visibly working.**

---

## 3. Diff Review

### 3.1 New: `src/agents/hyper_agents/retry_helper.py` (+85)

Clean extraction of the retry/backoff loop:
- `retry_with_backoff()` — exponential backoff, sync + async support, per-attempt timeout, configurable retry exceptions, optional `on_retry` callback
- `RetryError` — carries `last_exception` + `attempt_index`
- Returns `(result, attempt_index)` on success
- Preserves original worker behaviour (base 2.0, `max_retries` semantics)

### 3.2 New: `src/agents/hyper_agents/tests/test_retry_helper.py` (+110)

Seven pytest cases covering: first-attempt success, success after retries, exhaustion → `RetryError`, `on_retry` callback timing/args, async functions (success + retry), and timeout behaviour.

### 3.3 Modified: `src/agents/hyper_agents/worker.py` (refactor)

`_execute_with_retry()` now delegates the loop to `retry_with_backoff()`, keeping the worker's logging, ND-friendly error formatting, and `TaskResult` population (including `retries_used`). Failure path sets `retries_used=task.max_retries` — matching original semantics.

### 3.4 New: `summary.md` (+45)

Agent-generated run summary. **Not product code.** Recommend discarding from the merge or moving to `docs/`.

---

## 4. Findings (Pre-Merge Review)

### ⚠️ F1 — Double timeout application (HIGH)

The worker passes `timeout=task.timeout` to `retry_with_backoff()`, but `_attempt_task()` **already** wraps async handlers with `asyncio.wait_for(...)`. Async tasks now get timeout applied twice. For sync handlers, only the helper's `wait_for` applies (via `run_in_executor`), so behaviour differs by handler type. **Fix:** remove the inner `asyncio.wait_for` in `_attempt_task()` (or don't pass `timeout` to the helper) so there is exactly one timeout layer.

### ⚠️ F2 — Fragile exception equality assertion (MEDIUM)

In `test_retry_helper.py`:

```python
assert exc_info.value.last_exception == ValueError("always fails")
```

This constructs a new exception object and compares with `==` (identity for most exceptions). It passes only by accident of CPython identity/interning in some paths — the correct pattern is:

```python
assert isinstance(exc_info.value.last_exception, ValueError)
assert str(exc_info.value.last_exception) == "always fails"
```

### ⚠️ F3 — `summary.md` in the merge (LOW)

Run artifact, not code. Exclude from the merge commit.

### ⚠️ F4 — Missing newline at EOF (LOW)

`retry_helper.py` and `test_retry_helper.py` both lack a trailing newline (`\ No newline at end of file`). Most linters flag this; trivial fix.

### ⚠️ F5 — Timeout test is messy (LOW)

`test_retry_with_backoff_timeout` redefines `slow_func` three times with leftover comments about mocking difficulty. It works, but it reads like the agent's own uncertainty — worth tidying when touching the file for F2.

---

## 5. Regression & Behavioural Risk

- **`retry_exceptions=(asyncio.TimeoutError, Exception)`** in the worker call is redundant (`TimeoutError` is an `Exception` subclass) — harmless but noisy.
- **`on_retry` fires before the first sleep** — matches original logging order (log then sleep). ✅ Preserved.
- **`retries_used` semantics** — success path now returns the helper's `attempt_index`; original used the loop counter. Equivalent. ✅
- **Backoff timing** — original: `wait_time = 2 ** attempt` before each retry sleep. Helper: `backoff_base ** attempt` with default 2.0. ✅ Identical.

---

## 6. Studio Product Signals

Beyond this run, the Studio page itself shows progress worth logging:

- **Model picker upgraded** — now grouped: Cloud (Sonnet 5, Opus 4.8, Haiku 4.5, Fable 5) + **Free / Local** group (Nemotron 3 Super 120B, Qwen3 4B) — currently disabled, labelled "needs FCC proxy (coming soon)". Helper text explains Cloud vs Local trade-offs.
- **Run header** — shows run ID, model, elapsed time, Shepherd counts, and live cost. This was the "run metadata bar" improvement called out in the 2026-09-08 UI review — now shipped and populated.
- **The `fetch failed` submission bug is resolved** — same UI, same prompts, runs now go through.

---

## 7. Recommended Actions

1. **Do not merge blind.** Fix F1 (double timeout) and F2 (exception assertion) first — both are small edits.
2. Exclude `summary.md` from the merge (F3).
3. Add trailing newlines (F4) while touching the files.
4. Re-run the retry helper test suite inside the worktree after fixes.
5. Merge via the Studio review gate — this becomes the first merged Studio run and a proven reference workflow.
6. Log the successful BLOCK event as governance evidence (useful for sponsor material).

---

## 8. Scoreboard

| Then (2026-09-09) | Now (2026-09-10) |
|---|---|
| `fetch failed` × 2 — no stream, no diff | Full run: stream + tests + diff + review |
| No governed-run evidence in UI | 1 BLOCK enforced live, agent recovered in-bounds |
| No run metadata | Run header: elapsed, cost, Shepherd counts |
| Claude-only model picker | Free/Local group visible (wiring pending) |
| Studio = promise | Studio = proven loop (pending first merge) |

---

**Report by:** Perplexity (Hyper Merge session)  
**Evidence:** Studio page `/ide` run `cs_7d86f`, 2026-09-10 01:28 BST
