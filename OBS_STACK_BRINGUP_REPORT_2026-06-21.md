# 📊 Observability Stack Bring-Up — Session Report

> **Date:** 2026-06-21 · **Repo:** HyperCode-V2.4 · **By:** @welshDog + Claude
> **Goal:** Diagnose why Grafana wasn't running and bring it up on `:3001`
> **Outcome:** ✅ Full local obs stack LIVE + healthy. Nothing was rebuilt.

---

## 🎯 TL;DR

The obs stack wasn't broken — it was just **never started**. It lives behind the
`--profile observability` gate (RAM-saver default on this box), so the everyday
`up -d` skips it. One wired secret + one profiled launch = Grafana live on `:3001`.

---

## 🔍 What We Found (diagnosis)

### 1. Two competing obs compose files
| File | Verdict |
|---|---|
| **`docker-compose.observability.yml`** | ✅ **CANONICAL** — `include:`d by root `docker-compose.yml`, profile `observability`, on `obs-net` (+ external `agents-net`/`data-net`). Grafana `13.0.1`, full Prom↔Loki↔Tempo↔Pyroscope correlation + P1-2 governance Postgres datasource. |
| `docker-compose.monitoring.yml` | ⚠️ **LEGACY standalone** — NOT included by root, no profile, on `hypercode_public_net`. Same container names + host port `3001` → **would conflict**. Do not run. |
| `docker-compose.grafana-cloud.yml` | ☁️ Cloud push agent (ships to grafana.net) — separate path, no local UI. |

> The other 9 compose files that mention "prometheus/grafana" only reference scrape
> labels/env — they don't define the services.

### 2. Container state at start
- **~30 core containers** running + healthy (core, agents, brain cluster, redis, postgres, minio, chroma).
- **0 obs containers** existed (grafana, prometheus, loki, tempo, promtail, alertmanager, node-exporter, cadvisor, pyroscope, celery-exporter — all absent).
- `minio` + `chroma` (the non-gated deps in observability.yml) were already up → confirmed the file works, only the profiled services were missing.

### 3. Infra pre-checks — all green
- `HC_DATA_ROOT=H:\HyperStation zone\HyperCode\HyperCodeData` → all 7 bind-mount dirs exist ✅
- External nets `hypercode_obs_net` / `hypercode_agents_net` / `hypercode_data_net` all exist ✅
- `hypercode_public_net` (legacy file's net) does NOT exist → confirms `monitoring.yml` has never been used ✅
- Datasource provisioning complete: Prometheus / Loki / Tempo / Pyroscope + P1-2 `HyperCode Postgres` (governance ledger) ✅

### 4. 🪤 The real gotcha — Grafana password wiring gap
- `secrets/grafana_admin_password.txt` (32 chars) + `grafana_admin_user.txt` **exist and are populated**.
- BUT `observability.yml` reads the password from the **env var** `${GF_SECURITY_ADMIN_PASSWORD}` — **not** from the `__FILE` secret.
- `.env` only had a **comment** (line 98), no real assignment → Grafana would have booted on **admin/admin**.

---

## 🔧 What We Did (actions)

1. **Wired the password** — added a real `GF_SECURITY_ADMIN_PASSWORD=` line to `.env`,
   sourced from `secrets/grafana_admin_password.txt` (done in PowerShell so the secret
   never hit the chat log). `GF_SECURITY_ADMIN_USER=lyndzwills` was already set.
2. **Launched the profile** — `.\hyperlaunch.ps1 --profile observability up -d`.
3. **Verified health** — hit `/api/health` from host + inside the container; confirmed
   datasources + alert rules firing.
4. **Banked the knowledge** — wrote a memory note so the gotchas don't repeat.

---

## ✅ Final State

| Service | Status |
|---|---|
| grafana | ✅ Up (healthy) — `http://127.0.0.1:3001` |
| prometheus | ✅ healthy |
| loki | ✅ healthy |
| tempo | ✅ healthy |
| pyroscope | ✅ up |
| promtail | ✅ healthy |
| node-exporter | ✅ healthy |
| cadvisor | ✅ healthy |
| alertmanager | ✅ healthy (already firing `crew_orchestrator_down` + `smoke_failures_detected`) |
| celery-exporter | ✅ healthy |
| hypercode-core | ✅ healthy (see OOM note) |

**Login:** `lyndzwills` / secret-file password · **Health:** `{"database":"ok","version":"13.0.1"}`

---

## ⚠️ Notes & Risks

- **OOM risk (4.8 GB Docker):** during bring-up, `hypercode-core` got **exit 137 (OOM kill)**
  — obs stack on top of core+agents hit the memory ceiling. Its `restart: unless-stopped`
  recovered it (now healthy). If core flaps again → bump Docker Desktop memory or drop a profile.
- **Grafana `(unhealthy)` for first ~40s** is a false negative during the DB-startup
  `start_period`; flips healthy once `/api/health` returns `database: ok`.
- **Local ≠ Cloud:** `http://127.0.0.1:3001` = local (IDE/agents + all provisioned dashboards).
  `https://hypercode.grafana.net/` = Cloud, push-only via `grafana-agent` — provisioned
  dashboards are NOT there.
- **`.env` change stays local** — Sacred Rule: never commit `.env`. Nothing to push.

---

## 🔁 Reproduce / Restart

```powershell
cd H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4
.\hyperlaunch.ps1 --profile observability up -d
Start-Process http://127.0.0.1:3001
```

> 🐶♾️ Built by @welshDog · Llanelli, Wales · *"Stop apologising for your brain. Start building."*
