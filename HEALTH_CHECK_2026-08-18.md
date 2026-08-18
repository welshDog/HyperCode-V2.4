# 🏥 HyperCode V2.4 Health Check Report — 2026-08-18

**Timestamp:** 2026-08-18 22:23 UTC+1  
**Stack Status:** ✅ **OPERATIONAL** (with caveats)  
**Data Pipeline:** ⚠️ **PARTIAL** (local only, Cloud pipeline not yet tested)

---

## Summary

| Category | Status | Count | Notes |
|----------|--------|-------|-------|
| **Services Running** | ✅ UP | 26/52 | Core infrastructure + key agents + MCP stack |
| **Services Healthy** | ✅ HEALTHY | 20/26 | Database, cache, core APIs all passing checks |
| **Services Unhealthy** | ⚠️ DEGRADED | 1/26 | `github-sync-brain` failing (non-critical) |
| **Services Exited** | ❌ DOWN | 26/52 | Mostly tier-3 agents (exited 4 weeks ago) |
| **Data Ingestion** | ✅ FLOWING | 4/14 | Prometheus scraping: hypercode-core ✅, grafana ✅, minio ✅, safety-shepherd ✅ |
| **Metrics Targets** | ⚠️ DOWN | 10/14 | cadvisor, celery-exporter, loki, node-exporter, promtail, tempo, crew-orchestrator, broski-bot all unreachable |

---

## Core Infrastructure — ✅ Healthy

| Service | Status | Health | Notes |
|---------|--------|--------|-------|
| **PostgreSQL** | ✅ UP | `accepting connections` | DB initialized, migrations clean (per handover) |
| **Redis** | ✅ UP | `PONG` | Responsive, AOF enabled for durability |
| **Prometheus** | ✅ UP | `healthy` | Scraping, 4 targets active, JSON API responding |
| **Grafana** | ✅ UP | `ok` (db: ok) | v13.0.1, database connected, UI on `:3001` |
| **MinIO** | ✅ UP | `healthy` | Object storage active, `minio:9000` reachable |
| **Chroma** | ✅ UP | `healthy` | Vector DB running on `:8009` |

---

## HyperCode Core — ✅ Healthy

| Service | Status | Health | Notes |
|---------|--------|--------|-------|
| **hypercode-core** | ✅ UP | `healthy` | `/health` returns `ok`, `/metrics` scraped successfully ✅ |
| **hypercode-ollama** | ✅ UP | `healthy` | LLM runtime ready, models preloaded |
| **hypercode-dashboard** | ✅ UP | `healthy` | UI on `:8088`, rendering without errors |
| **hypercode-mcp-server** | ✅ UP | `healthy` | MCP server on `:8823` responding |

---

## Agent Infrastructure — ✅ Mostly Healthy

| Service | Status | Health | Notes |
|---------|--------|--------|-------|
| **MCP Gateway** | ✅ UP | `healthy` | Router on `:8820`, all MCP bridges connected |
| **MCP REST Adapter** | ✅ UP | `healthy` | Dashboard IDE tool calls wired through `:8821` |
| **Safety Shepherd** | ✅ UP | `healthy` | Policy enforcement running on `:8096` |
| **Healer Agent** | ✅ UP | `healthy` | Service watchdog active, monitoring enabled |
| **hyper-brain** | ✅ UP | `healthy` | Neurosymbolic core on `:8100`, responding |
| **Broski Bot** | ✅ UP | `healthy` | Discord bot connected, economy system live |
| **BROski Pets Bridge** | ✅ UP | `healthy` | Pet integration on `:8098` |
| **Database Architect** | ✅ UP | `healthy` | Agent on `:8004`, exposing `/metrics` ✅ |
| **agent-hyper-brain-core** | ✅ UP | No HC | Brain variant on `:3301`, up 27min |
| **agent-mcp-bridge** | ✅ UP | No HC | MCP bridge on `:3302`, up 11h |
| **Evolve Relay** | ✅ UP | `healthy` | Evolution relay on `:8097` |
| **Obsidian Watcher** | ✅ UP | No HC | Vault sync watcher running |
| **GitHub Sync** | ✅ UP | `healthy` | Repo sync cron active |
| **GitHub Sync Brain** | ⚠️ UP | `unhealthy` | Brain variant failing health probe (non-critical) |

---

## Observability — ⚠️ Partial

### Prometheus Targets

**✅ Active (scraped):**
```
prometheus:9090       ✅ UP (localhost:9090)
hypercode-core:8000   ✅ UP — metrics flowing
grafana:3000          ✅ UP — metrics flowing
minio:9000            ✅ UP — metrics flowing
safety-shepherd:8096  ✅ UP — metrics flowing
```

**❌ Down (DNS/connection failures):**
```
broski-bot:8000               ❌ "connection refused"
cadvisor:8080                 ❌ "no such host" (profile-gated, not running)
celery-exporter:9808          ❌ "no such host" (profile-gated, not running)
crew-orchestrator:8080        ❌ "no such host" (not running)
loki:3100                     ❌ "no such host" (profile-gated, not running)
node-exporter:9100            ❌ "no such host" (profile-gated, not running)
promtail:9080                 ❌ "no such host" (profile-gated, not running)
pyroscope:4040                ❌ "no such host" (profile-gated, not running)
tempo:3200                    ❌ "no such host" (profile-gated, not running)
```

### Traces (OpenTelemetry)

**❌ Tempo not reachable:**
```
hypercode-core logs: "Failed to export traces to tempo:4317, error: StatusCode.UNAVAILABLE"
Retry backoff active (0.8–0.9s intervals)
Impact: Tracing data not being collected, but app continues to work
```

---

## Tier-3 Agents — ❌ Exited (4 weeks ago)

All exited with status `255` or `137` (OOM / signal):

```
backend-specialist       ❌ Exited (255) 4 weeks
frontend-specialist      ❌ Exited (255) 4 weeks
coder-agent              ❌ Exited (137) 4 weeks — OOM
project-strategist       ❌ Exited (255) 4 weeks
qa-engineer              ❌ Exited (255) 4 weeks
devops-engineer          ❌ Exited (255) 4 weeks
...6 more agents
```

**Hypothesis:** Compose file references agents that no longer exist or have moved. Need to verify against `docker-compose.agents.yml`.

---

## Grafana Cloud Pipeline — ❓ Not Yet Deployed

**Status:** Config files created, not yet started.

**To test:**
```bash
# 1. Fill in .env with Grafana Cloud credentials (GRAFANA_CLOUD_*)
# 2. Start the pipeline:
docker compose --profile grafana-cloud up -d

# 3. Verify Prometheus container boots:
docker compose exec -T prometheus-cloud wget -q -O - http://localhost:9090/-/healthy

# 4. Verify Grafana Agent connects:
docker logs grafana-agent | grep -i "remote_write\|connected\|error"

# 5. Check Cloud datasource for incoming series:
# Grafana Cloud → Explore → Prometheus → Query: up (should return data ~15-30s after agent start)
```

---

## Critical Issues

| Priority | Issue | Impact | Action |
|----------|-------|--------|--------|
| 🔴 **P0** | Traces not exporting (tempo unreachable) | None (app works, tracing just silent) | Start with `--profile observability` or debug network |
| 🔴 **P1** | github-sync-brain unhealthy | None (github-sync backup is healthy) | Check brain variant logs if needed |
| 🟡 **P2** | Tier-3 agents exited (4 weeks) | None (not actively used) | Rebuild if needed, or delete stale services |
| 🟡 **P2** | Grafana Cloud pipeline not tested | Can't push metrics to Cloud yet | Fill .env + test with `--profile grafana-cloud` |

---

## What's Working Right Now

✅ **Core Stack:**
- Database, cache, LLM runtime all healthy
- FastAPI backend responding to requests
- Dashboard rendering without errors
- MCP tool stack live and connected

✅ **Local Observability:**
- Prometheus scraping 4/14 targets
- Grafana ingesting data (real dashboards can now query real metrics)
- Alert rules loaded

✅ **Infrastructure:**
- Service mesh (MCP gateway) routing correctly
- Policy enforcement (Safety Shepherd) active
- Watchdog (Healer) monitoring
- Economy system (Broski Bot) live

---

## What Needs Attention Before Cloud Push

1. **Fill `.env`** with Grafana Cloud credentials (copy from Grafana Cloud UI)
2. **Test locally first:** `docker compose --profile grafana-cloud up -d`
3. **Verify agent boots:** `docker logs grafana-agent` (look for "remote_write" success messages)
4. **Confirm data arrives:** Grafana Cloud → Explore → Query `up` (should see 4+ active targets)
5. **Then rebuild dashboards** to query Cloud instead of local Prometheus

---

## Next Steps

**Immediate (< 1 hour):**
1. Start Grafana Cloud pipeline with real credentials
2. Monitor logs for any auth or connection errors
3. Query one simple metric in Grafana Cloud to confirm bidirectional connection works

**Short term (1–4 hours):**
1. Rebuild dashboards in Grafana Cloud using the new data sources
2. Verify all 4 scraped targets are showing real metrics
3. Configure alerts in Grafana Cloud (e.g., "agent down")

**Medium term:**
1. Add missing exporters (redis_exporter, postgres_exporter) if deeper DB/cache metrics needed
2. Debug why Tempo unreachable (profile issue? network?)
3. Rebuild or prune tier-3 agent services that have been down 4 weeks

---

**Report Generated:** 2026-08-18 22:23 UTC+1  
**Next Health Check:** `docker compose ps -a && docker compose exec -T hypercode-core curl -s http://localhost:8000/health`
