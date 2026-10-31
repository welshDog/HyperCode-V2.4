# Pattern review: `governor` (2026-10-31, schema 2)

Second review of `agents/governor`, using the schema 2 tooling (verifiable content hashes, compose and
Python-module signals). Supersedes the 2026-10-29 packet for review purposes; that folder stays as the
record of the first approval.

| File | What it is |
|---|---|
| `governor_inventory.json` | Inventory of `agents/governor`, **schema 2**: 14 manifests (Dockerfile, requirements, 12 Python modules), complete, no withheld content hashes. |
| `governor_approval.json` | Human approval `governor-2026-10-31-lyndz` (approved by Lyndz, 2026-10-31T13:10:24Z), bound to inventory digest `c5a21bfd8d09fa8e…a506`. |
| `governor_packet.json` | Review packet built from the two files above: 4 candidates, `pending_human_review`, synthesis and execution **not** authorised. |
| `governor_decisions.json` | The human decision record for that packet: all four candidates accepted (2026-10-31). |

## Status

- **Decisions recorded 2026-10-31: all four candidates ACCEPTED by Lyndz** (`governor_decisions.json`,
  format `hypercode.pattern-decisions.v1`, produced with the dashboard's own export code; each decision is
  bound to a hash of the exact candidate). The record is unsigned. Accepting a candidate marks it as a
  reviewed, true fact about the source. It does **not** authorise synthesis or execution
  (`synthesis_authorized` and `execution_authorized` stay `false`); a future synthesis stage would need
  its own explicit authorisation.
- The approval is a local record, not a cryptographic identity. It only authorises building a *review
  packet*, never synthesis or execution.

## Candidates, and what was checked on 2026-10-31

| Candidate | Checked against the source | Reviewer's recommendation (decision: accepted) |
|---|---|---|
| `container-build-hardening-signals` | Dockerfile has a builder and a runtime stage, `USER appuser`, `HEALTHCHECK`. | Accept (static hint only). |
| `declared-language-ecosystems` | `requirements.txt`: fastapi, uvicorn, pydantic, httpx, pyseto, redis, cryptography. | Accept (low value). |
| `capability-boundary-signals` | Independent `grep`: no docker client, subprocess, `os.system`, eval or pickle. `pyseto` in `capability.py` and `keys.py`; `httpx` in `ledger_client.py` and `shepherd_client.py`. | Accept, the most useful one. |
| `python-module-surface` | All 9 routes confirmed against the decorators in `main.py`. | Accept, with the auth caveat below. |

These are recommendations, not decisions.

## Findings from the review that the packet cannot express

Recorded so they are not lost; none is a decision about the packet.

- **Route auth.** Operator key (constant-time compare, key from a secret file) protects `revoke`, both
  `approvals` routes, `kill` and `unkill`. `health`, `lease`, `capabilities/mint` and `capabilities/verify`
  have no caller check in the app; `mint` is gated by plan validation, the Shepherd verdict, kill switch,
  approvals and lease, and the service is published on `127.0.0.1:8089` only. Decide whether that is
  deliberate. `inter_agent_key` and `agent_api_key_governor` are mounted, but no inbound check using
  them was found in `main.py` (they may be for outbound calls: unconfirmed).
- **Runtime (live container and `docker-compose.fleet.yml`).** Good: non-root, `cap_drop: ALL`,
  `no-new-privileges`, not privileged, no host network, no Docker socket, all mounts read-only
  (including the kill-switch directory). Gaps: writable root filesystem, no memory or CPU limit, and an
  `API_KEY: ${API_KEY:-}` environment line (empty today) that could carry the master key into the service.
- **Dockerfile.** The builder stage runs `pip wheel --no-deps`, so transitive dependencies are still
  fetched at install time; dependencies are unpinned (`>=`) with no lock file; `curl` is installed only for
  the healthcheck; `uvicorn[standard]` pulls extra packages.
- **Tool gap.** The Governor's compose service lives in `docker-compose.fleet.yml`, outside the scanned
  folder, so the packet has no `compose-hardening-declarations` candidate. The hardening above was
  checked by hand.

## Re-checking

```
python scripts/architecture_inventory.py agents/governor
```

Compare with `governor_inventory.json` (identical while the Governor source is unchanged). To rebuild the packet:

```
python scripts/pattern_review.py reports/pattern-review/governor-2026-10-31/governor_inventory.json \
  --approval reports/pattern-review/governor-2026-10-31/governor_approval.json \
  --output <somewhere>/governor_packet.json
```

`content_sha256` is the SHA-256 of the file with CRLF normalised to LF, so it can be checked against the
real file. `sha256` in an evidence entry is only an alias of `metadata_sha256` (a hash of the extracted
facts, not of the file).
