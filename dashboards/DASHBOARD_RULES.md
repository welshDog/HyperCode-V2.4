# 📊 HyperCode Dashboard Rules

> Git is the ONLY edit surface. Never edit dashboards directly in Grafana Cloud UI.

## 🔴 Three Hard Rules

| Rule | How |
|------|-----|
| **One UID per dashboard** | Keep `"uid"` identical across local + cloud — Cloud import with same UID overwrites, not duplicates |
| **Git is the only edit surface** | Edit in local Grafana → Export → Save JSON here → Commit → Push |
| **Folders mirror the repo** | `dashboards/hypercode/` → Grafana folder `hypercode`, etc. |

## 📁 Folder Structure

```
dashboards/
  hypercode/     ← HyperCode ops dashboards (agents, health, mission control)
  platform/      ← Infrastructure (cloud health, billing, logs, cardinality)
  incident/      ← BROski command centre, alert groups, incident insights
```

## 🔧 Fixing Dashboards Before Promotion

### 1. Add datasource input (REQUIRED)

If your dashboard has `"__inputs": []`, add this:

```json
"__inputs": [
  {
    "name": "DS_PROMETHEUS",
    "label": "Prometheus",
    "description": "",
    "type": "datasource",
    "pluginId": "prometheus",
    "pluginName": "Prometheus"
  }
],
```

Then reference it in every target:
```json
"datasource": { "type": "prometheus", "uid": "${DS_PROMETHEUS}" }
```

### 2. Fix hardcoded rate intervals

```json
// ❌ breaks for time ranges < 5m
"expr": "rate(metric[5m])"

// ✅ always correct
"expr": "rate(metric[$__rate_interval])"
```

## 🚀 Day-to-Day Workflow

1. Edit dashboard in local Grafana (`localhost:3001`)
2. **Share → Export → Export for sharing externally** (preserves `__inputs`)
3. Save to `dashboards/<folder>/<uid>.json` — overwrite in place
4. Commit + open PR
5. CI validates → merge → auto-promoted to Cloud

## ⚠️ Never Do This

- **Never** use "Save to library" or Grafana snapshot URLs — creates orphan copies with new UIDs = sprawl
- **Never** edit dashboards directly in Cloud UI
- **Never** duplicate a dashboard JSON with the same UID into two different folders

## 🔑 Required GitHub Secrets

Add these in repo Settings → Secrets → Actions:

| Secret | Value |
|--------|-------|
| `GRAFANA_CLOUD_URL` | `https://hypercode.grafana.net` |
| `GRAFANA_CLOUD_TOKEN` | Your service account token (`glsa_...`) |
| `GRAFANA_CLOUD_PROM_UID` | Your Cloud Prometheus datasource UID (find in Grafana Cloud → Connections → Data sources) |
