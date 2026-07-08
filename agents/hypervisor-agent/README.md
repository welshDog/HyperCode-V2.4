# 🧬 HyperVisor Agent — Real-Time Resource Guardian

**The missing piece for laptop container orchestration.**

HyperVisor is an intelligent monitoring and auto-scaling agent that watches your CPU, RAM, and disk in real-time, predicts OOM crashes before they happen, and automatically heals your system.

---

## 🎯 What It Does

### **Real-Time Metrics**
- System-wide CPU, RAM, disk monitoring (live via WebSocket)
- Per-container resource tracking (CPU%, memory%, restart counts)
- Trend analysis & OOM prediction (5-minute forecast via linear regression)

### **Intelligent Alerting**
- Configurable thresholds (CPU warn/crit, RAM warn/crit, disk)
- Smart alert cooldown (doesn't spam you)
- Multi-channel: Redis, Discord webhook, WebSocket stream
- Alert levels: `info`, `warn`, `crit`

### **Auto-Scaling Rules**
- **Kill zombies**: Containers restarting 10+ times (failed rollout)
- **Stop non-critical on memory pressure**: Pause Grafana/Prometheus/Loki when RAM > 90%
- **Prevent cascading failures**: One failing container won't drag down the whole system

### **Production-Grade**
- Non-root user (security hardening)
- Health checks + graceful shutdown
- Resource-bounded (256MB RAM cap)
- Integrates with Crew Orchestrator + existing agent stack

---

## 🚀 Quick Start

### 1. **Deploy HyperVisor**
```bash
cd HyperCode-V2.4

# Start HyperVisor alongside your agents
docker compose -f docker-compose.core.yml \
               -f docker-compose.hyper-agents.yml \
               up -d hypervisor-agent
```

### 2. **Monitor via CLI**
```bash
# Check status
python agents/hypervisor-agent/cli.py status

# View current metrics
python agents/hypervisor-agent/cli.py metrics

# Watch live (WebSocket stream)
python agents/hypervisor-agent/cli.py watch

# See active alerts
python agents/hypervisor-agent/cli.py alerts

# Trigger auto-scaling
python agents/hypervisor-agent/cli.py scale
```

### 3. **Check REST API**
```bash
# Health
curl http://127.0.0.1:8094/health

# Metrics (JSON)
curl http://127.0.0.1:8094/metrics | jq

# Alerts
curl http://127.0.0.1:8094/alerts | jq

# WebSocket stream (real-time)
wscat -c ws://127.0.0.1:8094/ws/metrics
```

---

## ⚙️ Configuration

Environment variables (set in `docker-compose.hyper-agents.yml`):

```yaml
AGENT_NAME: hypervisor-01              # Agent identifier
AGENT_PORT: "8094"                    # Listen port
REDIS_URL: redis://redis:6379         # Alert cache + metrics
DOCKER_SOCKET: unix:///var/run/docker.sock  # Docker API access

# Thresholds (%)
CPU_THRESHOLD_WARN: "70"
CPU_THRESHOLD_CRIT: "90"
RAM_THRESHOLD_WARN: "75"
RAM_THRESHOLD_CRIT: "90"
DISK_THRESHOLD_WARN: "80"

# OOM prediction window (seconds)
OOM_PREDICTION_WINDOW: "300"

# Discord alerts (optional)
DISCORD_WEBHOOK: "https://discordapp.com/api/webhooks/..."
```

---

## 📊 Metrics Explained

### System Metrics
- `cpu_percent`: Total CPU usage across all cores
- `ram_percent`: Memory utilization (0-100)
- `ram_available_mb`: Free RAM in megabytes
- `disk_percent`: Disk usage (0-100)
- `running_containers`: Number of healthy containers

### Container Metrics
- `memory_percent`: % of container's memory limit used
- `cpu_percent`: CPU % for this container
- `restart_count`: Total restarts (high = unstable)
- `uptime_seconds`: How long the container has been running

### Alerts
- **Level**: `crit` (critical), `warn` (warning), `info` (informational)
- **Category**: `cpu`, `memory`, `disk`, `container`
- **Cooldown**: Prevents alert spam (60s for CPU/RAM, 300s for disk)

---

## 🤖 How OOM Prediction Works

HyperVisor uses **linear regression on RAM trend** to forecast OOM:

1. Collects RAM usage every 5 seconds (300-point history)
2. Fits a linear trend: `predicted_ram = slope × time + intercept`
3. Predicts RAM % in 5 minutes
4. If prediction ≥ 95%, raises `crit` alert
5. Probability = `(predicted_ram - 90) × 2` (0-100%)

Example:
- Current: 75% RAM
- Trend: +0.2% per second
- Prediction: 75 + (0.2 × 300) = **135%** → **OOM in 5 minutes!**

---

## 🔧 Auto-Scaling Rules

### Rule 1: Kill Zombies
Removes containers that are stuck restarting:
```
if restart_count > 10 AND state != "running":
    kill(container)
```

**Why?** Prevents cascading failures from bad deployments.

### Rule 2: Stop Non-Critical on Memory Pressure
When `ram_percent ≥ 90`:
```
stop(grafana, prometheus, loki, promtail)
```

**Why?** Monitoring stack is non-critical; core services survive.

---

## 📡 Integration Points

### Crew Orchestrator
- HyperVisor registers on startup (non-blocking)
- Publishes metrics to Crew for cross-agent awareness

### Redis
- Caches alerts with 10s TTL
- Stores latest metrics for CLI/dashboard access

### Discord Bot (broski-bot)
- `DISCORD_WEBHOOK` sends `crit` alerts to ops channel
- Includes metrics snapshot in embed

### Observer Agent (hyper-observer)
- Can query HyperVisor metrics via REST
- Correlate system pressure with application behavior

---

## 🎯 Example Scenarios

### Scenario 1: Memory Leak
```
Time 0:00  RAM 40% → Alert: info
Time 0:05  RAM 50% → (info cooldown)
Time 0:10  RAM 60% → (info cooldown)
Time 0:15  RAM 75% → Alert: warn (RAM_THRESHOLD_WARN)
Time 0:20  RAM 85% → (warn cooldown)
Time 0:25  RAM 92% → Alert: crit + OOM prediction 95% in 5 min
Time 0:26  [AUTO-SCALE] Stop prometheus + loki
Time 0:27  RAM drops to 78% → Crisis averted ✅
```

### Scenario 2: Runaway Container
```
Container: hypercode-core
Restart count: 15 in 60 seconds
Status: exited

→ [AUTO-SCALE] Killed zombie container: hypercode-core
→ Alert: warn "hypercode-core restarting frequently"
→ Manual intervention needed (check logs, fix deployment)
```

---

## 🛠️ Troubleshooting

### HyperVisor won't start
```bash
# Check logs
docker logs hypervisor-agent

# Verify Docker socket access
docker exec hypervisor-agent ls -la /var/run/docker.sock

# Rebuild
docker compose up --build hypervisor-agent
```

### WebSocket connection fails
```bash
# Check port binding
netstat -tlnp | grep 8094

# Verify firewall
curl http://127.0.0.1:8094/health  # Should respond
```

### Alerts not reaching Discord
```bash
# Check webhook URL
echo $DISCORD_WEBHOOK

# Test manually
curl -X POST "$DISCORD_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{"content":"Test"}'
```

---

## 🧪 Testing Auto-Scale

Trigger memory pressure manually:
```bash
# Create a memory hog in background
python -c "import os; x = bytearray(3000 * 1024 * 1024)" &

# Watch HyperVisor respond
python agents/hypervisor-agent/cli.py watch

# Cleanup
pkill -f "bytearray"
```

---

## 🚀 Next Steps

1. **Add MCP bridge**: Query HyperVisor metrics from Claude/Cursor
2. **Extend auto-scaling**: Custom rules per container (e.g., scale Ollama replicas)
3. **Historical dashboards**: Grafana integration for long-term trends
4. **Predictive scaling**: Forecast load spikes and pre-scale before peak

---

## 📝 License

Part of the HyperFocus Z0ne ecosystem. Built by @welshDog.

**"Stop apologizing for your brain. Start building."** ⚡
