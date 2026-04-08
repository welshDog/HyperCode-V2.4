# ⚡ HyperCode V2.0 — Daily Ops Guide

> Quick reference for keeping the stack LEGENDARY 🦅

---

## 🌅 Morning Startup

```powershell
# 1. Check everything's up
python scripts/hypercode_health_check.py

# 2. If Redis/Postgres are down
docker-compose up -d redis postgres

# 3. If any agent is down
docker-compose up -d
```

---

## 🔍 Quick Checks

```powershell
# See all running containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check a specific service log
docker logs <container-name> --tail 50

# Restart one service
docker-compose restart <service-name>
```

---

## 🚨 Emergency Commands

```powershell
# Full restart everything
docker-compose down && docker-compose up -d

# Nuke and rebuild (last resort)
docker-compose down -v && docker-compose up -d --build

# Check disk space
docker system df

# Clean unused images
docker image prune -f
```

---

## 📊 Service Ports Cheatsheet

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Dashboard | http://localhost:8088 |
| Mission UI | http://localhost:8099 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |
| Ollama | http://localhost:11434 |
| MCP Gateway | http://localhost:8820 |

---

## 🏆 Target: Stay LEGENDARY (90%+)

- ✅ All 17 HTTP services green
- ✅ Redis + Postgres healthy
- ✅ 38+ containers running
- ✅ Health check score 20+/22

---

🏴󠁧󠁢󠁷󠁬󠁳󠁿 **Built by @welshDog — HyperFocus Zone, Llanelli, Wales** 🦅♾
