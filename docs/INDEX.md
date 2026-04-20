# 📖 HyperCode V2.4 — Docs Index

**Status:** Active  
**Last Updated:** 2026-04-20  
**Applies To:** HyperCode v2.4.2

> **Start here.** One file. Links to everything.
> 32/32 containers 🟢 | Grade A 🏅 | Prometheus/Grafana/Tempo live | DLQ + priority queues live ✅

---

## ⚡ New? Start Here

| What you need | Go to |
|---|---|
| Current status snapshot (update every session) | [WHATS_DONE.md](../WHATS_DONE.md) |
| Project brain + sacred rules | [CLAUDE.md](../CLAUDE.md) |
| Get the system running fast | [QUICKSTART.md](QUICKSTART.md) |
| Full setup from scratch | [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) |
| Day-to-day ops commands | [DAILY_OPS.md](DAILY_OPS.md) |
| Something broke | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| BROski terminal commands | [BROSKI_TERMINAL_GUIDE.md](BROSKI_TERMINAL_GUIDE.md) |
| Onboarding a new dev | [ONBOARDING.md](ONBOARDING.md) |

---

## 🏗️ Architecture & System Design

| Doc | What it covers |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full system architecture — networks, services, data flow |
| [COMPLETE_PORTS_LIST.md](COMPLETE_PORTS_LIST.md) | Every port in the stack (3100–3599 range) |
| [DOCKER_HEALTH_REPORT_v2.4.md](DOCKER_HEALTH_REPORT_v2.4.md) | Docker health snapshot |
| [DOCKER_INFRA_OPTIMIZATION.md](DOCKER_INFRA_OPTIMIZATION.md) | Build cache, prune strategy, disk tips |
| [DOCKER_MODEL_RUNNER.md](DOCKER_MODEL_RUNNER.md) | Local LLM via Docker Model Runner |
| [MAPE_K_INTEGRATION.md](MAPE_K_INTEGRATION.md) | Self-healing MAPE-K loop design |
| [MCP_GATEWAY_OPERATIONAL_GUIDE.md](MCP_GATEWAY_OPERATIONAL_GUIDE.md) | MCP gateway full ops guide |
| [MCP_IDE_INTEGRATION.md](MCP_IDE_INTEGRATION.md) | Wiring MCP to your IDE |
| [MCP_QUICK_START.md](MCP_QUICK_START.md) | MCP up and running in minutes |

---

## 🤖 Agents

| Doc | What it covers |
|---|---|
| [AGENT_X_GUIDE.md](AGENT_X_GUIDE.md) | Agent X — the agent that builds agents |
| [HEALER_AGENT_GUIDE.md](HEALER_AGENT_GUIDE.md) | Healer — self-healing + auto-recovery |
| [CREW_ORCHESTRATOR.md](CREW_ORCHESTRATOR.md) | Crew Orchestrator — multi-agent task routing |
| [SKILLS_GUIDE.md](SKILLS_GUIDE.md) | Agent skills catalogue |
| [THROTTLE_AGENT_CODE_REVIEW.md](THROTTLE_AGENT_CODE_REVIEW.md) | Throttle Agent deep code review |
| [THROTTLE_AGENT_HEALTH_CHECK.md](THROTTLE_AGENT_HEALTH_CHECK.md) | Throttle Agent health check |
| [docs/agents/](agents/) | All individual agent docs |
| [docs/hyper-agents/](hyper-agents/) | Hyper-specialist agent docs |

---

## 💳 Stripe & Payments

| Doc | What it covers |
|---|---|
| [API.md](API.md) | All live API endpoints incl. `/api/stripe/*` |
| [SECRETS.md](SECRETS.md) | Env vars + secrets management |
| [docs/integrations/](integrations/) | Stripe + payment integration docs |

**Live Stripe endpoints:**
```
POST /api/stripe/checkout    → Checkout session (token packs + subscriptions)
GET  /api/stripe/plans       → Plan list
POST /api/stripe/webhook     → Stripe event handler (rate-limit exempt)
```

---

## 🔒 Security

| Doc | What it covers |
|---|---|
| [SECURITY.md](SECURITY.md) | Security policy + reporting vulns |
| [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md) | Full audit report |
| [SECRETS.md](SECRETS.md) | Secrets management — Docker secrets + .env |
| [AUTO_FIXES_APPLIED.md](AUTO_FIXES_APPLIED.md) | Automated security fixes log |
| [BLOCKERS_FIXED.md](BLOCKERS_FIXED.md) | Blockers resolved log |

**Security standards (Phase 7–9):**
- Non-root containers ✅
- `docker-ce-cli` (not `docker.io`) ✅
- `apt-get upgrade -y` + pip pinning in all Dockerfiles ✅
- `data-net` + `obs-net` internal-only ✅
- Trivy target: 0 CRITICAL, <5 HIGH per image ✅
- Trivy CI runs without GitHub Advanced Security dependencies (no SARIF upload) ✅

---

## 📊 Observability

| Doc | What it covers |
|---|---|
| [OBSERVABILITY_QUICK_START.md](OBSERVABILITY_QUICK_START.md) | Grafana/Loki/Tempo up fast |
| [OBSERVABILITY_DELIVERY_SUMMARY.md](OBSERVABILITY_DELIVERY_SUMMARY.md) | Full observability delivery |
| [OBSERVABILITY_EXEC_SUMMARY.md](OBSERVABILITY_EXEC_SUMMARY.md) | Exec-level summary |
| [TEMPO_FIX_GUIDE.md](TEMPO_FIX_GUIDE.md) | Tempo tracing fix guide |

**Stack:** Prometheus • Grafana • Loki • Tempo • Promtail — all on `obs-net` (internal)

---

## 🚀 Deployment

| Doc | What it covers |
|---|---|
| [DEPLOYMENT.md](DEPLOYMENT.md) | Standard deployment steps |
| [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | Full deployment guide |
| [deployment-guide.md](deployment-guide.md) | Alt deployment guide |
| [HYPERLAUNCH.md](HYPERLAUNCH.md) | HyperLaunch sequence |
| [docs/deployment/](deployment/) | All deployment sub-docs |

**Quick stack start:**
```powershell
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```

---

## 🧪 Testing

| Doc | What it covers |
|---|---|
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Test suite guide |
| [benchmarks.md](benchmarks.md) | Performance benchmarks |

**Run tests:**
```powershell
pytest backend/tests/ -v
pytest backend/tests/test_stripe.py -v
pytest backend/tests/test_uplink_ws.py -v
```

---

## 📈 Roadmap & Status

| Doc | What it covers |
|---|---|
| [CHANGELOG.md](CHANGELOG.md) | Full version history |
| [RELEASE_NOTES_v2.4.md](RELEASE_NOTES_v2.4.md) | v2.4.0 release notes (historical) |
| [AI_EVOLUTION_ROADMAP_2025-2027.md](AI_EVOLUTION_ROADMAP_2025-2027.md) | 2-year AI evolution plan |
| [PRODUCTION_UPGRADE_ROADMAP.md](PRODUCTION_UPGRADE_ROADMAP.md) | Production upgrade path |
| [VISION_AND_METRICS.md](VISION_AND_METRICS.md) | Vision + success metrics |
| [FINAL_STATUS_AND_ROADMAP.md](FINAL_STATUS_AND_ROADMAP.md) | Current status snapshot |
| [PROJECT_HEALTH_STATUS.md](PROJECT_HEALTH_STATUS.md) | Live health indicators |

---

## 🤝 Contributing

| Doc | What it covers |
|---|---|
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community standards |
| [DEVELOPER_CALL_TO_ACTION.md](DEVELOPER_CALL_TO_ACTION.md) | Join the build |
| [hey-thanks-for-looking.md](hey-thanks-for-looking.md) | Welcome note for new explorers 👋 |

---

## 📦 Other Key Docs

| Doc | What it covers |
|---|---|
| [RUNBOOK.md](RUNBOOK.md) | Incident runbook |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Quick reference card |
| [MAINTENANCE_UPGRADES.md](MAINTENANCE_UPGRADES.md) | Maintenance + upgrade log |
| [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md) | All integration summaries |
| [HYPERSTATION_DASHBOARD_PROJECT_PLAN.md](HYPERSTATION_DASHBOARD_PROJECT_PLAN.md) | Dashboard project plan |
| [HyperStation_User_Guide.md](HyperStation_User_Guide.md) | User guide for HyperStation |
| [broski-bot-integration-spec-confirmed.md](broski-bot-integration-spec-confirmed.md) | BROski bot integration spec |
| [docs/archive/](archive/) | Old docs — historical reference only |

---

## 🗂️ Doc Folders

| Folder | Contents |
|---|---|
| [agents/](agents/) | Individual agent documentation |
| [api/](api/) | API reference docs |
| [architecture/](architecture/) | Architecture deep-dives |
| [archive/](archive/) | Old/superseded docs |
| [claude-integration/](claude-integration/) | Claude AI integration guides |
| [community/](community/) | Community docs |
| [configuration/](configuration/) | Config reference |
| [deployment/](deployment/) | Deployment sub-docs |
| [development/](development/) | Dev workflow docs |
| [features/](features/) | Feature docs |
| [getting-started/](getting-started/) | New user guides |
| [guides/](guides/) | How-to guides |
| [health-reports/](health-reports/) | Historical health reports |
| [hyper-agents/](hyper-agents/) | Hyper-specialist agents |
| [infra/](infra/) | Infrastructure docs |
| [integrations/](integrations/) | Third-party integrations |

---

## 📌 Key Rules (never re-debate)

```
✔ docker-ce-cli — NEVER docker.io for socket agents
✔ from app.X import Y — NEVER from backend.app.X
✔ FastAPI: public routes BEFORE auth-gated routes
✔ Stripe webhook = rate-limit EXEMPT
✔ data-net + obs-net = internal: true
✔ .env files NEVER committed
✔ Conventional commits: feat: fix: docs: chore:
✔ Trivy: 0 CRITICAL target per image
```

---

<div align="center">

**32/32 containers 🟢 | Grade A 🏅 | Independent Docker AI audit: world-class infrastructure**

*Built for ADHD brains. Fast feedback. Real tools. No fluff.* 🧠⚡

*@welshDog — Lyndz Williams, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿*

