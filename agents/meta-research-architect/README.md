# Meta-Research Architect Hyper Agent

**Phase 1: observe → explain.** One job: poll arXiv on a timer, brief what's new.

No write path to GitHub, infrastructure, secrets, or agent dispatch. It produces
text only. Improvement proposals go through `mission-director` → `fleet-controller`,
never from here.

## What it does

- **Scheduled sweep** (default: weekly) — newest papers in `cs.AI, cs.LG, cs.MA, cs.NE`,
  de-duped against a Redis seen-set, top 5 written to a brief.
- **Fan-out** to whichever sinks are configured (each optional, each best-effort):
  - Redis — `SET research:latest`, `PUBLISH hypercode_research`
  - Discord — POST the markdown to a webhook
  - Vault — drop a markdown note so the Obsidian brain graph / RAG ingests it

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | none | liveness |
| GET | `/status` | none | sweep config, next run, sink state, safety facts |
| POST | `/research/brief` | `X-Agent-Key`* | ad-hoc brief for one `{"topic": "..."}` |
| POST | `/research/run-now` | `X-Agent-Key`* | run the scheduled sweep immediately |

\* only enforced when `AGENT_API_KEY` is set.

## Config (env)

| Var | Default | Notes |
|---|---|---|
| `RESEARCH_UPDATE_INTERVAL` | `604800` | sweep cadence, seconds |
| `RESEARCH_ARXIV_CATEGORIES` | `cs.AI,cs.LG,cs.MA,cs.NE` | comma list |
| `RESEARCH_MAX_RESULTS_PER_QUERY` | `25` | fetched per sweep |
| `RESEARCH_TOP_PICKS` | `5` | included in the brief |
| `RESEARCH_RUN_ON_STARTUP` | `true` | one sweep ~30s after boot |
| `RESEARCH_DISCORD_WEBHOOK_URL` | — | falls back to `DISCORD_WEBHOOK_URL` |
| `RESEARCH_VAULT_DIR` | — | e.g. `/vault_inbox/Research` (needs a volume mount) |
| `AGENT_API_KEY` | — | shared-secret gate for the two POST routes |
| `REDIS_URL` | `redis://redis:6379/0` | |

## Run

Wired into `docker-compose.agents.yml` (in `docker-compose.yml`'s `include:`),
`profiles: ["agents"]`. Host port **8101** → container 8095 (8095 is taken by
hyperhealth-api).

```bash
# from HyperCode-V2.4/
docker compose --profile agents up -d --build meta-research-architect
curl -s localhost:8101/status | python -m json.tool
curl -s -XPOST localhost:8101/research/run-now -H "X-Agent-Key: $AGENT_API_KEY"
```

## Test

```bash
cd agents/meta-research-architect
pip install -r requirements.txt pytest
pytest -q            # offline: arXiv + redis are stubbed
```

## Not in Phase 1 (deliberately removed)

`orchestrator_tuner`, `neurodivergent_tutor`, `agent_delegator` / mission-envelope
models, `/missions/plan`. Bring them back only once the sweep→brief loop is proven
and the `fleet-controller` safety spine is fail-closed (see *The Hyper AGI Core Verdict*).
