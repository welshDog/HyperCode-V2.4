# 🧠 MAPE-K Engine Integration Guide

> Phase 1 of HyperCode V2.0 Self-Healing Upgrade

---

## ⚡ What Is MAPE-K?

MAP-K = **Monitor → Analyze → Plan → Execute + Knowledge Base**

It's the industry-standard loop for autonomous self-healing systems.
Your Healer Agent now has this loop running every 10 seconds! 🔥

---

## 🚀 Wiring Into main.py (ONE-TIME SETUP)

Add these 3 lines to `agents/healer/main.py`:

```python
# At the top
from mape_k_bootstrap import start_mape_k

# In your startup event
@app.on_event("startup")
async def startup():
    await start_mape_k(app)  # 🧠 MAPE-K ONLINE!
```

That's it. The engine starts, registers API routes, and polls every 10s.

---

## 📡 New API Endpoints

| Endpoint | What It Shows |
|----------|---------------|
| `GET /mape-k/status` | Current anomaly scores + engine stats |
| `GET /mape-k/history` | Recent healing events (what broke + fix) |
| `GET /mape-k/metrics` | Grafana-friendly metrics |

---

## 🔬 How Anomaly Detection Works

**Z-Score method** (Phase 1 — simple but powerful):

```
Z = |response_time - mean| / std_deviation

Z > 3.0 = anomaly (3-sigma rule = 99.7% confidence)
```

- Needs 10+ data points before activating
- Tracks rolling 60-point history per service
- ZERO external dependencies — pure Python stdlib!

---

## ⚙️ Heal Action Priority

```
1. HTTP soft restart  → POST to /restart endpoint (< 5s)
2. Docker restart     → docker compose restart (< 30s)
3. Alert only         → Log + notify (non-critical services)
4. No action          → Cooldown active (60s between heals)
```

---

## 📊 Key Metrics To Watch

| Metric | Target |
|--------|--------|
| `mape_k_auto_fix_success_rate_pct` | > 80% |
| `mape_k_avg_mttr_seconds` | < 30s |
| `mape_k_heals_last_hour` | Low = stable stack |

---

## 🗺️ Phase Roadmap

- ✅ **Phase 1** — MAPE-K + Z-score anomaly detection (DONE! 🔥)
- 🔜 **Phase 2** — Isolation Forest ML anomaly detection
- 🔜 **Phase 3** — Agent X evolutionary upgrade loop
- 🔜 **Phase 4** — PostgreSQL knowledge base persistence

---

🏴󠁧󠁢󠁷󠁬󠁳󠁿 **Built by @welshDog — HyperFocus Zone, Llanelli, Wales** 🦅♾
