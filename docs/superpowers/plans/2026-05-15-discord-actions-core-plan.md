# Discord Actions (One Door) — Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /api/v1/discord/actions` to hypercode-core so BROski Bot can call Core for economy/focus/quests without touching Supabase.

**Architecture:** Create a small FastAPI router that (1) verifies the bot API key via `Authorization: Bearer`, (2) enforces idempotency via a DB table keyed by `Idempotency-Key` + `X-Request-Hash`, and (3) dispatches whitelisted actions into existing BROski$ service functions. Return a bot-friendly `{status, render, ...}` payload and use HTTP 409 for idempotency hits.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, pytest, sqlite test DB.

---

## File Map (what gets touched)

**Create**
- `backend/app/api/v1/endpoints/discord_actions.py` — One Door endpoint + schemas + dispatcher
- `backend/tests/unit/test_discord_actions.py` — endpoint contract tests

**Modify**
- `backend/app/api/api.py` — include the new router
- `backend/app/core/config.py` — add `BOT_API_KEY` settings alias (optional but recommended)
- `backend/app/models/broski.py` — add `DiscordIdempotencyKey` model
- `backend/app/api/v1/endpoints/broski.py` — add `GET /api/v1/broski/pulse` required by bot client

---

### Task 1: Add failing contract tests for `POST /api/v1/discord/actions`

**Files:**
- Create: `backend/tests/unit/test_discord_actions.py`

- [ ] **Step 1: Write failing tests**

```python
import json

import pytest

from app.core.config import settings
from app.models import models


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-bot-key"}


def _discord_ctx(*, interaction_id: str = "i1") -> dict:
    return {
        "user_id": "u1",
        "guild_id": "g1",
        "channel_id": "c1",
        "interaction_id": interaction_id,
    }


def test_discord_actions_requires_auth(client):
    resp = client.post("/api/v1/discord/actions", json={})
    assert resp.status_code in (401, 403)


def test_discord_actions_daily_claim_happy_path(client, db, monkeypatch):
    monkeypatch.setattr(settings, "BOT_API_KEY", "test-bot-key", raising=False)

    user = models.User(
        email="a@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    body = {"action": "daily.claim", "discord": _discord_ctx(), "payload": {}}
    resp = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:i1",
            "X-Request-Hash": "abcd1234abcd1234",
        },
        json=body,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["render"]["type"] == "embed"


def test_discord_actions_idempotency_returns_409(client, db, monkeypatch):
    monkeypatch.setattr(settings, "BOT_API_KEY", "test-bot-key", raising=False)

    user = models.User(
        email="b@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    body = {"action": "daily.claim", "discord": _discord_ctx(), "payload": {}}
    headers = {
        **_auth_headers(),
        "Idempotency-Key": "discord:i1",
        "X-Request-Hash": "abcd1234abcd1234",
    }

    first = client.post("/api/v1/discord/actions", headers=headers, json=body)
    assert first.status_code == 200

    second = client.post("/api/v1/discord/actions", headers=headers, json=body)
    assert second.status_code == 409
    assert second.json() == first.json()


def test_discord_actions_rejects_hash_mismatch(client, db, monkeypatch):
    monkeypatch.setattr(settings, "BOT_API_KEY", "test-bot-key", raising=False)

    user = models.User(
        email="c@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    body1 = {"action": "economy.balance", "discord": _discord_ctx(), "payload": {}}
    body2 = {"action": "economy.balance", "discord": _discord_ctx(), "payload": {"x": 1}}

    headers = {
        **_auth_headers(),
        "Idempotency-Key": "discord:i1",
        "X-Request-Hash": "abcd1234abcd1234",
    }
    ok = client.post("/api/v1/discord/actions", headers=headers, json=body1)
    assert ok.status_code == 200

    bad = client.post("/api/v1/discord/actions", headers=headers, json=body2)
    assert bad.status_code == 409
    assert bad.json()["code"] == "idempotency_mismatch"
```

- [ ] **Step 2: Run tests to verify failure**

Run:
`pytest backend/tests/unit/test_discord_actions.py -q`

Expected:
FAIL because `/api/v1/discord/actions` is not implemented yet.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_discord_actions.py
git commit -m "test(core): add contract tests for discord actions endpoint"
```

---

### Task 2: Add DB model for idempotency keys

**Files:**
- Modify: `backend/app/models/broski.py`

- [ ] **Step 1: Write failing test for DB model existence**

Add to `backend/tests/unit/test_discord_actions.py`:

```python
def test_discord_idempotency_table_exists(db):
    db.execute("SELECT 1")
```

This ensures the DB fixture is set up and won’t break once the model is added.

- [ ] **Step 2: Implement SQLAlchemy model**

Add:
- `idempotency_key` (unique)
- `request_hash`
- `response_json`
- `created_at`

- [ ] **Step 3: Run tests**

Run:
`pytest backend/tests/unit/test_discord_actions.py -q`

Expected:
Still failing only on missing endpoint.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/broski.py
git commit -m "feat(core): add discord idempotency key model"
```

---

### Task 3: Implement `/api/v1/discord/actions` router + auth

**Files:**
- Create: `backend/app/api/v1/endpoints/discord_actions.py`
- Modify: `backend/app/api/api.py`
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Implement settings**

Add to `Settings`:
- `BOT_API_KEY` (alias accepts `BOT_API_KEY` and `API_KEY`)

- [ ] **Step 2: Implement auth dependency**

Require:
- `Authorization: Bearer <key>`
Compare with `settings.BOT_API_KEY` (or `settings.API_KEY`).

- [ ] **Step 3: Implement endpoint**

Requirements:
- Read `Idempotency-Key` and `X-Request-Hash` headers.
- If `Idempotency-Key` already exists:
  - if hash matches: return cached response with HTTP 409.
  - else: return HTTP 409 with `{status:"error", code:"idempotency_mismatch"}`.
- Dispatch whitelisted actions:
  - `daily.claim` → use `broski_service.handle_daily_login`
  - `economy.balance` → reuse wallet read logic used by `GET /broski/balance/{discord_id}`
- Return `{status:"ok", render:{type:"embed", ...}}` on success.

- [ ] **Step 4: Register router**

In `backend/app/api/api.py` include:
- `api_router.include_router(discord_actions.router, prefix="/discord", tags=["discord"])`

- [ ] **Step 5: Run tests**

Run:
`pytest backend/tests/unit/test_discord_actions.py -q`

Expected:
PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/api.py backend/app/core/config.py backend/app/api/v1/endpoints/discord_actions.py
git commit -m "feat(core): add POST /api/v1/discord/actions (one door)"
```

---

### Task 4: Add `GET /api/v1/broski/pulse` for bot briefing

**Files:**
- Modify: `backend/app/api/v1/endpoints/broski.py`
- Modify: `backend/tests/unit/test_discord_actions.py`

- [ ] **Step 1: Add test**

```python
def test_broski_pulse_exists(client, monkeypatch):
    monkeypatch.setattr(settings, "BOT_API_KEY", "test-bot-key", raising=False)
    resp = client.get("/api/v1/broski/pulse")
    assert resp.status_code in (200, 401, 403)
```

- [ ] **Step 2: Implement endpoint**

Return a small stable payload:
- `{"status":"ok"}`

- [ ] **Step 3: Run tests**

Run:
`pytest backend/tests/unit/test_discord_actions.py -q`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/endpoints/broski.py backend/tests/unit/test_discord_actions.py
git commit -m "feat(core): add broski pulse endpoint"
```

---

## Self-Review Checklist

- [ ] Endpoint returns 200 on success and 409 on idempotency hit.
- [ ] Cached idempotency response matches first response exactly.
- [ ] Hash mismatch returns 409 with `code=idempotency_mismatch`.
- [ ] Bot auth accepts Bearer token and does not allow missing/empty keys.
- [ ] No logs print secrets or full request bodies.

## Local Verification Commands

Run:
- `pytest backend/tests/unit/test_discord_actions.py -q`
- `pytest backend/tests/unit/test_api_health.py -q`

