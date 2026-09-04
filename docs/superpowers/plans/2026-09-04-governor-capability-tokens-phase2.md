# Governor + Capability Tokens (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `governor` service — the governance-plane nucleus that mints signed, scope-bound capability tokens — and make `fleet-controller` require one, while `execution.performed` stays structurally `false`.

**Architecture:** New boring daemon `agents/governor/`, containment-minimal (no Docker socket, no `DOCKER_HOST`, no crew credential, no LLM SDK). It calls Safety Shepherd for a structured verdict, applies a fixed `(mode × decision × kill-switch)` transition table, and — only if the table permits AND the kill-switch is clear AND approvals are satisfied AND the system lease is valid — mints a PASETO v4.public (Ed25519) token bound to the plan hash. Governance state lives in the existing append-only Governance Ledger plus a dedicated Redis logical DB (Approach B — no new datastore). `fleet-controller` gains an offline public-key verification step.

**Tech Stack:** Python 3.11, FastAPI, `pyseto` (PASETO v4.public / Ed25519), `cryptography` (keygen), `redis.asyncio`, `httpx`, pytest + pytest-asyncio + fakeredis. Docker Compose (`--profile fleet`), Docker secrets.

**Spec:** `docs/superpowers/specs/2026-09-04-autonomous-control-plane-north-star-design.md` (§4 capability format, §5 Governor, §7 transition table, §9 Phase 2 cut line, §11 rollout order)

## Global Constraints

- Python indent: **4 spaces**, never 3, never mixed (`.pylintrc` enforces).
- Imports inside agent code: relative to the agent dir (`from models import X`), matching `fleet-controller`. Agents share code by **file-copy**, never cross-agent package import.
- `.env` files and `secrets/*.txt` are **never committed**. The Ed25519 private key is a Docker secret; only the **public** key PEM is committed.
- Redis DB convention (Sacred Rule): DB 1 = cache, DB 2 = rate limits — never reuse. Governor uses **DB 3**.
- `execution.performed` in every `fleet-controller` response this phase can produce is **`false`**. No Docker client, no execution code path is added anywhere.
- Fail-closed everywhere in the governance path: any dependency unreachable / malformed / ambiguous ⇒ deny (no mint) and, for the kill-switch, treat as ON.
- `git fetch` before any push. Nothing is done until committed. Do **not** push unless the human asks.
- Agent test suites run **standalone** from the agent directory (`cd agents/<name> && python -m pytest tests -q`); pytest discovers the repo-root `pyproject.toml` (`asyncio_mode = "auto"`). Do not add agent dirs to root `testpaths`.
- New service port: **`governor` → :8089** (confirmed free across `docker-compose*.yml` 2026-09-04; fall back to `:8085` if a collision appears). `fleet-controller` keeps its documented **:8094** (the `:8094` in `docker-compose.hyper-agents.yml` is `hypervisor-agent` in a separate, non-co-launched file — pre-existing, out of scope).
- Commit message trailer on every commit:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_011eWxNpGJQgxEJK63UtQZU3
  ```

---

## File Structure

**Create — `agents/governor/`:**

| File | Responsibility |
|---|---|
| `Dockerfile` | 2-stage build, mirrors `agents/fleet-controller/Dockerfile` |
| `requirements.txt` | `fastapi`, `uvicorn[standard]`, `pydantic`, `httpx`, `pyseto`, `redis` |
| `main.py` | FastAPI app, lifespan, all `/v1/*` + `/health` endpoints |
| `models.py` | pydantic request/response models |
| `keys.py` | load Ed25519 private key (secret file / env), expose public PEM |
| `capability.py` | mint + offline-verify a PASETO v4.public capability |
| `transitions.py` | the fixed `(mode, decision, kill_switch)` → outcome table |
| `shepherd_client.py` | fail-closed structured-verdict client for Shepherd `/evaluate` |
| `redis_state.py` | jti replay set, revocation set (Redis DB 3) |
| `killswitch.py` | Redis flag OR sentinel file ⇒ killed; unreachable ⇒ killed |
| `lease.py` | system-lease record + `is_valid()` + one renew tick |
| `approvals.py` | approval records + two-person rule enforcement |
| `ledger_client.py` | fire-and-forget Governance Ledger writes (mirrors fleet-controller's) |
| `governor_public_key.pem` | committed Ed25519 public key (verifiers copy this) |
| `tests/conftest.py` + `tests/test_*.py` | one test module per unit above |
| `scripts/gen_governor_keypair.py` (repo `scripts/`) | generate the keypair; writes private to `secrets/`, public to the two agent dirs |

**Modify:**

| File | Change |
|---|---|
| `agents/safety-shepherd/policy.py` | add `POLICY_VERSION`, `RISK_CLASS` map, structured fields on `Decision.as_dict()` (additive) |
| `agents/safety-shepherd/safety_shepherd.py:335-373` | handler passes the new fields through (additive) |
| `agents/safety-shepherd/test_policy.py` | assertions for the new fields + a back-compat test |
| `agents/fleet-controller/capability_verify.py` | **new** — offline public-key verify |
| `agents/fleet-controller/main.py:43-67` | verify step on `/v1/plans/preview`, populate `capability` |
| `agents/fleet-controller/models.py:50-57` | `capability` becomes a structured sub-model (still optional) |
| `agents/fleet-controller/requirements.txt` | add `pyseto` |
| `agents/fleet-controller/Dockerfile:64-68` | `COPY capability_verify.py .` + `COPY governor_public_key.pem .` |
| `agents/fleet-controller/governor_public_key.pem` | **new** — copy of governor's public key |
| `docker-compose.fleet.yml` | **new** — wires `fleet-controller` + `governor` behind `--profile fleet` |
| `docker-compose.secrets.yml` | add `governor_ed25519_private_key` secret + governor block |
| `.github/workflows/agent-safety.yml` | add `governor` to the matrix + a `fleet-manifest` negative-capability job |
| `.github/workflows/docker-push.yml:~180` | add a `governor` build entry |
| `.github/scripts/fleet_overlay.yml` | add `governor` to `roster` |
| `.gitignore` | ensure `secrets/governor_ed25519_private_key.txt` is ignored (usually covered by `secrets/*`) |

---

## Task 1: Scaffold `agents/governor/` (health only)

**Files:**
- Create: `agents/governor/Dockerfile`, `agents/governor/requirements.txt`, `agents/governor/main.py`, `agents/governor/tests/conftest.py`, `agents/governor/tests/test_health.py`

**Interfaces:**
- Produces: `main.app` (FastAPI instance); `GET /health` → `{"status": "healthy", "agent": "governor"}`

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_health.py`:
```python
import pytest


@pytest.mark.asyncio
async def test_health_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy", "agent": "governor"}
```

`agents/governor/tests/conftest.py` (copy fleet-controller's pattern):
```python
import os
import sys

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest_asyncio.fixture
async def client():
    import main

    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Write minimal implementation**

`agents/governor/requirements.txt`:
```
fastapi>=0.136.1
uvicorn[standard]>=0.27.0
pydantic>=2.11.9,<2.13.0
httpx>=0.28.1
pyseto>=1.8.0
redis>=5.0.0
```

`agents/governor/main.py`:
```python
"""
governor — Phase 2. The governance-plane nucleus.

Mints signed, scope-bound capability tokens. Holds the kill-switch, the
Ed25519 signing key, the jti replay store, the system lease, and approval
records. Structurally inert: no Docker socket, no DOCKER_HOST, no
crew-orchestrator credential, no LLM/MCP client. See
docs/superpowers/specs/2026-09-04-autonomous-control-plane-north-star-design.md
"""
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="governor", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": "governor"}
```

`agents/governor/Dockerfile` — copy `agents/fleet-controller/Dockerfile` verbatim, then change:
- header comment first line to `# Governor — Phase 2. Governance-plane nucleus.`
- `ENV ... AGENT_NAME=governor`
- the `COPY main.py .` block to list every governor `.py` file created by later tasks **plus** `COPY governor_public_key.pem .`. For now just:
  ```dockerfile
  COPY main.py .
  ```
  (later tasks add their `COPY` lines in the same block)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agents/governor && python -m pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/governor/
git commit -m "feat(governor): scaffold service with health endpoint"
```

---

## Task 2: `keys.py` — Ed25519 key custody + keypair generator

**Files:**
- Create: `agents/governor/keys.py`, `agents/governor/tests/test_keys.py`, `scripts/gen_governor_keypair.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `keys.load_private_key() -> pyseto.Key` — reads PEM from `GOVERNOR_PRIVATE_KEY_FILE` (default `/run/secrets/governor_ed25519_private_key`) or, if absent, the `GOVERNOR_PRIVATE_KEY_PEM` env var. Raises `RuntimeError("governor signing key not configured")` if neither is set.
  - `keys.load_public_key() -> pyseto.Key` — reads `GOVERNOR_PUBLIC_KEY_FILE` (default: the committed `governor_public_key.pem` next to the module).
  - `keys.public_key_pem() -> str`

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_keys.py`:
```python
import pytest

import keys


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("GOVERNOR_PRIVATE_KEY_PEM", raising=False)
    monkeypatch.setenv("GOVERNOR_PRIVATE_KEY_FILE", "/nonexistent/path")
    with pytest.raises(RuntimeError, match="signing key not configured"):
        keys.load_private_key()


def test_env_pem_round_trips(monkeypatch, tmp_path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv = Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub_pem = (
        priv.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    monkeypatch.setenv("GOVERNOR_PRIVATE_KEY_PEM", priv_pem)
    pub_file = tmp_path / "pub.pem"
    pub_file.write_text(pub_pem)
    monkeypatch.setenv("GOVERNOR_PUBLIC_KEY_FILE", str(pub_file))

    import pyseto

    token = pyseto.encode(keys.load_private_key(), payload={"k": "v"}, serializer=__import__("json"))
    decoded = pyseto.decode(keys.load_public_key(), token, deserializer=__import__("json"))
    assert decoded.payload == {"k": "v"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_keys.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'keys'`

- [ ] **Step 3: Write minimal implementation**

`agents/governor/keys.py`:
```python
"""Ed25519 key custody for the governor.

The private key is the governor's one privileged asset. It is loaded once,
from a Docker secret file by default, and never logged. Verifiers never see
it — they hold only governor_public_key.pem.
"""
from __future__ import annotations

import os
from pathlib import Path

import pyseto

_PRIVATE_FILE_ENV = "GOVERNOR_PRIVATE_KEY_FILE"
_PRIVATE_PEM_ENV = "GOVERNOR_PRIVATE_KEY_PEM"
_PUBLIC_FILE_ENV = "GOVERNOR_PUBLIC_KEY_FILE"
_DEFAULT_PRIVATE_FILE = "/run/secrets/governor_ed25519_private_key"
_DEFAULT_PUBLIC_FILE = str(Path(__file__).with_name("governor_public_key.pem"))


def _read_private_pem() -> str:
    path = os.getenv(_PRIVATE_FILE_ENV, _DEFAULT_PRIVATE_FILE)
    if path and Path(path).is_file():
        return Path(path).read_text()
    pem = os.getenv(_PRIVATE_PEM_ENV, "").strip()
    if pem:
        return pem
    raise RuntimeError("governor signing key not configured")


def load_private_key() -> pyseto.Key:
    return pyseto.Key.new(version=4, purpose="public", key=_read_private_pem())


def public_key_pem() -> str:
    path = os.getenv(_PUBLIC_FILE_ENV, _DEFAULT_PUBLIC_FILE)
    return Path(path).read_text()


def load_public_key() -> pyseto.Key:
    return pyseto.Key.new(version=4, purpose="public", key=public_key_pem())
```

`scripts/gen_governor_keypair.py`:
```python
"""Generate the governor Ed25519 keypair.

Private PEM -> secrets/governor_ed25519_private_key.txt  (gitignored)
Public  PEM -> agents/governor/governor_public_key.pem
               agents/fleet-controller/governor_public_key.pem   (file-copy: verifiers vendor the public key)

Run once per environment. Re-running rotates the key (invalidates every
live capability — do it during a maintenance window).
"""
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]

priv = Ed25519PrivateKey.generate()
priv_pem = priv.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
)
pub_pem = priv.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
)

(ROOT / "secrets").mkdir(exist_ok=True)
(ROOT / "secrets" / "governor_ed25519_private_key.txt").write_bytes(priv_pem)
for rel in ("agents/governor/governor_public_key.pem", "agents/fleet-controller/governor_public_key.pem"):
    (ROOT / rel).write_bytes(pub_pem)
print("wrote private key to secrets/ and public key to both agent dirs")
```

- [ ] **Step 4: Generate a real keypair for local dev + tests**

Run: `python scripts/gen_governor_keypair.py`
Expected: `agents/governor/governor_public_key.pem` and `agents/fleet-controller/governor_public_key.pem` exist; `secrets/governor_ed25519_private_key.txt` exists and is gitignored (`git status --porcelain secrets/` shows nothing).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/test_keys.py -v`
Expected: PASS (both tests)

- [ ] **Step 6: Commit**

```bash
git add agents/governor/keys.py agents/governor/tests/test_keys.py \
        agents/governor/governor_public_key.pem \
        agents/fleet-controller/governor_public_key.pem \
        scripts/gen_governor_keypair.py
git commit -m "feat(governor): Ed25519 key custody + keypair generator"
```

---

## Task 3: `capability.py` — mint a PASETO v4.public capability

**Files:**
- Create: `agents/governor/capability.py`, `agents/governor/tests/test_capability_mint.py`

**Interfaces:**
- Consumes: `keys.load_private_key()`
- Produces:
  - `capability.Claims` — pydantic model: `iss: str`, `sub: str`, `mission_id: str`, `plan_hash: str`, `action: str`, `target: str | None`, `mode: str`, `max_attempts: int`, `not_before: str` (ISO 8601 Z), `expires_at: str`, `jti: str`, `verdict_id: str`, `policy_version: str`, `approval_id: str | None`
  - `capability.mint(*, sub, mission_id, plan_hash, action, target, mode, verdict_id, policy_version, approval_id=None, ttl_seconds=300, max_attempts=1, now=None) -> tuple[str, Claims]` — returns `(token_str, claims)`. `jti` is `f"cap_{uuid4().hex}"`. `iss="governor"`.

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_capability_mint.py`:
```python
from datetime import datetime, timedelta, timezone

import pyseto
import pytest

import capability
import keys


def _decode(token: str) -> dict:
    return pyseto.decode(keys.load_public_key(), token, deserializer=__import__("json")).payload


def test_mint_claims_present_and_bound():
    now = datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc)
    token, claims = capability.mint(
        sub="fleet-controller",
        mission_id="mission_abc",
        plan_hash="sha256:deadbeef",
        action="compose_profile.preview",
        target="agents",
        mode="DRY_RUN",
        verdict_id="verdict_1",
        policy_version="safety-2026-09-04.1",
        ttl_seconds=300,
        now=now,
    )
    payload = _decode(token)
    assert payload["iss"] == "governor"
    assert payload["sub"] == "fleet-controller"
    assert payload["plan_hash"] == "sha256:deadbeef"
    assert payload["action"] == "compose_profile.preview"
    assert payload["mode"] == "DRY_RUN"
    assert payload["max_attempts"] == 1
    assert payload["jti"].startswith("cap_")
    assert payload["not_before"] == "2026-09-04T13:00:00+00:00"
    assert payload["expires_at"] == "2026-09-04T13:05:00+00:00"
    assert claims.jti == payload["jti"]


def test_mint_jti_unique():
    kw = dict(
        sub="fleet-controller", mission_id="m", plan_hash="sha256:x",
        action="compose_profile.preview", target=None, mode="DRY_RUN",
        verdict_id="v", policy_version="p",
    )
    _, c1 = capability.mint(**kw)
    _, c2 = capability.mint(**kw)
    assert c1.jti != c2.jti
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_capability_mint.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'capability'`

- [ ] **Step 3: Write minimal implementation**

`agents/governor/capability.py`:
```python
"""PASETO v4.public (Ed25519) capability tokens.

A capability says: this exact mission may perform this exact action against
this exact target until this exact expiry, once. The governor is the only
holder of the signing key; every verifier checks with the public key only.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pyseto
from pydantic import BaseModel

import keys

ISSUER = "governor"


class Claims(BaseModel):
    iss: str
    sub: str
    mission_id: str
    plan_hash: str
    action: str
    target: Optional[str] = None
    mode: str
    max_attempts: int
    not_before: str
    expires_at: str
    jti: str
    verdict_id: str
    policy_version: str
    approval_id: Optional[str] = None


def mint(
    *,
    sub: str,
    mission_id: str,
    plan_hash: str,
    action: str,
    target: Optional[str],
    mode: str,
    verdict_id: str,
    policy_version: str,
    approval_id: Optional[str] = None,
    ttl_seconds: int = 300,
    max_attempts: int = 1,
    now: Optional[datetime] = None,
) -> tuple[str, Claims]:
    now = now or datetime.now(timezone.utc)
    claims = Claims(
        iss=ISSUER,
        sub=sub,
        mission_id=mission_id,
        plan_hash=plan_hash,
        action=action,
        target=target,
        mode=mode,
        max_attempts=max_attempts,
        not_before=now.isoformat(),
        expires_at=(now + timedelta(seconds=ttl_seconds)).isoformat(),
        jti=f"cap_{uuid.uuid4().hex}",
        verdict_id=verdict_id,
        policy_version=policy_version,
        approval_id=approval_id,
    )
    token = pyseto.encode(keys.load_private_key(), payload=claims.model_dump(), serializer=json)
    return token.decode() if isinstance(token, bytes) else token, claims
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/test_capability_mint.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/governor/capability.py agents/governor/tests/test_capability_mint.py
git commit -m "feat(governor): mint PASETO v4.public capability tokens"
```

---

## Task 4: `capability.py` — offline verify (signature + claim gates)

**Files:**
- Modify: `agents/governor/capability.py`
- Create: `agents/governor/tests/test_capability_verify.py`

**Interfaces:**
- Produces:
  - `capability.VerifyError(Exception)` with `.code: str` ∈ `{"bad_signature", "wrong_issuer", "wrong_subject", "plan_hash_mismatch", "out_of_scope", "wrong_mode", "not_yet_valid", "expired", "malformed"}`
  - `capability.verify(token: str, *, expected_sub: str, expected_plan_hash: str, expected_action: str, expected_target: str | None, expected_mode: str, public_key=None, now: datetime | None = None) -> Claims` — raises `VerifyError` on any failed gate; returns `Claims` on success. **Stateless** — no jti/replay/kill checks here (those are Task 12's stateful layer).

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_capability_verify.py`:
```python
from datetime import datetime, timedelta, timezone

import pytest

import capability

_NOW = datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc)
_BASE = dict(
    sub="fleet-controller", mission_id="m", plan_hash="sha256:aaa",
    action="compose_profile.preview", target="agents", mode="DRY_RUN",
    verdict_id="v", policy_version="p",
)
_EXPECT = dict(
    expected_sub="fleet-controller", expected_plan_hash="sha256:aaa",
    expected_action="compose_profile.preview", expected_target="agents",
    expected_mode="DRY_RUN",
)


def _mint(**over):
    kw = {**_BASE, **over}
    token, _ = capability.mint(now=_NOW, **kw)
    return token


def test_valid_token_verifies():
    claims = capability.verify(_mint(), now=_NOW, **_EXPECT)
    assert claims.mission_id == "m"


@pytest.mark.parametrize("bad,code", [
    (dict(expected_plan_hash="sha256:bbb"), "plan_hash_mismatch"),
    (dict(expected_sub="crew-orchestrator"), "wrong_subject"),
    (dict(expected_action="compose_profile.start"), "out_of_scope"),
    (dict(expected_mode="LIVE"), "wrong_mode"),
])
def test_claim_gates(bad, code):
    with pytest.raises(capability.VerifyError) as exc:
        capability.verify(_mint(), now=_NOW, **{**_EXPECT, **bad})
    assert exc.value.code == code


def test_expired():
    with pytest.raises(capability.VerifyError) as exc:
        capability.verify(_mint(), now=_NOW + timedelta(seconds=301), **_EXPECT)
    assert exc.value.code == "expired"


def test_not_yet_valid():
    with pytest.raises(capability.VerifyError) as exc:
        capability.verify(_mint(), now=_NOW - timedelta(seconds=5), **_EXPECT)
    assert exc.value.code == "not_yet_valid"


def test_forged_signature():
    good = _mint()
    forged = good[:-4] + ("AAAA" if good[-4:] != "AAAA" else "BBBB")
    with pytest.raises(capability.VerifyError) as exc:
        capability.verify(forged, now=_NOW, **_EXPECT)
    assert exc.value.code in ("bad_signature", "malformed")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_capability_verify.py -v`
Expected: FAIL — `AttributeError: module 'capability' has no attribute 'verify'`

- [ ] **Step 3: Write minimal implementation** — append to `agents/governor/capability.py`:

```python
from datetime import datetime as _dt


class VerifyError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(detail or code)


def verify(
    token: str,
    *,
    expected_sub: str,
    expected_plan_hash: str,
    expected_action: str,
    expected_target: Optional[str],
    expected_mode: str,
    public_key=None,
    now: Optional[datetime] = None,
) -> Claims:
    now = now or datetime.now(timezone.utc)
    pk = public_key or keys.load_public_key()
    try:
        raw = pyseto.decode(pk, token, deserializer=json).payload
        claims = Claims(**raw)
    except pyseto.exceptions.VerifyError:
        raise VerifyError("bad_signature")
    except Exception:
        raise VerifyError("malformed")

    if claims.iss != ISSUER:
        raise VerifyError("wrong_issuer")
    if claims.sub != expected_sub:
        raise VerifyError("wrong_subject")
    if claims.plan_hash != expected_plan_hash:
        raise VerifyError("plan_hash_mismatch")
    if claims.action != expected_action or (claims.target or None) != (expected_target or None):
        raise VerifyError("out_of_scope")
    if claims.mode != expected_mode:
        raise VerifyError("wrong_mode")
    if now < _dt.fromisoformat(claims.not_before):
        raise VerifyError("not_yet_valid")
    if now >= _dt.fromisoformat(claims.expires_at):
        raise VerifyError("expired")
    return claims
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/test_capability_verify.py -v`
Expected: PASS (all params)

- [ ] **Step 5: Commit**

```bash
git add agents/governor/capability.py agents/governor/tests/test_capability_verify.py
git commit -m "feat(governor): offline capability verification with typed VerifyError codes"
```

---

## Task 5: `transitions.py` — the fixed transition table

**Files:**
- Create: `agents/governor/transitions.py`, `agents/governor/tests/test_transitions.py`

**Interfaces:**
- Produces:
  - `transitions.Outcome` — pydantic/dataclass: `mint: bool`, `needs_approval: bool`, `capability_mode: str | None` (`"DRY_RUN"` | `"LIVE"` | `None`), `reason: str`
  - `transitions.resolve(*, mode: str, decision: str, kill_switch: bool, risk_class: str) -> Outcome` — pure. `mode ∈ {"DRY_RUN","LIVE"}`, `decision ∈ {"ALLOW","BLOCK","ESCALATE"}`.

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_transitions.py`:
```python
import pytest

import transitions as t


@pytest.mark.parametrize("mode,decision,kill,expect_mint,expect_appr,cap_mode", [
    ("DRY_RUN", "ALLOW", False, True, False, "DRY_RUN"),
    ("DRY_RUN", "ESCALATE", False, False, True, None),
    ("DRY_RUN", "BLOCK", False, False, False, None),
    ("LIVE", "ALLOW", False, True, False, "LIVE"),
    ("LIVE", "ESCALATE", False, False, True, None),
    ("LIVE", "BLOCK", False, False, False, None),
    ("LIVE", "ALLOW", True, False, False, None),
    ("DRY_RUN", "ALLOW", True, False, False, None),
])
def test_table(mode, decision, kill, expect_mint, expect_appr, cap_mode):
    out = t.resolve(mode=mode, decision=decision, kill_switch=kill, risk_class="INFRASTRUCTURE_MUTATION")
    assert out.mint is expect_mint
    assert out.needs_approval is expect_appr
    assert out.capability_mode == cap_mode


def test_kill_switch_still_allows_readonly_preview():
    out = t.resolve(mode="DRY_RUN", decision="ALLOW", kill_switch=True, risk_class="READ_ONLY")
    assert out.mint is True
    assert out.capability_mode == "DRY_RUN"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_transitions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'transitions'`

- [ ] **Step 3: Write minimal implementation**

`agents/governor/transitions.py`:
```python
"""The transition table — fixed code, never LLM-decided.

(mode x decision x kill_switch) -> Outcome. One place, exhaustive, one
test per row. Spec §7.
"""
from __future__ import annotations

from dataclasses import dataclass

_READ_ONLY = {"READ_ONLY"}


@dataclass(frozen=True)
class Outcome:
    mint: bool
    needs_approval: bool
    capability_mode: str | None
    reason: str


def resolve(*, mode: str, decision: str, kill_switch: bool, risk_class: str) -> Outcome:
    if kill_switch:
        if risk_class in _READ_ONLY and decision == "ALLOW":
            return Outcome(True, False, mode, "kill-switch ON; read-only preview permitted")
        return Outcome(False, False, None, "kill-switch ON; all mutation rejected")

    if decision == "BLOCK":
        return Outcome(False, False, None, "policy verdict BLOCK")
    if decision == "ESCALATE":
        return Outcome(False, True, None, "policy verdict ESCALATE; approval required")
    if decision == "ALLOW":
        return Outcome(True, False, mode, f"policy verdict ALLOW; {mode} capability")
    return Outcome(False, False, None, f"unknown decision {decision!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/test_transitions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/governor/transitions.py agents/governor/tests/test_transitions.py
git commit -m "feat(governor): fixed (mode x decision x kill-switch) transition table"
```

---

## Task 6: `shepherd_client.py` — fail-closed structured-verdict client

**Files:**
- Create: `agents/governor/shepherd_client.py`, `agents/governor/tests/test_shepherd_client.py`

**Interfaces:**
- Produces:
  - `shepherd_client.Verdict` — dataclass: `decision: str`, `reason: str`, `risk_class: str`, `policy_version: str`, `allowed_actions: list[str]`, `blocked_actions: list[str]`, `event_id: str | None`, `shepherd_available: bool`, `fail_closed: bool`
  - `shepherd_client._FAIL_CLOSED` — the frozen singleton: `decision="BLOCK"`, `risk_class="INFRASTRUCTURE_MUTATION"`, `shepherd_available=False`, `fail_closed=True`
  - `async shepherd_client.evaluate_plan(*, mission_id: str, plan_hash: str, action: str, target: str | None) -> Verdict`
  - `async shepherd_client.aclose() -> None`

Mirrors `agents/fleet-controller/safety_client.py` exactly (shared client, `httpx.AsyncClient(timeout=3.0)` built once, `SAFETY_SHEPHERD_URL` env default `http://safety-shepherd:8096`, `X-Agent-Key` header from `API_KEY`). Request body: `{"agent": "governor", "category": "docker", "tool": action, "target": target, "domain": None, "context": {"mission_id": mission_id, "plan_hash": plan_hash}}`.

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_shepherd_client.py`:
```python
import httpx
import pytest

import shepherd_client as sc


def _transport(handler):
    return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
async def _reset():
    yield
    await sc.aclose()


async def _run_with(monkeypatch, handler):
    client = httpx.AsyncClient(transport=_transport(handler), timeout=3.0)
    monkeypatch.setattr(sc, "_get_client", lambda: client)
    return await sc.evaluate_plan(
        mission_id="m", plan_hash="sha256:x", action="compose_profile.preview", target="agents"
    )


@pytest.mark.asyncio
async def test_structured_verdict_parsed(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={
            "decision": "ESCALATE", "reason": "runtime state",
            "risk_class": "INFRASTRUCTURE_MUTATION", "policy_version": "safety-2026-09-04.1",
            "allowed_actions": ["compose_profile.preview"], "blocked_actions": ["compose_profile.start"],
            "event_id": "evt_1",
        })
    v = await _run_with(monkeypatch, handler)
    assert v.decision == "ESCALATE"
    assert v.risk_class == "INFRASTRUCTURE_MUTATION"
    assert v.policy_version == "safety-2026-09-04.1"
    assert v.blocked_actions == ["compose_profile.start"]
    assert v.shepherd_available is True
    assert v.fail_closed is False


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [
    lambda request: httpx.Response(500, text="boom"),
    lambda request: httpx.Response(200, text="not json"),
    lambda request: httpx.Response(200, json={"reason": "no decision key"}),
])
async def test_fail_closed_paths(monkeypatch, handler):
    v = await _run_with(monkeypatch, handler)
    assert v.decision == "BLOCK"
    assert v.shepherd_available is False
    assert v.fail_closed is True


@pytest.mark.asyncio
async def test_connection_error_fail_closed(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("refused")
    v = await _run_with(monkeypatch, handler)
    assert v.fail_closed is True
    assert v.risk_class == "INFRASTRUCTURE_MUTATION"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_shepherd_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shepherd_client'`

- [ ] **Step 3: Write minimal implementation**

`agents/governor/shepherd_client.py`:
```python
"""Fail-closed structured-verdict client for Safety Shepherd /evaluate.

Same discipline as fleet-controller/safety_client.py: any timeout, non-200,
unparseable body, or body missing `decision` returns the frozen
_FAIL_CLOSED verdict. A well-formed structured verdict passes through with
the new risk_class / policy_version / allowed_actions / blocked_actions
fields. No off/monitor mode — this path is unconditionally enforced.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import httpx

_FALLBACK_RISK = "INFRASTRUCTURE_MUTATION"


@dataclass(frozen=True)
class Verdict:
    decision: str
    reason: str
    risk_class: str
    policy_version: str
    allowed_actions: list = field(default_factory=list)
    blocked_actions: list = field(default_factory=list)
    event_id: Optional[str] = None
    shepherd_available: bool = True
    fail_closed: bool = False


_FAIL_CLOSED = Verdict(
    decision="BLOCK",
    reason="Safety Shepherd unavailable; fail-closed",
    risk_class=_FALLBACK_RISK,
    policy_version="unknown",
    shepherd_available=False,
    fail_closed=True,
)

_client: Optional[httpx.AsyncClient] = None


def _url() -> str:
    return (os.getenv("SAFETY_SHEPHERD_URL") or "http://safety-shepherd:8096").rstrip("/")


def _headers() -> dict:
    key = (os.getenv("API_KEY") or "").strip()
    return {"X-Agent-Key": key} if key else {}


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=3.0)
    return _client


async def aclose() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def evaluate_plan(*, mission_id: str, plan_hash: str, action: str, target: Optional[str]) -> Verdict:
    body = {
        "agent": "governor",
        "category": "docker",
        "tool": action,
        "target": target,
        "domain": None,
        "context": {"mission_id": mission_id, "plan_hash": plan_hash},
    }
    try:
        resp = await _get_client().post(f"{_url()}/evaluate", json=body, headers=_headers())
    except Exception:
        return _FAIL_CLOSED
    if resp.status_code != 200:
        return _FAIL_CLOSED
    try:
        data = resp.json()
    except Exception:
        return _FAIL_CLOSED
    if not isinstance(data, dict) or "decision" not in data:
        return _FAIL_CLOSED
    return Verdict(
        decision=str(data["decision"]).upper(),
        reason=str(data.get("reason") or ""),
        risk_class=str(data.get("risk_class") or _FALLBACK_RISK),
        policy_version=str(data.get("policy_version") or "unknown"),
        allowed_actions=list(data.get("allowed_actions") or []),
        blocked_actions=list(data.get("blocked_actions") or []),
        event_id=data.get("event_id"),
        shepherd_available=True,
        fail_closed=False,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/test_shepherd_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/governor/shepherd_client.py agents/governor/tests/test_shepherd_client.py
git commit -m "feat(governor): fail-closed structured-verdict Shepherd client"
```

---

## Task 7: `redis_state.py` — jti replay + revocation (Redis DB 3)

**Files:**
- Create: `agents/governor/redis_state.py`, `agents/governor/tests/test_redis_state.py`

**Interfaces:**
- Produces:
  - `redis_state.get_redis()` — module-singleton `redis.asyncio.Redis` from `GOVERNOR_REDIS_URL` (default `redis://redis:6379/3`), `decode_responses=True`
  - `async redis_state.register_use(jti: str, ttl_seconds: int) -> bool` — returns `True` if this is the first use (added), `False` if `jti` was already present (replay). Uses `SET key NX EX ttl`.
  - `async redis_state.is_revoked(jti: str) -> bool`
  - `async redis_state.revoke(jti: str) -> None` (also accepts a `mission_id` marker key `mission:<id>` — `revoke_mission`)
  - `async redis_state.revoke_mission(mission_id: str) -> None` / `async redis_state.is_mission_revoked(mission_id: str) -> bool`
  - `async redis_state.aclose() -> None`
- Test dependency: `fakeredis` (`pip install fakeredis`); the fixture monkeypatches `get_redis` to a `fakeredis.aioredis.FakeRedis(decode_responses=True)`.

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_redis_state.py`:
```python
import fakeredis.aioredis
import pytest

import redis_state


@pytest.fixture
def fake(monkeypatch):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    return r


@pytest.mark.asyncio
async def test_first_use_then_replay(fake):
    assert await redis_state.register_use("cap_1", 300) is True
    assert await redis_state.register_use("cap_1", 300) is False


@pytest.mark.asyncio
async def test_revoke_jti(fake):
    assert await redis_state.is_revoked("cap_2") is False
    await redis_state.revoke("cap_2")
    assert await redis_state.is_revoked("cap_2") is True


@pytest.mark.asyncio
async def test_revoke_mission(fake):
    await redis_state.revoke_mission("mission_x")
    assert await redis_state.is_mission_revoked("mission_x") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && pip install fakeredis && python -m pytest tests/test_redis_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'redis_state'`

- [ ] **Step 3: Write minimal implementation**

`agents/governor/redis_state.py`:
```python
"""jti replay store + revocation set. Redis DB 3 (never 1/cache, never 2/rate-limits)."""
from __future__ import annotations

import os
from typing import Optional

import redis.asyncio as redis

_JTI = "gov:jti:"
_REVOKED_JTI = "gov:revoked:jti:"
_REVOKED_MISSION = "gov:revoked:mission:"

_r: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _r
    if _r is None:
        url = os.getenv("GOVERNOR_REDIS_URL") or "redis://redis:6379/3"
        _r = redis.from_url(url, decode_responses=True)
    return _r


async def aclose() -> None:
    global _r
    if _r is not None:
        await _r.aclose()
        _r = None


async def register_use(jti: str, ttl_seconds: int) -> bool:
    added = await get_redis().set(f"{_JTI}{jti}", "1", nx=True, ex=max(ttl_seconds, 1))
    return bool(added)


async def is_revoked(jti: str) -> bool:
    return bool(await get_redis().exists(f"{_REVOKED_JTI}{jti}"))


async def revoke(jti: str) -> None:
    await get_redis().set(f"{_REVOKED_JTI}{jti}", "1")


async def revoke_mission(mission_id: str) -> None:
    await get_redis().set(f"{_REVOKED_MISSION}{mission_id}", "1")


async def is_mission_revoked(mission_id: str) -> bool:
    return bool(await get_redis().exists(f"{_REVOKED_MISSION}{mission_id}"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/test_redis_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/governor/redis_state.py agents/governor/tests/test_redis_state.py
git commit -m "feat(governor): Redis DB 3 jti replay store + revocation set"
```

---

## Task 8: `killswitch.py` — Redis flag OR sentinel file, fail-closed

**Files:**
- Create: `agents/governor/killswitch.py`, `agents/governor/tests/test_killswitch.py`

**Interfaces:**
- Consumes: `redis_state.get_redis()`
- Produces:
  - `async killswitch.is_killed() -> bool` — `True` if the Redis key `gov:kill` is set, OR the sentinel file at `GOVERNOR_KILL_FILE` (default `/governance/KILL`) exists, OR Redis is unreachable (**fail-closed** — an unknowable kill state is treated as killed).
  - `async killswitch.engage(reason: str) -> None` — sets `gov:kill` to `reason`.
  - `async killswitch.release(reason: str) -> None` — deletes `gov:kill`. Does **not** touch the sentinel file (only a human clears that, off-box).

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_killswitch.py`:
```python
import fakeredis.aioredis
import pytest

import killswitch
import redis_state


@pytest.fixture
def fake(monkeypatch, tmp_path):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    return r


@pytest.mark.asyncio
async def test_default_not_killed(fake):
    assert await killswitch.is_killed() is False


@pytest.mark.asyncio
async def test_redis_flag_kills(fake):
    await killswitch.engage("manual test")
    assert await killswitch.is_killed() is True
    await killswitch.release("done")
    assert await killswitch.is_killed() is False


@pytest.mark.asyncio
async def test_sentinel_file_kills_even_after_release(fake, tmp_path):
    (tmp_path / "KILL").write_text("stop")
    assert await killswitch.is_killed() is True
    await killswitch.release("api says clear")
    assert await killswitch.is_killed() is True  # file still present


@pytest.mark.asyncio
async def test_redis_unreachable_fails_closed(monkeypatch, tmp_path):
    class Boom:
        async def get(self, *a, **k):
            raise ConnectionError("no redis")
    monkeypatch.setattr(redis_state, "get_redis", lambda: Boom())
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    assert await killswitch.is_killed() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_killswitch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'killswitch'`

- [ ] **Step 3: Write minimal implementation**

`agents/governor/killswitch.py`:
```python
"""Global kill-switch. Redis flag for fast toggling; an off-box sentinel
file that a compromised process cannot clear; fail-closed if Redis can't
be reached (an unknowable kill state is a killed state)."""
from __future__ import annotations

import os
from pathlib import Path

import redis_state

_KEY = "gov:kill"


def _sentinel_path() -> str:
    return os.getenv("GOVERNOR_KILL_FILE", "/governance/KILL")


async def is_killed() -> bool:
    if Path(_sentinel_path()).exists():
        return True
    try:
        return bool(await redis_state.get_redis().get(_KEY))
    except Exception:
        return True


async def engage(reason: str) -> None:
    await redis_state.get_redis().set(_KEY, reason or "engaged")


async def release(reason: str) -> None:
    await redis_state.get_redis().delete(_KEY)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/test_killswitch.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/governor/killswitch.py agents/governor/tests/test_killswitch.py
git commit -m "feat(governor): kill-switch (Redis flag + off-box sentinel file, fail-closed)"
```

---

## Task 9: `lease.py` — system lease + renew tick

**Files:**
- Create: `agents/governor/lease.py`, `agents/governor/tests/test_lease.py`

**Interfaces:**
- Consumes: `redis_state.get_redis()`, `killswitch.is_killed()`
- Produces:
  - `async lease.current() -> dict | None` — `{"lease_id": str, "issued_at": iso, "expires_at": iso}` or `None`
  - `async lease.is_valid(now: datetime | None = None) -> bool`
  - `async lease.renew_tick(*, shepherd_healthy: bool, ttl_seconds: int = 300, now: datetime | None = None) -> bool` — if `not killed and shepherd_healthy`, writes a fresh lease (`SET gov:lease <json> EX ttl`) and returns `True`; otherwise leaves the lease to expire and returns `False`.

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_lease.py`:
```python
from datetime import datetime, timedelta, timezone

import fakeredis.aioredis
import pytest

import killswitch
import lease
import redis_state

_NOW = datetime(2026, 9, 4, 13, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake(monkeypatch, tmp_path):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    return r


@pytest.mark.asyncio
async def test_renew_then_valid(fake):
    assert await lease.renew_tick(shepherd_healthy=True, ttl_seconds=300, now=_NOW) is True
    assert await lease.is_valid(now=_NOW + timedelta(seconds=120)) is True
    assert await lease.is_valid(now=_NOW + timedelta(seconds=400)) is False


@pytest.mark.asyncio
async def test_renew_skipped_when_killed(fake):
    await killswitch.engage("halt")
    assert await lease.renew_tick(shepherd_healthy=True, now=_NOW) is False
    assert await lease.is_valid(now=_NOW) is False


@pytest.mark.asyncio
async def test_renew_skipped_when_shepherd_down(fake):
    assert await lease.renew_tick(shepherd_healthy=False, now=_NOW) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_lease.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lease'`

- [ ] **Step 3: Write minimal implementation**

`agents/governor/lease.py`:
```python
"""System execution lease. The execution plane holds authority only while
this is valid. The governor renews it on a loop ONLY while the kill-switch
is clear and Shepherd is healthy — so a kill flip makes the whole
execution plane go inert within one lease period with no cooperation."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import killswitch
import redis_state

_KEY = "gov:lease"


async def current() -> Optional[dict]:
    raw = await redis_state.get_redis().get(_KEY)
    return json.loads(raw) if raw else None


async def is_valid(now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    rec = await current()
    if not rec:
        return False
    return now < datetime.fromisoformat(rec["expires_at"])


async def renew_tick(*, shepherd_healthy: bool, ttl_seconds: int = 300, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if await killswitch.is_killed() or not shepherd_healthy:
        return False
    rec = {
        "lease_id": f"lease_{uuid.uuid4().hex}",
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
    }
    await redis_state.get_redis().set(_KEY, json.dumps(rec), ex=ttl_seconds)
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/test_lease.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/governor/lease.py agents/governor/tests/test_lease.py
git commit -m "feat(governor): system lease with kill/health-gated renew tick"
```

---

## Task 10: `approvals.py` — records + two-person rule

**Files:**
- Create: `agents/governor/approvals.py`, `agents/governor/tests/test_approvals.py`

**Interfaces:**
- Consumes: `redis_state.get_redis()`
- Produces:
  - `approvals.DANGEROUS_CLASSES = {"INFRASTRUCTURE_MUTATION", "DESTRUCTIVE"}`
  - `async approvals.record(*, mission_id: str, plan_hash: str, approver_id: str, decision: str, reason: str) -> str` — returns an `approval_id` (`appr_<hex>`); stores under `gov:appr:<mission_id>` as a list.
  - `async approvals.satisfied(*, mission_id: str, plan_hash: str, proposer_id: str, risk_class: str) -> str | None` — returns a synthetic `approval_id` (deterministic: `f"appr-set:{mission_id}"`) when the rule is met, else `None`. Rule: every stored approval must have `decision == "approved"` and matching `plan_hash`; `proposer_id` never counts; dangerous classes need **≥2 distinct** `approver_id`s, others need **≥1**.

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_approvals.py`:
```python
import fakeredis.aioredis
import pytest

import approvals
import redis_state


@pytest.fixture
def fake(monkeypatch):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    return r


async def _approve(mid, who, ph="sha256:p"):
    return await approvals.record(
        mission_id=mid, plan_hash=ph, approver_id=who, decision="approved", reason="ok"
    )


@pytest.mark.asyncio
async def test_reversible_needs_one(fake):
    assert await approvals.satisfied(
        mission_id="m1", plan_hash="sha256:p", proposer_id="mission-director", risk_class="REVERSIBLE_ACTION"
    ) is None
    await _approve("m1", "alice")
    assert await approvals.satisfied(
        mission_id="m1", plan_hash="sha256:p", proposer_id="mission-director", risk_class="REVERSIBLE_ACTION"
    ) is not None


@pytest.mark.asyncio
async def test_dangerous_needs_two_distinct(fake):
    await _approve("m2", "alice")
    assert await approvals.satisfied(
        mission_id="m2", plan_hash="sha256:p", proposer_id="bob", risk_class="INFRASTRUCTURE_MUTATION"
    ) is None
    await _approve("m2", "alice")  # same person again — still 1 distinct
    assert await approvals.satisfied(
        mission_id="m2", plan_hash="sha256:p", proposer_id="bob", risk_class="INFRASTRUCTURE_MUTATION"
    ) is None
    await _approve("m2", "carol")
    assert await approvals.satisfied(
        mission_id="m2", plan_hash="sha256:p", proposer_id="bob", risk_class="INFRASTRUCTURE_MUTATION"
    ) is not None


@pytest.mark.asyncio
async def test_proposer_never_counts(fake):
    await _approve("m3", "alice")
    await _approve("m3", "dave")
    assert await approvals.satisfied(
        mission_id="m3", plan_hash="sha256:p", proposer_id="dave", risk_class="INFRASTRUCTURE_MUTATION"
    ) is None  # only alice counts


@pytest.mark.asyncio
async def test_plan_hash_must_match(fake):
    await _approve("m4", "alice", ph="sha256:OLD")
    assert await approvals.satisfied(
        mission_id="m4", plan_hash="sha256:NEW", proposer_id="bob", risk_class="REVERSIBLE_ACTION"
    ) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_approvals.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'approvals'`

- [ ] **Step 3: Write minimal implementation**

`agents/governor/approvals.py`:
```python
"""Human approval records + the two-person rule.

Phase 2 has no dashboard — an approval is created by an authenticated call
carrying an approver_id. The governor enforces the count rule; Phase 3
adds the UI that calls this.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

import redis_state

DANGEROUS_CLASSES = {"INFRASTRUCTURE_MUTATION", "DESTRUCTIVE"}


def _key(mission_id: str) -> str:
    return f"gov:appr:{mission_id}"


async def record(*, mission_id: str, plan_hash: str, approver_id: str, decision: str, reason: str) -> str:
    approval_id = f"appr_{uuid.uuid4().hex}"
    entry = {
        "approval_id": approval_id,
        "plan_hash": plan_hash,
        "approver_id": approver_id,
        "decision": decision,
        "reason": reason,
    }
    await redis_state.get_redis().rpush(_key(mission_id), json.dumps(entry))
    return approval_id


async def satisfied(*, mission_id: str, plan_hash: str, proposer_id: str, risk_class: str) -> Optional[str]:
    raw = await redis_state.get_redis().lrange(_key(mission_id), 0, -1)
    approvers = {
        e["approver_id"]
        for e in (json.loads(x) for x in raw)
        if e.get("decision") == "approved"
        and e.get("plan_hash") == plan_hash
        and e.get("approver_id") != proposer_id
    }
    need = 2 if risk_class in DANGEROUS_CLASSES else 1
    return f"appr-set:{mission_id}" if len(approvers) >= need else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/test_approvals.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/governor/approvals.py agents/governor/tests/test_approvals.py
git commit -m "feat(governor): approval records + two-person rule for dangerous classes"
```

---

## Task 11: `ledger_client.py` — fire-and-forget Governance Ledger writes

**Files:**
- Create: `agents/governor/ledger_client.py`, `agents/governor/tests/test_ledger_client.py`

**Interfaces:**
- Produces (mirrors `agents/fleet-controller/ledger_client.py`):
  - `ledger_client.init() -> None` (lifespan startup — builds the client only if `CORE_AGENT_KEY` set)
  - `async ledger_client.aclose() -> None`
  - `ledger_client.record(action: str, decision: str, payload: dict) -> None` — fire-and-forget; no-op if uninitialised; `agent="governor"`, `user_id="system"`; never awaited, never raises.
  - `ledger_client.build_body(action, decision, payload) -> dict` — pure helper, unit-testable.

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_ledger_client.py`:
```python
import ledger_client


def test_build_body_shape():
    body = ledger_client.build_body("capability.minted", "ALLOW", {"jti": "cap_1"})
    assert body == {
        "agent": "governor",
        "action": "capability.minted",
        "decision": "ALLOW",
        "user_id": "system",
        "payload": {"jti": "cap_1"},
    }


def test_record_is_noop_without_client():
    ledger_client._client = None
    ledger_client.record("x", "ALLOW", {})  # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_ledger_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ledger_client'`

- [ ] **Step 3: Write minimal implementation** — copy `agents/fleet-controller/ledger_client.py` and adapt:

```python
"""Fire-and-forget Governance Ledger write. Mirrors fleet-controller's
ledger_client: never awaited from a request path, never raises, no-op
until CORE_AGENT_KEY is provisioned."""
from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

LEDGER_PATH = "/api/v1/governance/ledger"

_client: Optional[httpx.AsyncClient] = None
_tasks: set = set()


def init() -> None:
    global _client
    key = (os.getenv("CORE_AGENT_KEY") or "").strip()
    if not key:
        return
    core_url = (os.getenv("CORE_URL") or "http://hypercode-core:8000").rstrip("/")
    _client = httpx.AsyncClient(base_url=core_url, timeout=3.0, headers={"X-Agent-Key": key})


async def aclose() -> None:
    global _client
    for task in list(_tasks):
        task.cancel()
    if _client is not None:
        await _client.aclose()
        _client = None


def build_body(action: str, decision: str, payload: dict) -> dict:
    return {
        "agent": "governor",
        "action": action,
        "decision": decision,
        "user_id": "system",
        "payload": payload,
    }


async def _write(action: str, decision: str, payload: dict) -> None:
    client = _client
    if client is None:
        return
    try:
        await client.post(LEDGER_PATH, json=build_body(action, decision, payload))
    except Exception:
        pass


def record(action: str, decision: str, payload: dict) -> None:
    if _client is None:
        return
    task = asyncio.create_task(_write(action, decision, payload))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/test_ledger_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/governor/ledger_client.py agents/governor/tests/test_ledger_client.py
git commit -m "feat(governor): fire-and-forget Governance Ledger client"
```

---

## Task 12: `POST /v1/capabilities/mint` — wire the pipeline

**Files:**
- Modify: `agents/governor/main.py`, `agents/governor/Dockerfile` (COPY the new modules)
- Create: `agents/governor/models.py`, `agents/governor/plan_validator.py` (copy of `agents/fleet-controller/plan_validator.py` + its `PlanRequest`/`RequestedAction` models — file-copy convention), `agents/governor/tests/test_mint_endpoint.py`

**Interfaces:**
- Consumes: `shepherd_client.evaluate_plan`, `transitions.resolve`, `killswitch.is_killed`, `lease.is_valid`, `approvals.satisfied`, `capability.mint`, `redis_state`, `ledger_client.record`, `plan_validator.validate_plan`
- Produces:
  - `models.MintRequest`: `plan: PlanRequest`, `plan_hash: str`, `mode: Literal["DRY_RUN","LIVE"]`, `action: str`, `target: str | None`, `proposer_id: str = "mission-director"`
  - `models.MintResponse`: `capability: str | None`, `jti: str | None`, `verdict: dict`, `minted: bool`, `reason: str`
  - `POST /v1/capabilities/mint` → `MintResponse`, status 200 always (a refusal is a 200 with `minted=false`); 422 only for schema/allowlist rejection.

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_mint_endpoint.py`:
```python
import fakeredis.aioredis
import pytest

import killswitch
import redis_state
import shepherd_client


@pytest.fixture(autouse=True)
def _wire(monkeypatch, tmp_path):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    yield


def _plan():
    return {
        "schema_version": 1,
        "mission_id": "mission_demo_1",
        "requested_actions": [
            {"action_id": "a1", "kind": "compose_profile.preview", "profile": "agents"}
        ],
        "constraints": {"max_services": 25, "allow_profiles": ["agents"], "deny_profiles": ["prod", "gpu"]},
    }


def _req(**over):
    base = {
        "plan": _plan(), "plan_hash": "sha256:demo", "mode": "DRY_RUN",
        "action": "compose_profile.preview", "target": "agents", "proposer_id": "mission-director",
    }
    base.update(over)
    return base


def _verdict(monkeypatch, decision, risk="INFRASTRUCTURE_MUTATION"):
    async def fake_eval(**kw):
        return shepherd_client.Verdict(
            decision=decision, reason="test", risk_class=risk,
            policy_version="safety-2026-09-04.1", event_id="evt_1",
        )
    monkeypatch.setattr(shepherd_client, "evaluate_plan", fake_eval)


@pytest.mark.asyncio
async def test_allow_dry_run_mints(client, monkeypatch):
    _verdict(monkeypatch, "ALLOW")
    resp = await client.post("/v1/capabilities/mint", json=_req())
    body = resp.json()
    assert resp.status_code == 200
    assert body["minted"] is True
    assert body["capability"] and body["jti"].startswith("cap_")


@pytest.mark.asyncio
async def test_block_no_capability(client, monkeypatch):
    _verdict(monkeypatch, "BLOCK")
    body = (await client.post("/v1/capabilities/mint", json=_req())).json()
    assert body["minted"] is False
    assert body["capability"] is None


@pytest.mark.asyncio
async def test_escalate_needs_approval(client, monkeypatch):
    _verdict(monkeypatch, "ESCALATE")
    body = (await client.post("/v1/capabilities/mint", json=_req())).json()
    assert body["minted"] is False
    assert "approval" in body["reason"].lower()


@pytest.mark.asyncio
async def test_kill_switch_refuses(client, monkeypatch):
    _verdict(monkeypatch, "ALLOW")
    await killswitch.engage("halt")
    body = (await client.post("/v1/capabilities/mint", json=_req())).json()
    assert body["minted"] is False
    assert "kill-switch" in body["reason"].lower()


@pytest.mark.asyncio
async def test_shepherd_down_fail_closed(client, monkeypatch):
    async def boom(**kw):
        return shepherd_client._FAIL_CLOSED
    monkeypatch.setattr(shepherd_client, "evaluate_plan", boom)
    body = (await client.post("/v1/capabilities/mint", json=_req())).json()
    assert body["minted"] is False
    assert body["verdict"]["shepherd_available"] is False


@pytest.mark.asyncio
async def test_denied_profile_422(client, monkeypatch):
    _verdict(monkeypatch, "ALLOW")
    bad = _req()
    bad["plan"]["requested_actions"][0]["profile"] = "gpu"
    resp = await client.post("/v1/capabilities/mint", json=bad)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_live_allow_mints_live_capability(client, monkeypatch):
    _verdict(monkeypatch, "ALLOW")
    body = (await client.post("/v1/capabilities/mint", json=_req(mode="LIVE"))).json()
    assert body["minted"] is True
    import capability, keys, pyseto, json as _j
    payload = pyseto.decode(keys.load_public_key(), body["capability"], deserializer=_j).payload
    assert payload["mode"] == "LIVE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_mint_endpoint.py -v`
Expected: FAIL — 404 on `/v1/capabilities/mint`

- [ ] **Step 3: Write minimal implementation**

Copy `agents/fleet-controller/plan_validator.py` → `agents/governor/plan_validator.py` **and** copy `agents/fleet-controller/models.py`'s `RequestedAction` / `Constraints` / `PlanRequest` / `canonical_hash` into `agents/governor/models.py` (governor needs the same plan shape; file-copy, not import).

Add to `agents/governor/models.py`:
```python
from typing import Literal, Optional

from pydantic import BaseModel


class MintRequest(BaseModel):
    plan: PlanRequest
    plan_hash: str
    mode: Literal["DRY_RUN", "LIVE"]
    action: str
    target: Optional[str] = None
    proposer_id: str = "mission-director"


class MintResponse(BaseModel):
    capability: Optional[str] = None
    jti: Optional[str] = None
    verdict: dict
    minted: bool
    reason: str
```

`agents/governor/main.py` (full replacement):
```python
"""
governor — Phase 2. The governance-plane nucleus.

Mints signed, scope-bound capability tokens. Holds the kill-switch, the
Ed25519 signing key, the jti replay store, the system lease, and approval
records. Structurally inert: no Docker socket, no DOCKER_HOST, no
crew-orchestrator credential, no LLM/MCP client. See
docs/superpowers/specs/2026-09-04-autonomous-control-plane-north-star-design.md
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException

import capability
import ledger_client
import lease as lease_mod
import redis_state
import shepherd_client
import transitions
from approvals import satisfied as approvals_satisfied
from killswitch import is_killed
from models import MintRequest, MintResponse
from plan_validator import PlanValidationError, validate_plan


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    ledger_client.init()
    try:
        yield
    finally:
        await shepherd_client.aclose()
        await ledger_client.aclose()
        await redis_state.aclose()


app = FastAPI(title="governor", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": "governor"}


@app.post("/v1/capabilities/mint", response_model=MintResponse)
async def mint_capability(req: MintRequest) -> MintResponse:
    try:
        validate_plan(req.plan)
    except PlanValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.detail) from exc

    verdict = await shepherd_client.evaluate_plan(
        mission_id=req.plan.mission_id, plan_hash=req.plan_hash, action=req.action, target=req.target
    )
    verdict_dict = {
        "decision": verdict.decision,
        "reason": verdict.reason,
        "risk_class": verdict.risk_class,
        "policy_version": verdict.policy_version,
        "shepherd_available": verdict.shepherd_available,
    }
    ledger_client.record("verdict.issued", verdict.decision, {
        "mission_id": req.plan.mission_id, "plan_hash": req.plan_hash,
        "verdict_id": verdict.event_id, "risk_class": verdict.risk_class,
        "policy_version": verdict.policy_version,
    })

    killed = await is_killed()
    outcome = transitions.resolve(
        mode=req.mode, decision=verdict.decision, kill_switch=killed, risk_class=verdict.risk_class
    )

    approval_id = None
    if outcome.needs_approval:
        approval_id = await approvals_satisfied(
            mission_id=req.plan.mission_id, plan_hash=req.plan_hash,
            proposer_id=req.proposer_id, risk_class=verdict.risk_class,
        )
        if approval_id is None:
            ledger_client.record("mint.refused", verdict.decision, {
                "mission_id": req.plan.mission_id, "plan_hash": req.plan_hash, "reason": "approval required",
            })
            return MintResponse(verdict=verdict_dict, minted=False,
                                reason="policy verdict ESCALATE; human approval required")

    if not outcome.mint and approval_id is None:
        ledger_client.record("mint.refused", verdict.decision, {
            "mission_id": req.plan.mission_id, "plan_hash": req.plan_hash, "reason": outcome.reason,
        })
        return MintResponse(verdict=verdict_dict, minted=False, reason=outcome.reason)

    if req.mode == "LIVE" and not await lease_mod.is_valid():
        ledger_client.record("mint.refused", verdict.decision, {
            "mission_id": req.plan.mission_id, "plan_hash": req.plan_hash, "reason": "system lease invalid",
        })
        return MintResponse(verdict=verdict_dict, minted=False, reason="system lease invalid")

    cap_mode = outcome.capability_mode or req.mode
    token, claims = capability.mint(
        sub="fleet-controller",
        mission_id=req.plan.mission_id,
        plan_hash=req.plan_hash,
        action=req.action,
        target=req.target,
        mode=cap_mode,
        verdict_id=verdict.event_id or "unknown",
        policy_version=verdict.policy_version,
        approval_id=approval_id,
    )
    ledger_client.record("capability.minted", verdict.decision, {
        "mission_id": req.plan.mission_id, "plan_hash": req.plan_hash,
        "jti": claims.jti, "verdict_id": verdict.event_id, "mode": cap_mode,
        "expires_at": claims.expires_at,
    })
    return MintResponse(capability=token, jti=claims.jti, verdict=verdict_dict, minted=True,
                        reason=outcome.reason)
```

Update `agents/governor/Dockerfile` COPY block to list every `.py` file in `agents/governor/` plus `COPY governor_public_key.pem .`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/ -v`
Expected: PASS (all modules, including the new `test_mint_endpoint.py`)

- [ ] **Step 5: Commit**

```bash
git add agents/governor/
git commit -m "feat(governor): POST /v1/capabilities/mint — validate -> shepherd -> transition -> gates -> mint"
```

---

## Task 13: Remaining endpoints — `/verify`, `/revoke`, `/v1/lease`

**Files:**
- Modify: `agents/governor/main.py`, `agents/governor/models.py`
- Create: `agents/governor/tests/test_verify_revoke_lease.py`

**Interfaces:**
- Produces:
  - `POST /v1/capabilities/verify` — body `{token, expected_sub, expected_plan_hash, expected_action, expected_target, expected_mode, burn: bool = false}` → `{valid: bool, code: str | None, claims: dict | None}`. Runs `capability.verify` (stateless) **then** stateful checks: `redis_state.is_revoked(jti)`, `redis_state.is_mission_revoked(mission_id)`, `killswitch.is_killed()`. If `burn` is true and all pass, calls `redis_state.register_use(jti, ttl)` and fails with `code="replayed"` if it was already used.
  - `POST /v1/capabilities/revoke` — body `{jti?: str, mission_id?: str, reason: str}` → `{revoked: true}`; writes a `capability.revoked` ledger row.
  - `GET /v1/lease` → `{lease: dict | None, valid: bool}`.

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_verify_revoke_lease.py`:
```python
import fakeredis.aioredis
import pytest

import capability
import redis_state

_EXPECT = dict(
    expected_sub="fleet-controller", expected_plan_hash="sha256:v",
    expected_action="compose_profile.preview", expected_target="agents",
    expected_mode="DRY_RUN",
)


@pytest.fixture(autouse=True)
def _wire(monkeypatch, tmp_path):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))


def _token():
    tok, _ = capability.mint(
        sub="fleet-controller", mission_id="m", plan_hash="sha256:v",
        action="compose_profile.preview", target="agents", mode="DRY_RUN",
        verdict_id="v", policy_version="p",
    )
    return tok


@pytest.mark.asyncio
async def test_verify_valid(client):
    body = (await client.post("/v1/capabilities/verify", json={"token": _token(), **_EXPECT})).json()
    assert body["valid"] is True
    assert body["code"] is None


@pytest.mark.asyncio
async def test_verify_rejects_revoked_mission(client):
    await client.post("/v1/capabilities/revoke", json={"mission_id": "m", "reason": "test"})
    body = (await client.post("/v1/capabilities/verify", json={"token": _token(), **_EXPECT})).json()
    assert body["valid"] is False
    assert body["code"] == "revoked"


@pytest.mark.asyncio
async def test_verify_burn_then_replay(client):
    tok = _token()
    first = (await client.post("/v1/capabilities/verify", json={"token": tok, "burn": True, **_EXPECT})).json()
    assert first["valid"] is True
    second = (await client.post("/v1/capabilities/verify", json={"token": tok, "burn": True, **_EXPECT})).json()
    assert second["valid"] is False
    assert second["code"] == "replayed"


@pytest.mark.asyncio
async def test_lease_endpoint(client):
    body = (await client.get("/v1/lease")).json()
    assert body["valid"] is False
    assert body["lease"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_verify_revoke_lease.py -v`
Expected: FAIL — 404s

- [ ] **Step 3: Write minimal implementation** — add to `agents/governor/models.py`:
```python
class VerifyRequest(BaseModel):
    token: str
    expected_sub: str
    expected_plan_hash: str
    expected_action: str
    expected_target: Optional[str] = None
    expected_mode: str
    burn: bool = False


class RevokeRequest(BaseModel):
    jti: Optional[str] = None
    mission_id: Optional[str] = None
    reason: str
```

Add to `agents/governor/main.py`:
```python
import capability as cap_mod
from models import RevokeRequest, VerifyRequest


@app.post("/v1/capabilities/verify")
async def verify_capability(req: VerifyRequest) -> dict:
    try:
        claims = cap_mod.verify(
            req.token, expected_sub=req.expected_sub, expected_plan_hash=req.expected_plan_hash,
            expected_action=req.expected_action, expected_target=req.expected_target,
            expected_mode=req.expected_mode,
        )
    except cap_mod.VerifyError as exc:
        return {"valid": False, "code": exc.code, "claims": None}

    if await redis_state.is_revoked(claims.jti) or await redis_state.is_mission_revoked(claims.mission_id):
        return {"valid": False, "code": "revoked", "claims": None}
    if await is_killed():
        return {"valid": False, "code": "kill_switch", "claims": None}
    if req.burn:
        first = await redis_state.register_use(claims.jti, claims.max_attempts and 300 or 300)
        if not first:
            return {"valid": False, "code": "replayed", "claims": None}
    return {"valid": True, "code": None, "claims": claims.model_dump()}


@app.post("/v1/capabilities/revoke")
async def revoke_capability(req: RevokeRequest) -> dict:
    if req.jti:
        await redis_state.revoke(req.jti)
    if req.mission_id:
        await redis_state.revoke_mission(req.mission_id)
    ledger_client.record("capability.revoked", "REVOKED", {
        "jti": req.jti, "mission_id": req.mission_id, "reason": req.reason,
    })
    return {"revoked": True}


@app.get("/v1/lease")
async def get_lease() -> dict:
    return {"lease": await lease_mod.current(), "valid": await lease_mod.is_valid()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/governor/
git commit -m "feat(governor): /v1/capabilities/verify (stateful), /revoke, /v1/lease"
```

---

## Task 14: `/v1/approvals` + `/v1/kill` + `/v1/unkill` endpoints

**Files:**
- Modify: `agents/governor/main.py`, `agents/governor/models.py`
- Create: `agents/governor/tests/test_kill_and_approval_endpoints.py`

**Interfaces:**
- Produces:
  - `POST /v1/approvals` — body `{mission_id, plan_hash, approver_id, decision, reason}` → `{approval_id: str}`; writes an `approval.recorded` ledger row.
  - `GET /v1/approvals/{mission_id}` → `{approvals: list[dict]}` (from Redis).
  - `POST /v1/kill` — requires header `X-Operator-Key` == `OPERATOR_KEY` env (loaded from `/run/secrets/api_key` via `OPERATOR_KEY_FILE`, env-or-file like other agents). Body `{reason}`. Calls `killswitch.engage`. 401 without a valid key. Writes `kill.engaged` ledger row.
  - `POST /v1/unkill` — same auth, body `{reason}` (mandatory, min length 1). Calls `killswitch.release`. Writes `kill.released` ledger row. Note in the response: `{"released": true, "note": "sentinel file, if present, still forces killed"}`.

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_kill_and_approval_endpoints.py`:
```python
import fakeredis.aioredis
import pytest

import killswitch
import redis_state


@pytest.fixture(autouse=True)
def _wire(monkeypatch, tmp_path):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))
    monkeypatch.setenv("OPERATOR_KEY", "s3cret-op")


@pytest.mark.asyncio
async def test_kill_requires_operator_key(client):
    assert (await client.post("/v1/kill", json={"reason": "x"})).status_code == 401


@pytest.mark.asyncio
async def test_kill_then_unkill(client):
    h = {"X-Operator-Key": "s3cret-op"}
    assert (await client.post("/v1/kill", json={"reason": "halt"}, headers=h)).status_code == 200
    assert await killswitch.is_killed() is True
    assert (await client.post("/v1/unkill", json={"reason": "clear"}, headers=h)).status_code == 200
    assert await killswitch.is_killed() is False


@pytest.mark.asyncio
async def test_unkill_requires_reason(client):
    h = {"X-Operator-Key": "s3cret-op"}
    assert (await client.post("/v1/unkill", json={"reason": ""}, headers=h)).status_code == 422


@pytest.mark.asyncio
async def test_record_and_list_approvals(client):
    r = await client.post("/v1/approvals", json={
        "mission_id": "m9", "plan_hash": "sha256:p", "approver_id": "alice",
        "decision": "approved", "reason": "lgtm",
    })
    assert r.json()["approval_id"].startswith("appr_")
    lst = (await client.get("/v1/approvals/m9")).json()["approvals"]
    assert lst[0]["approver_id"] == "alice"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_kill_and_approval_endpoints.py -v`
Expected: FAIL — 404s

- [ ] **Step 3: Write minimal implementation** — add to `models.py`:
```python
class ApprovalRequest(BaseModel):
    mission_id: str
    plan_hash: str
    approver_id: str
    decision: str
    reason: str


class KillRequest(BaseModel):
    reason: str = Field(min_length=1)
```
(add `from pydantic import Field` to the imports)

Add to `main.py`:
```python
import json as _json
import os

from fastapi import Header
from killswitch import engage as kill_engage, release as kill_release
from approvals import record as approvals_record
from models import ApprovalRequest, KillRequest


def _operator_key() -> str:
    path = os.getenv("OPERATOR_KEY_FILE", "/run/secrets/api_key")
    if path and os.path.isfile(path):
        return open(path).read().strip()
    return (os.getenv("OPERATOR_KEY") or "").strip()


def _require_operator(x_operator_key: str | None) -> None:
    expected = _operator_key()
    if not expected or x_operator_key != expected:
        raise HTTPException(status_code=401, detail="invalid operator key")


@app.post("/v1/approvals")
async def post_approval(req: ApprovalRequest) -> dict:
    approval_id = await approvals_record(
        mission_id=req.mission_id, plan_hash=req.plan_hash, approver_id=req.approver_id,
        decision=req.decision, reason=req.reason,
    )
    ledger_client.record("approval.recorded", req.decision.upper(), {
        "mission_id": req.mission_id, "plan_hash": req.plan_hash,
        "approver_id": req.approver_id, "approval_id": approval_id,
    })
    return {"approval_id": approval_id}


@app.get("/v1/approvals/{mission_id}")
async def list_approvals(mission_id: str) -> dict:
    raw = await redis_state.get_redis().lrange(f"gov:appr:{mission_id}", 0, -1)
    return {"approvals": [_json.loads(x) for x in raw]}


@app.post("/v1/kill")
async def post_kill(req: KillRequest, x_operator_key: str | None = Header(default=None)) -> dict:
    _require_operator(x_operator_key)
    await kill_engage(req.reason)
    ledger_client.record("kill.engaged", "KILL", {"reason": req.reason})
    return {"killed": True}


@app.post("/v1/unkill")
async def post_unkill(req: KillRequest, x_operator_key: str | None = Header(default=None)) -> dict:
    _require_operator(x_operator_key)
    await kill_release(req.reason)
    ledger_client.record("kill.released", "UNKILL", {"reason": req.reason})
    return {"released": True, "note": "sentinel file, if present, still forces killed"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/ -v`
Expected: PASS (whole suite)

- [ ] **Step 5: Commit**

```bash
git add agents/governor/
git commit -m "feat(governor): /v1/approvals + operator-gated /v1/kill and /v1/unkill"
```

---

## Task 15: Background lease-renew loop

**Files:**
- Modify: `agents/governor/main.py`
- Create: `agents/governor/tests/test_renew_loop.py`

**Interfaces:**
- Consumes: `lease.renew_tick`, `shepherd_client` (a `/health` probe helper `shepherd_client.healthy() -> bool`)
- Produces:
  - `shepherd_client.healthy() -> bool` — `GET {SAFETY_SHEPHERD_URL}/health`, `True` only on 200, fail-closed `False` otherwise.
  - `main._renew_loop()` — `while True: await lease.renew_tick(shepherd_healthy=await shepherd_client.healthy()); await asyncio.sleep(GOVERNOR_LEASE_RENEW_SECONDS or 120)`. Started as a task in `lifespan`, cancelled on shutdown.

- [ ] **Step 1: Write the failing test**

`agents/governor/tests/test_renew_loop.py`:
```python
import fakeredis.aioredis
import pytest

import lease
import redis_state
import shepherd_client


@pytest.fixture
def fake(monkeypatch, tmp_path):
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_state, "get_redis", lambda: r)
    monkeypatch.setenv("GOVERNOR_KILL_FILE", str(tmp_path / "KILL"))


@pytest.mark.asyncio
async def test_healthy_probe_true(monkeypatch, fake):
    import httpx
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    monkeypatch.setattr(shepherd_client, "_get_client", lambda: client)
    assert await shepherd_client.healthy() is True
    await client.aclose()


@pytest.mark.asyncio
async def test_healthy_probe_failclosed(monkeypatch, fake):
    import httpx
    def boom(r):
        raise httpx.ConnectError("no")
    client = httpx.AsyncClient(transport=httpx.MockTransport(boom))
    monkeypatch.setattr(shepherd_client, "_get_client", lambda: client)
    assert await shepherd_client.healthy() is False
    await client.aclose()


@pytest.mark.asyncio
async def test_one_renew_tick_via_loop_body(monkeypatch, fake):
    monkeypatch.setattr(shepherd_client, "healthy", lambda: _true())
    async def _true():
        return True
    ok = await lease.renew_tick(shepherd_healthy=await shepherd_client.healthy())
    assert ok is True
    assert await lease.is_valid() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/governor && python -m pytest tests/test_renew_loop.py -v`
Expected: FAIL — `AttributeError: module 'shepherd_client' has no attribute 'healthy'`

- [ ] **Step 3: Write minimal implementation**

Add to `agents/governor/shepherd_client.py`:
```python
async def healthy() -> bool:
    try:
        resp = await _get_client().get(f"{_url()}/health")
        return resp.status_code == 200
    except Exception:
        return False
```

Add to `agents/governor/main.py` lifespan (and imports `import asyncio`, `import os`):
```python
async def _renew_loop() -> None:
    interval = int(os.getenv("GOVERNOR_LEASE_RENEW_SECONDS") or 120)
    while True:
        try:
            await lease_mod.renew_tick(shepherd_healthy=await shepherd_client.healthy())
        except Exception:
            pass
        await asyncio.sleep(interval)
```
In `lifespan`, after `ledger_client.init()`:
```python
    task = asyncio.create_task(_renew_loop())
    try:
        yield
    finally:
        task.cancel()
        await shepherd_client.aclose()
        await ledger_client.aclose()
        await redis_state.aclose()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/governor && python -m pytest tests/ -v`
Expected: PASS (whole suite)

- [ ] **Step 5: Commit**

```bash
git add agents/governor/
git commit -m "feat(governor): background lease-renew loop gated on kill-switch + Shepherd health"
```

---

## Task 16: Safety Shepherd — structured verdict (additive)

**Files:**
- Modify: `agents/safety-shepherd/policy.py`, `agents/safety-shepherd/safety_shepherd.py:335-373`
- Modify: `agents/safety-shepherd/test_policy.py`
- Create: `agents/safety-shepherd/test_structured_verdict.py`

**Interfaces:**
- Produces (additive — every existing key on the `/evaluate` response stays):
  - `policy.POLICY_VERSION = "safety-2026-09-04.1"`
  - `policy.RISK_CLASS: dict[str, str]` — maps `category` → risk class: `{"docker": "INFRASTRUCTURE_MUTATION", "file_write": "REVERSIBLE_ACTION", "http_external": "REVERSIBLE_ACTION", "stripe": "DESTRUCTIVE", "discord": "REVERSIBLE_ACTION"}`, default `"READ_ONLY"`.
  - `Decision.as_dict()` gains: `risk_class`, `policy_version`, `reasons` (`[self.reason]`), `allowed_actions` (`["compose_profile.preview", "compose_config.validate"]` when `category == "docker"` else `[]`), `blocked_actions` (`["compose_profile.start", "compose_profile.stop"]` when `category == "docker"` else `[]`).

- [ ] **Step 1: Write the failing test**

`agents/safety-shepherd/test_structured_verdict.py`:
```python
from policy import RISK_CLASS, POLICY_VERSION, Decision


def test_risk_class_map():
    assert RISK_CLASS["docker"] == "INFRASTRUCTURE_MUTATION"
    assert RISK_CLASS.get("nonsense", "READ_ONLY") == "READ_ONLY"


def test_as_dict_has_structured_fields_for_docker():
    d = Decision("ESCALATE", "dangerous", "dangerous_category", category="docker", agent="governor")
    out = d.as_dict()
    # back-compat: old keys still present
    assert out["decision"] == "ESCALATE"
    assert out["reason"] == "dangerous"
    assert out["rule"] == "dangerous_category"
    # new keys
    assert out["risk_class"] == "INFRASTRUCTURE_MUTATION"
    assert out["policy_version"] == POLICY_VERSION
    assert out["reasons"] == ["dangerous"]
    assert "compose_profile.start" in out["blocked_actions"]
    assert "compose_profile.preview" in out["allowed_actions"]


def test_as_dict_generic_category_has_empty_action_lists():
    out = Decision("ALLOW", "ok", "default", category="generic").as_dict()
    assert out["risk_class"] == "READ_ONLY"
    assert out["allowed_actions"] == []
    assert out["blocked_actions"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/safety-shepherd && python -m pytest test_structured_verdict.py -v`
Expected: FAIL — `ImportError: cannot import name 'RISK_CLASS'`

- [ ] **Step 3: Write minimal implementation** — in `agents/safety-shepherd/policy.py`:

After the `DANGEROUS` set:
```python
POLICY_VERSION = "safety-2026-09-04.1"

RISK_CLASS = {
    "docker": "INFRASTRUCTURE_MUTATION",
    "file_write": "REVERSIBLE_ACTION",
    "http_external": "REVERSIBLE_ACTION",
    "stripe": "DESTRUCTIVE",
    "discord": "REVERSIBLE_ACTION",
}

_DOCKER_ALLOWED = ["compose_profile.preview", "compose_config.validate"]
_DOCKER_BLOCKED = ["compose_profile.start", "compose_profile.stop"]
```

Replace `Decision.as_dict` with:
```python
    def as_dict(self) -> dict[str, Any]:
        cat = self.category or ""
        is_docker = cat == "docker"
        return {
            "decision": self.decision,
            "reason": self.reason,
            "rule": self.rule,
            "category": self.category,
            "agent": self.agent,
            "risk_class": RISK_CLASS.get(cat, "READ_ONLY"),
            "policy_version": POLICY_VERSION,
            "reasons": [self.reason] if self.reason else [],
            "allowed_actions": list(_DOCKER_ALLOWED) if is_docker else [],
            "blocked_actions": list(_DOCKER_BLOCKED) if is_docker else [],
        }
```

The `/evaluate` handler in `safety_shepherd.py` already does `result = decision.as_dict()` then adds `event_id` — no handler change needed; the new keys flow through automatically. Add one assertion to `test_policy.py`'s existing evaluate test (or a new test) that an unchanged caller reading only `data["decision"]` still works:
```python
def test_evaluate_response_backcompat():
    from policy import evaluate
    manifest = {"agents": {"*": {"tools": []}}, "defaults": {}}
    d = evaluate(manifest, {"agent": "x", "category": "generic"})
    out = d.as_dict()
    assert set(["decision", "reason", "rule", "category"]).issubset(out)  # old contract intact
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/safety-shepherd && python -m pytest test_policy.py test_structured_verdict.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/safety-shepherd/policy.py agents/safety-shepherd/test_policy.py agents/safety-shepherd/test_structured_verdict.py
git commit -m "feat(safety-shepherd): additive structured verdict (risk_class, policy_version, allowed/blocked actions)"
```

---

## Task 17: fleet-controller — require a capability

**Files:**
- Create: `agents/fleet-controller/capability_verify.py`, `agents/fleet-controller/governor_public_key.pem` (already created in Task 2 by the keygen script), `agents/fleet-controller/tests/test_capability_gate.py`
- Modify: `agents/fleet-controller/main.py:43-67`, `agents/fleet-controller/models.py:50-57`, `agents/fleet-controller/requirements.txt`, `agents/fleet-controller/Dockerfile:64-68`

**Interfaces:**
- Consumes: governor's PASETO public key (vendored PEM); `capability` submitted alongside the plan.
- Produces:
  - `capability_verify.verify_or_none(token: str | None, *, plan_hash: str, action: str, target: str | None, mode: str) -> tuple[bool, str]` — offline PASETO v4.public verify against `governor_public_key.pem`; returns `(ok, reason)`. `sub` must be `"fleet-controller"`, `iss` `"governor"`, time window valid, `plan_hash`/`action`/`target`/`mode` must match. No token → `(False, "no capability presented")`.
  - `models.PlanRequest` gains `capability: Optional[str] = None` (the inbound token) — distinct from the existing outbound `PlanResponse.capability`.
  - `models.CapabilityView` (BaseModel): `presented: bool`, `valid: bool`, `reason: str`. `PlanResponse.capability` type changes `Optional[str]` → `Optional[CapabilityView]`.
  - `/v1/plans/preview` behaviour: still `422` on schema/profile rejection; still calls Shepherd; **now also** runs `capability_verify.verify_or_none` and puts the result in `PlanResponse.capability`. `execution.performed` stays `False` unconditionally. A missing/invalid capability does **not** 4xx in Phase 2 (preview still returns) — it is recorded in the response and the ledger. (Phase 4 makes it blocking for LIVE.)

- [ ] **Step 1: Write the failing test**

`agents/fleet-controller/tests/test_capability_gate.py`:
```python
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

import capability_verify  # noqa: E402


def _gov_token(**over):
    """Mint with governor's private key for the test (keygen script wrote it to secrets/)."""
    import json

    import pyseto
    priv_pem = (Path(__file__).resolve().parents[3] / "secrets" / "governor_ed25519_private_key.txt").read_text()
    key = pyseto.Key.new(version=4, purpose="public", key=priv_pem)
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    claims = {
        "iss": "governor", "sub": "fleet-controller", "mission_id": "m",
        "plan_hash": "sha256:demo", "action": "compose_profile.preview", "target": "agents",
        "mode": "DRY_RUN", "max_attempts": 1,
        "not_before": now.isoformat(), "expires_at": (now + timedelta(seconds=300)).isoformat(),
        "jti": "cap_test", "verdict_id": "v", "policy_version": "p", "approval_id": None,
    }
    claims.update(over)
    return pyseto.encode(key, payload=claims, serializer=json).decode()


def test_no_token():
    ok, reason = capability_verify.verify_or_none(
        None, plan_hash="sha256:demo", action="compose_profile.preview", target="agents", mode="DRY_RUN"
    )
    assert ok is False
    assert "no capability" in reason.lower()


def test_valid_token():
    ok, reason = capability_verify.verify_or_none(
        _gov_token(), plan_hash="sha256:demo", action="compose_profile.preview", target="agents", mode="DRY_RUN"
    )
    assert ok is True


def test_plan_hash_mismatch():
    ok, reason = capability_verify.verify_or_none(
        _gov_token(), plan_hash="sha256:OTHER", action="compose_profile.preview", target="agents", mode="DRY_RUN"
    )
    assert ok is False
    assert "plan_hash" in reason


@pytest.mark.asyncio
async def test_preview_reports_capability_and_never_executes(client, monkeypatch):
    import safety_client

    async def fake_check(plan, plan_hash):
        return safety_client.SafetyResult(decision="ALLOW", reason="ok")
    monkeypatch.setattr(safety_client, "check_infrastructure_mutation", fake_check)

    plan = {
        "schema_version": 1, "mission_id": "m",
        "requested_actions": [{"action_id": "a1", "kind": "compose_profile.preview", "profile": "agents"}],
        "constraints": {"allow_profiles": ["agents"], "deny_profiles": ["prod", "gpu"]},
        "capability": None,
    }
    body = (await client.post("/v1/plans/preview", json=plan)).json()
    assert body["execution"]["performed"] is False
    assert body["capability"]["presented"] is False
    assert body["capability"]["valid"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents/fleet-controller && python -m pytest tests/test_capability_gate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'capability_verify'`

- [ ] **Step 3: Write minimal implementation**

`agents/fleet-controller/requirements.txt` — add:
```
pyseto>=1.8.0
```

`agents/fleet-controller/capability_verify.py`:
```python
"""Offline capability verification. fleet-controller holds ONLY the governor
public key — it can check a token but never mint one. Phase 2: the result is
recorded, not enforced (a missing/invalid capability still returns a preview);
Phase 4 makes it blocking for LIVE."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pyseto

_PUB = str(Path(__file__).with_name("governor_public_key.pem"))


def _public_key() -> pyseto.Key:
    return pyseto.Key.new(version=4, purpose="public", key=Path(_PUB).read_text())


def verify_or_none(
    token: Optional[str], *, plan_hash: str, action: str, target: Optional[str], mode: str
) -> tuple[bool, str]:
    if not token:
        return False, "no capability presented"
    try:
        claims = pyseto.decode(_public_key(), token, deserializer=json).payload
    except Exception:
        return False, "bad signature or malformed capability"
    if claims.get("iss") != "governor":
        return False, "wrong issuer"
    if claims.get("sub") != "fleet-controller":
        return False, "wrong subject"
    if claims.get("plan_hash") != plan_hash:
        return False, "plan_hash mismatch"
    if claims.get("action") != action or (claims.get("target") or None) != (target or None):
        return False, "action/target out of scope"
    if claims.get("mode") != mode:
        return False, "mode mismatch"
    now = datetime.now(timezone.utc)
    try:
        if now < datetime.fromisoformat(claims["not_before"]):
            return False, "not yet valid"
        if now >= datetime.fromisoformat(claims["expires_at"]):
            return False, "expired"
    except Exception:
        return False, "malformed time window"
    return True, "ok"
```

`agents/fleet-controller/models.py` — change the `PlanRequest` and `PlanResponse`:
```python
class PlanRequest(BaseModel):
    schema_version: Literal[1]
    mission_id: str
    requested_actions: list[RequestedAction]
    constraints: Constraints = Field(default_factory=Constraints)
    capability: Optional[str] = None   # inbound governor token (Phase 2)


class CapabilityView(BaseModel):
    presented: bool
    valid: bool
    reason: str


class PlanResponse(BaseModel):
    plan_id: str
    plan_hash: str
    mode: Literal["DRY_RUN"] = "DRY_RUN"
    safety: SafetyView
    execution: ExecutionView
    capability: Optional[CapabilityView] = None   # was Optional[str]; now the verify result
```

`agents/fleet-controller/main.py` — in `preview_plan`, after computing `plan_hash` and before building the response:
```python
    from models import CapabilityView
    import capability_verify

    cap_action = plan.requested_actions[0].kind
    cap_target = plan.requested_actions[0].profile
    cap_ok, cap_reason = capability_verify.verify_or_none(
        plan.capability, plan_hash=plan_hash, action=cap_action, target=cap_target, mode="DRY_RUN"
    )
    capability_view = CapabilityView(presented=plan.capability is not None, valid=cap_ok, reason=cap_reason)
```
and add `capability=capability_view` to the `PlanResponse(...)` constructor.

`agents/fleet-controller/Dockerfile` — in the COPY block add:
```dockerfile
COPY capability_verify.py .
COPY governor_public_key.pem .
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents/fleet-controller && python -m pytest tests/ -v`
Expected: PASS (existing suite + new `test_capability_gate.py`); every `test_no_execution.py` assertion still holds.

- [ ] **Step 5: Commit**

```bash
git add agents/fleet-controller/
git commit -m "feat(fleet-controller): offline capability-verify step on /v1/plans/preview (recorded, non-blocking in Phase 2)"
```

---

## Task 18: `docker-compose.fleet.yml` + secrets wiring

**Files:**
- Create: `docker-compose.fleet.yml`
- Modify: `docker-compose.secrets.yml`
- Create: `governance-control/.gitkeep` (the sentinel-file mount dir)

**Interfaces:** none (infra). Both services behind `--profile fleet`. `governor` on `agents-net` + `data-net`; `fleet-controller` on `agents-net`. Neither mounts `/var/run/docker.sock`, sets `DOCKER_HOST`, or receives `ORCHESTRATOR_API_KEY` / `CREW_ORCHESTRATOR_API_KEY`.

- [ ] **Step 1: Confirm port :8089 is still free**

Run: `grep -rn "8089" docker-compose*.yml`
Expected: no output. (If any, use `:8085` and adjust every reference below.)

- [ ] **Step 2: Write `docker-compose.fleet.yml`**

```yaml
# Fleet / Governance plane — Phase 0 (fleet-controller) + Phase 2 (governor).
# Launch:  docker compose -f docker-compose.yml -f docker-compose.core.yml \
#            -f docker-compose.fleet.yml --profile fleet up -d
# Neither service can execute infrastructure changes: no docker.sock, no
# DOCKER_HOST, no crew-orchestrator credential. governor additionally holds
# the ONLY capability-signing key. See
# docs/superpowers/specs/2026-09-04-autonomous-control-plane-north-star-design.md

services:
  fleet-controller:
    build:
      context: ./agents/fleet-controller
    image: hypercode-v24-fleet-controller:latest
    container_name: fleet-controller
    profiles: ["fleet"]
    environment:
      AGENT_NAME: fleet-controller
      AGENT_PORT: "8080"
      SAFETY_SHEPHERD_URL: http://safety-shepherd:8096
      CORE_URL: http://hypercode-core:8000
    ports:
      - "127.0.0.1:8094:8080"
    networks:
      - agents-net
    depends_on:
      safety-shepherd:
        condition: service_started
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  governor:
    build:
      context: ./agents/governor
    image: hypercode-v24-governor:latest
    container_name: governor
    profiles: ["fleet"]
    environment:
      AGENT_NAME: governor
      AGENT_PORT: "8080"
      SAFETY_SHEPHERD_URL: http://safety-shepherd:8096
      CORE_URL: http://hypercode-core:8000
      GOVERNOR_REDIS_URL: redis://redis:6379/3
      GOVERNOR_PRIVATE_KEY_FILE: /run/secrets/governor_ed25519_private_key
      GOVERNOR_KILL_FILE: /governance/KILL
      OPERATOR_KEY_FILE: /run/secrets/api_key
      GOVERNOR_LEASE_RENEW_SECONDS: "120"
    ports:
      - "127.0.0.1:8089:8080"
    volumes:
      - ./governance-control:/governance:ro
    networks:
      - agents-net
      - data-net
    depends_on:
      safety-shepherd:
        condition: service_started
      redis:
        condition: service_started
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

networks:
  agents-net:
    external: true
    name: hypercode_agents_net
  data-net:
    external: true
    name: hypercode_data_net
```

- [ ] **Step 3: Add the secret to `docker-compose.secrets.yml`**

Under `secrets:` add:
```yaml
  governor_ed25519_private_key:
    file: ./secrets/governor_ed25519_private_key.txt
```
Under `services:` add:
```yaml
  governor:
    environment:
      CORE_AGENT_KEY_FILE: /run/secrets/agent_api_key_governor
    secrets:
      - governor_ed25519_private_key
      - api_key
      - agent_api_key_governor
```
And add to the `secrets:` block:
```yaml
  agent_api_key_governor:
    file: ./secrets/agent_api_key_governor.txt
```
(Provision the key value with the existing `scripts/mint_agent_keys.py` flow — note it in the smoke-test step; a missing file just means ledger writes no-op, which is safe.)

- [ ] **Step 4: Create the sentinel-mount dir**

Run: `mkdir -p governance-control && touch governance-control/.gitkeep`
Add a line to `.gitignore`: `governance-control/KILL`

- [ ] **Step 5: Validate the rendered config**

Run:
```bash
python scripts/gen_governor_keypair.py   # ensure secrets/governor_ed25519_private_key.txt exists
docker compose -f docker-compose.yml -f docker-compose.core.yml -f docker-compose.fleet.yml --profile fleet config >/tmp/fleet-render.yml
```
Expected: exits 0. Then:
```bash
grep -c "docker.sock" /tmp/fleet-render.yml   # expect 0
grep -E "DOCKER_HOST|ORCHESTRATOR_API_KEY" /tmp/fleet-render.yml   # expect no match in the governor/fleet-controller blocks
```

- [ ] **Step 6: Commit**

```bash
git add docker-compose.fleet.yml docker-compose.secrets.yml governance-control/.gitkeep .gitignore
git commit -m "feat(fleet): docker-compose.fleet.yml wires fleet-controller + governor behind --profile fleet"
```

---

## Task 19: CI — governor test leg + rendered-manifest negative-capability check

**Files:**
- Modify: `.github/workflows/agent-safety.yml`, `.github/workflows/docker-push.yml`, `.github/scripts/fleet_overlay.yml`
- Create: `.github/scripts/check_fleet_manifest_containment.py`

**Interfaces:** none (CI). The manifest check asserts, against the **rendered** `docker compose config`, that neither `fleet-controller` nor `governor`:
- has a `volumes:` entry containing `docker.sock`
- has `DOCKER_HOST` in `environment:`
- has `ORCHESTRATOR_API_KEY` or `CREW_ORCHESTRATOR_API_KEY` in `environment:`

- [ ] **Step 1: Write the failing test**

`.github/scripts/tests/test_check_fleet_manifest_containment.py`:
```python
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check_fleet_manifest_containment.py"


def test_passes_on_clean_manifest(tmp_path):
    manifest = tmp_path / "render.yml"
    manifest.write_text(
        "services:\n"
        "  governor:\n"
        "    environment:\n"
        "      SAFETY_SHEPHERD_URL: http://safety-shepherd:8096\n"
        "    volumes:\n"
        "      - ./governance-control:/governance:ro\n"
        "  fleet-controller:\n"
        "    environment: {}\n"
    )
    r = subprocess.run([sys.executable, str(SCRIPT), str(manifest)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_fails_when_socket_mounted(tmp_path):
    manifest = tmp_path / "render.yml"
    manifest.write_text(
        "services:\n"
        "  governor:\n"
        "    volumes:\n"
        "      - /var/run/docker.sock:/var/run/docker.sock:ro\n"
    )
    r = subprocess.run([sys.executable, str(SCRIPT), str(manifest)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "docker.sock" in r.stdout


def test_fails_on_docker_host_env(tmp_path):
    manifest = tmp_path / "render.yml"
    manifest.write_text(
        "services:\n"
        "  fleet-controller:\n"
        "    environment:\n"
        "      DOCKER_HOST: tcp://x:2375\n"
    )
    r = subprocess.run([sys.executable, str(SCRIPT), str(manifest)], capture_output=True, text=True)
    assert r.returncode == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest .github/scripts/tests/test_check_fleet_manifest_containment.py -v`
Expected: FAIL — script does not exist

- [ ] **Step 3: Write minimal implementation**

`.github/scripts/check_fleet_manifest_containment.py`:
```python
"""Assert the rendered compose manifest keeps fleet-controller and governor
inert: no docker.sock mount, no DOCKER_HOST, no crew-orchestrator credential.
The architecture is only real if the deployment manifest proves it.

Usage: check_fleet_manifest_containment.py <rendered-compose.yml>
"""
from __future__ import annotations

import sys

import yaml

WATCHED = ("fleet-controller", "governor")
BANNED_ENV = ("DOCKER_HOST", "ORCHESTRATOR_API_KEY", "CREW_ORCHESTRATOR_API_KEY")


def main(path: str) -> int:
    doc = yaml.safe_load(open(path)) or {}
    services = doc.get("services", {}) or {}
    failures: list[str] = []

    for name in WATCHED:
        svc = services.get(name)
        if not svc:
            print(f"note: {name} not in this manifest (skipped)")
            continue
        for vol in svc.get("volumes", []) or []:
            if "docker.sock" in str(vol):
                failures.append(f"{name}: mounts docker.sock ({vol})")
        env = svc.get("environment", {}) or {}
        keys = env.keys() if isinstance(env, dict) else [e.split("=")[0] for e in env]
        for banned in BANNED_ENV:
            if banned in keys:
                failures.append(f"{name}: has banned env {banned}")

    for f in failures:
        print(f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest .github/scripts/tests/test_check_fleet_manifest_containment.py -v`
Expected: PASS

- [ ] **Step 5: Wire into `agent-safety.yml`**

- In the `suite` job matrix, change `agent: [crew-orchestrator, fleet-controller]` → `agent: [crew-orchestrator, fleet-controller, governor]`.
- In the "Install agent + test dependencies" step, append `fakeredis` to the pip install line.
- Add a new job:
```yaml
  fleet-manifest:
    name: fleet manifest containment
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install
        run: pip install pyyaml pytest cryptography
      - name: Unit-test the checker
        run: python -m pytest .github/scripts/tests/test_check_fleet_manifest_containment.py -q
      - name: Generate a throwaway keypair (config needs the secret file to exist)
        run: python scripts/gen_governor_keypair.py
      - name: Render + check the fleet manifest
        run: |
          docker compose -f docker-compose.yml -f docker-compose.core.yml -f docker-compose.fleet.yml \
            --profile fleet config > /tmp/fleet-render.yml
          python .github/scripts/check_fleet_manifest_containment.py /tmp/fleet-render.yml
```

- [ ] **Step 6: Wire into `docker-push.yml` + `fleet_overlay.yml`**

- `.github/workflows/docker-push.yml` (~line 180, matching the `fleet-controller` entry): add a sibling entry `- name: governor` / `context: ./agents/governor`.
- `.github/scripts/fleet_overlay.yml`: add `- governor` to the `roster:` list, after `fleet-controller`.

- [ ] **Step 7: Commit**

```bash
git add .github/
git commit -m "ci: governor test leg + rendered-manifest containment check for fleet-controller & governor"
```

---

## Task 20: Manual smoke test + docs update

**Files:**
- Modify: `CLAUDE.md` (Phase 0-1 table → add governor row, fix the "no compose wiring" reality), `docs/STATUS.md`, `WHATS_DONE.md`
- Create: `docs/NEXT_SESSION_HANDOVER_2026-09-04.md`

- [ ] **Step 1: Bring the stack up**

Run:
```bash
python scripts/gen_governor_keypair.py
docker compose -f docker-compose.yml -f docker-compose.core.yml -f docker-compose.fleet.yml \
  -f docker-compose.secrets.yml --profile fleet up -d --build governor fleet-controller safety-shepherd
docker compose ps governor fleet-controller safety-shepherd
```
Expected: all three `healthy` within ~40s.

- [ ] **Step 2: Happy path — DRY_RUN ALLOW**

```bash
curl -s localhost:8089/v1/capabilities/mint -H 'content-type: application/json' -d '{
  "plan": {"schema_version":1,"mission_id":"smoke_1",
    "requested_actions":[{"action_id":"a1","kind":"compose_profile.preview","profile":"agents"}],
    "constraints":{"allow_profiles":["agents"],"deny_profiles":["prod","gpu"]}},
  "plan_hash":"sha256:smoke","mode":"DRY_RUN","action":"compose_profile.preview","target":"agents"}' | jq
```
Expected: Shepherd returns `ESCALATE` for `docker` (default dangerous) → `minted:false`, `reason` mentions approval. Record an approval, retry:
```bash
curl -s localhost:8089/v1/approvals -d '{"mission_id":"smoke_1","plan_hash":"sha256:smoke","approver_id":"lyndz","decision":"approved","reason":"smoke"}' -H 'content-type: application/json'
# retry the mint — still ESCALATE, still needs 2 for INFRASTRUCTURE_MUTATION; add a second approver
curl -s localhost:8089/v1/approvals -d '{"mission_id":"smoke_1","plan_hash":"sha256:smoke","approver_id":"broski","decision":"approved","reason":"smoke2"}' -H 'content-type: application/json'
```
Retry the mint → `minted:true`, `capability` present, `jti` starts `cap_`.

- [ ] **Step 3: fleet-controller records the capability, never executes**

```bash
CAP=$(… jti token from step 2 …)
curl -s localhost:8094/v1/plans/preview -H 'content-type: application/json' -d "{
  \"schema_version\":1,\"mission_id\":\"smoke_1\",
  \"requested_actions\":[{\"action_id\":\"a1\",\"kind\":\"compose_profile.preview\",\"profile\":\"agents\"}],
  \"constraints\":{\"allow_profiles\":[\"agents\"],\"deny_profiles\":[\"prod\",\"gpu\"]},
  \"capability\":\"$CAP\"}" | jq '.execution, .capability'
```
Expected: `execution.performed == false`; `capability.valid == true`.

- [ ] **Step 4: Kill-switch**

```bash
curl -s -X POST localhost:8089/v1/kill -H "X-Operator-Key: $(cat secrets/api_key.txt)" -d '{"reason":"smoke"}'
# mint again -> minted:false, reason mentions kill-switch
# wait 2 min -> curl localhost:8089/v1/lease -> valid:false
curl -s -X POST localhost:8089/v1/unkill -H "X-Operator-Key: $(cat secrets/api_key.txt)" -d '{"reason":"smoke done"}'
```

- [ ] **Step 5: Sentinel file beats Redis**

```bash
touch governance-control/KILL
curl -s localhost:8089/v1/capabilities/mint … | jq .minted   # false
curl -s -X POST localhost:8089/v1/unkill -H "X-Operator-Key: …" -d '{"reason":"x"}'
curl -s localhost:8089/v1/capabilities/mint … | jq .minted   # STILL false — file present
rm governance-control/KILL
```

- [ ] **Step 6: Shepherd down → fail closed**

```bash
docker compose stop safety-shepherd
curl -s localhost:8089/v1/capabilities/mint … | jq '.minted, .verdict.shepherd_available'   # false, false
docker compose start safety-shepherd
```

- [ ] **Step 7: Replay**

```bash
# verify with burn twice on the same token
curl -s localhost:8089/v1/capabilities/verify -d '{"token":"'"$CAP"'","burn":true,"expected_sub":"fleet-controller","expected_plan_hash":"sha256:smoke","expected_action":"compose_profile.preview","expected_target":"agents","expected_mode":"DRY_RUN"}' -H 'content-type: application/json'
# second call -> valid:false, code:"replayed"
```

- [ ] **Step 8: Full suites green**

Run:
```bash
(cd agents/governor && python -m pytest tests -q)
(cd agents/fleet-controller && python -m pytest tests -q)
(cd agents/safety-shepherd && python -m pytest test_policy.py test_structured_verdict.py -q)
python -m pytest .github/scripts/tests/test_check_fleet_manifest_containment.py -q
```
Expected: all pass.

- [ ] **Step 9: Update docs**

- `CLAUDE.md` "Phase 0-1" table: add a `governor :8089` row; correct the `fleet-controller` row to state it is **now** compose-wired via `docker-compose.fleet.yml` (Phase 0 shipped code-only; Phase 2 added the wiring).
- `docs/STATUS.md`: fleet section — add governor, note the new launch command.
- `WHATS_DONE.md`: new dated entry — Governor + capability tokens (Phase 2), the Phase 0 compose-wiring gap it closed, `execution.performed` still structurally false.
- `docs/NEXT_SESSION_HANDOVER_2026-09-04.md`: state = Phase 2 shipped; next = Phase 1 (typed dispatch queue) or Phase 3 (approval dashboard).

- [ ] **Step 10: Commit**

```bash
git add CLAUDE.md docs/STATUS.md WHATS_DONE.md docs/NEXT_SESSION_HANDOVER_2026-09-04.md
git commit -m "docs: Governor + capability tokens (Phase 2) shipped; fleet-controller now compose-wired"
```

---

## Self-Review

**Spec coverage** (spec §9 "In scope" ↔ tasks):
- `agents/governor/` service + endpoints → Tasks 1, 12, 13, 14
- PASETO v4.public mint/verify, plan_hash binding, TTL, not_before → Tasks 3, 4
- Redis replay store (dedicated DB 3) + revocation → Task 7
- System lease + renew loop → Tasks 9, 15
- Kill-switch (Redis flag + sentinel file, fail-closed) → Task 8
- Transition table, one test per row → Task 5
- Shepherd structured verdict (additive) + back-compat → Task 16
- fleet-controller capability-verify step; `capability` field populated; `performed` stays false → Task 17
- Governance Ledger rows at each hop → Tasks 11, 12, 13, 14 (`ledger_client.record` calls)
- Compose wiring behind `--profile fleet`, no socket/DOCKER_HOST/crew cred → Task 18
- CI negative-capability check on the rendered manifest → Task 19
- Two-person rule for dangerous classes → Task 10
- Contract tests (forged/expired/replayed/hash-mismatch/kill/shepherd-down/performed-false) → Tasks 4, 6, 8, 12, 13, 17, 20
- `docker-push.yml` + `fleet_overlay.yml` + roster → Task 19

**Out of scope** (spec §9) — confirmed *not* present in any task: durable proposal queue, `crew.plan.submit`, approval dashboard UI, any LIVE execution code path, `compose_profile.start`, hash-chained ledger, brain-agent changes, `safety_gate.py` fail-open.

**Placeholder scan:** no "TBD"/"handle edge cases"/"similar to Task N". Every code step has real code. The one deferred decision — governor port `:8089` vs fallback `:8085` — has an explicit check step (Task 18 Step 1).

**Type consistency:**
- `shepherd_client.Verdict` fields (`decision`, `risk_class`, `policy_version`, `event_id`, `shepherd_available`, `fail_closed`) used identically in Tasks 6, 12, 15.
- `capability.mint(...)` keyword signature identical in Tasks 3, 12; `capability.verify(...)` / `VerifyError.code` identical in Tasks 4, 13.
- `transitions.Outcome` (`mint`, `needs_approval`, `capability_mode`, `reason`) identical in Tasks 5, 12.
- `redis_state` function names (`register_use`, `is_revoked`, `revoke`, `revoke_mission`, `is_mission_revoked`) identical in Tasks 7, 8, 13.
- `killswitch.is_killed` / `engage` / `release` identical in Tasks 8, 9, 12, 13, 14, 15.
- fleet-controller `CapabilityView` (`presented`, `valid`, `reason`) defined and consumed in Task 17 only.
- Shepherd `Decision.as_dict()` new keys (`risk_class`, `policy_version`, `reasons`, `allowed_actions`, `blocked_actions`) match what `shepherd_client` parses in Task 6.
