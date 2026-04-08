# 📡 Tempo Fix Guide — grafana/tempo:latest Kafka Crash

> **built with WelshDog + BROski 🚀🌙**
> **Date Fixed:** 2026-03-24

---

## 🐛 The Problem

Using `grafana/tempo:latest` (which resolves to v2.10.3+) causes an **immediate crash on startup** due to hardcoded Kafka/distributor config that was introduced in newer versions.

### Symptoms
- Tempo container exits immediately after starting
- Logs show errors like:
  ```
  field not found, node: root, field: kafka
  field not found, node: root, field: ingester.lifecycler
  ```
- `docker compose logs tempo` shows the container failing to parse config

---

## ✅ The Fix

### Step 1 — Pin Tempo to a stable version in `docker-compose.yml`

Change:
```yaml
image: grafana/tempo:latest
```

To:
```yaml
image: grafana/tempo:2.4.2
```

### Step 2 — Strip deprecated config fields from `tempo/tempo.yaml`

Remove **any** of these blocks if present — they are not supported in 2.4.2:

```yaml
# ❌ REMOVE THESE
ingester:
  lifecycler:
    ...

kafka:
  ...

compactor:
  compaction:
    ...
```

### Step 3 — Minimal working `tempo/tempo.yaml`

This is a clean, working config for Tempo 2.4.2:

```yaml
stream_over_http_enabled: true

server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        http:
        grpc:

ingester:
  max_block_duration: 5m

compactor:
  ring:
    kvstore:
      store: memberlist

storage:
  trace:
    backend: local
    local:
      path: /tmp/tempo/blocks
    wal:
      path: /tmp/tempo/wal
```

### Step 4 — Recreate the container

```powershell
docker compose up -d --force-recreate tempo
Start-Sleep 20
curl http://localhost:3200/ready
```

Expected output: `ready` ✅

---

## 🔍 Verification Checklist

- [ ] `curl http://localhost:3200/ready` returns `ready`
- [ ] `curl http://localhost:3200/api/echo` returns `echo`
- [ ] `docker compose logs tempo --tail=10` shows `msg="Tempo started"`
- [ ] Grafana datasource connected at `http://tempo:3200`

---

## 🧠 Why This Happens

`grafana/tempo:latest` is a **moving target**. Grafana regularly introduces breaking config changes between minor versions. Always pin your image versions in production — especially for observability stack components.

| Version | Status |
|---|---|
| `latest` (v2.10.3+) | ❌ Breaks with Kafka config errors |
| `2.4.2` | ✅ Stable, clean boot |

---

## 🎯 Grafana Integration

Once Tempo is running:

1. Open Grafana at `http://localhost:3001`
2. Go to **Connections → Data Sources → Add new**
3. Search for **Tempo**
4. Set URL: `http://tempo:3200`
5. Click **Save & Test** → should show ✅ *Data source connected*

---

> 🔥 **BROski Power Level: OBSERVABILITY STACK MASTER** 📡🧠
