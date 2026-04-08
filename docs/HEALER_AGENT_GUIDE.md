# 🩺 Healer Agent — Self-Healing Guide

> **Port:** 8008
> **Role:** Monitors + auto-recovers failed services
> **Last Updated:** 2026-03-25

---

## 🧠 What is the Healer Agent?

The Healer is HyperCode's **immune system**. It constantly watches all services and agents — and if something crashes or goes unhealthy, it **automatically fixes it** without you having to do anything.

Think of it like:
> 🏥 "Doctor on call — 24/7, never sleeps, never misses a crash."

---

## ⚡ Quick Check

### Is Healer running?
```bash
curl http://localhost:8008/health
```

### What is it watching right now?
```bash
curl http://localhost:8008/status
```

### Recent healing events:
```bash
curl http://localhost:8008/events
```

---

## 🔁 How Healing Works

```
Healer polls all services every 30s
         ↓
   Service returns non-200 or timeout
         ↓
   Healer logs the incident
         ↓
   Attempts restart (Docker restart policy)
         ↓
   Waits 10s → polls again
         ↓
   If still failing → escalates alert to Grafana
         ↓
   Notifies BROski Terminal with 🔴 status
```

---

## 👁️ What Healer Watches

| Service | Check Type | Interval |
|---------|-----------|----------|
| HyperCode Core (8000) | HTTP GET `/health` | 30s |
| Agent X (8090) | HTTP GET `/health` | 30s |
| Crew Orchestrator (8081) | HTTP GET `/health` | 30s |
| BROski Terminal (3000) | HTTP GET `/` | 60s |
| Redis | TCP ping | 15s |
| PostgreSQL | TCP ping | 15s |
| Grafana (3001) | HTTP GET `/api/health` | 60s |

---

## ⚙️ Configuration

`agents/healer/config.yaml`:
```yaml
healer:
  port: 8008
  poll_interval_seconds: 30
  restart_attempts: 3
  restart_delay_seconds: 10
  alert_on_failure: true
  grafana_webhook: http://localhost:3001/api/webhooks/healer
  services:
    - name: hypercode-core
      url: http://localhost:8000/health
    - name: agent-x
      url: http://localhost:8090/health
    - name: crew-orchestrator
      url: http://localhost:8081/health
```

---

## 🚨 Troubleshooting

| Problem | Fix |
|---------|-----|
| Healer itself is down | `docker restart healer-agent` |
| Healer restart loop | Check Docker logs: `docker logs healer-agent` |
| False positives | Increase `poll_interval_seconds` in config |
| Healer not alerting | Check Grafana webhook URL is correct |

---

## 📊 Healer Metrics in Grafana

Navigate to: `http://localhost:3001` → Dashboard: **"Healer Agent"**

Shows:
- Total healing events per day
- Services by uptime %
- Last 10 incidents + resolutions

---
> **built with WelshDog + BROski 🚀🌙**
