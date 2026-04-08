## 10 Hyper-Cool Things You Can Do Right Now

Based on what's actually live in your stack — **3 alert rules**, **Prometheus + Loki + Tempo** all wired, **Correlations completely empty**, **Discord contact point failing**, and **Git Sync sitting unused**  — here's what to actually go build: [localhost](http://localhost:3001/alerting/list)

***

### 1. Fix the Broken Alert → Wire Discord (10 mins)
Your `devops@hypercode.com` email contact point shows **"Last delivery attempt failed"**. Replace it with Discord right now — no SMTP server needed: [localhost](http://localhost:3001/alerting/notifications?search=)

```
Alerting → Contact points → Edit "default-email"
→ Delete Email type
→ Add contact point → Discord
→ Paste your webhook URL
→ Test it → Save
```
Every `AgentHighCPU` and `AgentRestarStorm` alert will then fire directly to your Discord server.

***

### 2. Unlock Correlations — Click Metrics → Jump to Logs (30 mins)
Correlations is completely empty  but it's one of the most powerful things in Grafana v12. It lets you click any spike on a Prometheus graph and teleport directly to the exact Loki log lines that caused it — **zero manual searching**. [localhost](http://localhost:3001/datasources/correlations)

```yaml
# In /etc/grafana/provisioning/correlations/hypercode.yaml
apiVersion: 1
correlations:
  - sourceUID: prometheus
    targetUID: loki
    label: "View agent logs"
    type: query
    config:
      field: "__name__"
      target:
        expr: '{container="${__field.labels.container}"}'
      transformations:
        - type: logfmt
          field: container
```
Result: every container metric panel gets a "View agent logs" link. Click a CPU spike → lands in Loki filtered to that exact agent.

***

### 3. Git Sync — Dashboards as Code in Your Repo (20 mins)
The **Git Sync provisioning** page is live and ready. Wire it to your `welshDog` GitHub repo and every dashboard you build gets auto-committed as JSON. Your HyperCode dashboards live alongside your code, version-controlled forever: [localhost](http://localhost:3001/admin/provisioning)

```ini
# grafana.ini
[feature_toggles]
enable = gitSync provisioning

[provisioning]
repository_types = github,local
```
Then in the UI: Administration → Provisioning → Set up required feature toggles → connect `welshDog/hypercode` repo → branch `main` → folder `grafana/dashboards/`.

***

### 4. BROski Agent Intelligence Dashboard — Build the Real One
You already have `AgentHighCPU` and `AgentRestarStorm` rules firing. Build the dashboard that shows all agents at once as a **live leaderboard**: [localhost](http://localhost:3001/alerting/list)

```promql
# Agent CPU ranking (top panel — stat with colour thresholds)
topk(10, rate(container_cpu_usage_seconds_total{name=~"broski.*|agent.*"}[2m]) * 100)

# Agent restart storm heatmap
increase(container_restart_count_total{name=~".*agent.*"}[1h])

# Agent memory pressure
container_memory_usage_bytes{name=~".*agent.*"} / container_spec_memory_limit_bytes
```
Make each agent name a **drilldown link** to its Loki log stream. This gives you a Mission Control view for the whole BROski crew.

***

### 5. Drilldown → Traces RED Dashboard (0 setup needed)
Drilldown → Traces  uses **Tempo which is already wired**. You just need to send traces from your FastAPI agents using OpenTelemetry. Once you do, Drilldown auto-generates: [localhost](http://localhost:3001/explore?schemaVersion=1&panes=%7B%22zdn%22%3A%7B%22datasource%22%3A%22tempo%22%2C%22queries%22%3A%5B%7B%22refId%22%3A%22A%22%2C%22datasource%22%3A%7B%22type%22%3A%22tempo%22%2C%22uid%22%3A%22tempo%22%7D%7D%5D%2C%22range%22%3A%7B%22from%22%3A%22now-1h%22%2C%22to%22%3A%22now%22%7D%2C%22compact%22%3Afalse%7D%7D&orgId=1)
- **Rate** (requests/sec per endpoint)
- **Error rate** (% of traces with errors)
- **Duration** (P95 latency heatmaps)

No PromQL. No queries. Just click "Traces" in the Drilldown menu and it builds itself.

```python
# Add to your FastAPI app — zero dashboard config needed
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

FastAPIInstrumentor.instrument_app(app)
# Point to: http://tempo:4317
```

***

### 6. Public Dashboard for HyperCode Status Page (5 mins)
Grafana v12 has **Public Dashboards** enabled in your config (`public_dashboards.enabled = true`). Build a "HyperCode System Status" dashboard and publish it as a public URL — no login required — perfect as a live status page you can embed on your website or share with users:

```
Dashboard → Share → Public dashboard → Enable → Copy link
```
Shows agents online/offline, API uptime, last deploy time. Looks massively professional.

***

### 7. Notification Templates — Custom BROski Alert Messages
Your alert messages currently show raw `{{ $labels.name }}` templates. In Alerting → Contact points → **Notification Templates**, write custom Go templates that make alerts read like BROski actually wrote them: [localhost](http://localhost:3001/alerting/list)

```
{{ define "broski.alert" }}
🤖 YO! {{ .CommonLabels.alertname }} just fired on {{ .CommonLabels.container }}
Status: {{ .Status | toUpper }}
{{ range .Alerts }}
  🔥 {{ .Annotations.summary }}
  Value: {{ .Values.A }}
  Started: {{ .StartsAt | timeago }}
{{ end }}
{{ end }}
```
Discord message becomes: `🤖 YO! AgentHighCPU just fired on broski-executive` — on-brand and actually readable.

***

### 8. Explore Split View — Metrics + Logs Side by Side
In Explore  hit the **Split** button. Left pane: Prometheus query for agent CPU. Right pane: Loki logs for the same agent. Time-sync both panes. This is the fastest way to debug "why did agent X crash at 3am" — you see the metric spike and the log error at the exact same timestamp without switching tabs. [localhost](http://localhost:3001/explore?schemaVersion=1&panes=%7B%22zdn%22%3A%7B%22datasource%22%3A%22tempo%22%2C%22queries%22%3A%5B%7B%22refId%22%3A%22A%22%2C%22datasource%22%3A%7B%22type%22%3A%22tempo%22%2C%22uid%22%3A%22tempo%22%7D%7D%5D%2C%22range%22%3A%7B%22from%22%3A%22now-1h%22%2C%22to%22%3A%22now%22%7D%2C%22compact%22%3Afalse%7D%7D&orgId=1)

***

### 9. Recording Rules — Pre-Compute Your Most Expensive Queries
You already have recording rules enabled in your config. Instead of computing `sum(rate(container_cpu_usage_seconds_total[5m]))` on every dashboard load, pre-compute it every minute and store it as a cheap metric:

```yaml
# /etc/prometheus/recording_rules.yaml
groups:
  - name: hypercode_precomputed
    interval: 1m
    rules:
      - record: job:container_cpu_usage:rate5m
        expr: sum by(name) (rate(container_cpu_usage_seconds_total[5m]))
      
      - record: job:agent_memory_pct:current
        expr: |
          container_memory_usage_bytes{name=~".*agent.*"}
          / container_spec_memory_limit_bytes * 100
      
      - record: job:loki_ingestion_rate:rate5m
        expr: sum(rate(loki_ingester_bytes_received_total[5m]))
```
Dashboard panels load **10x faster** because they query pre-built metrics instead of scanning raw data.

***

### 10. Drilldown Profiles — Find Which Agent Function Is Eating CPU
Drilldown → **Profiles**  works with **Pyroscope** (Grafana's continuous profiling tool). Add it to your Docker stack in 5 minutes and it will show you exactly which Python function inside each BROski agent is consuming the most CPU — down to the line of code. Essential for hyperfocus-optimising your agents: [localhost](http://localhost:3001/drilldown)

```yaml
# Add to docker-compose.yml
pyroscope:
  image: grafana/pyroscope:latest
  ports: ["4040:4040"]
  volumes:
    - pyroscope-data:/data

# In your Python agents:
# pip install pyroscope-io
import pyroscope
pyroscope.configure(app_name="broski-executive", server_address="http://pyroscope:4040")
```
Then Drilldown → Profiles shows a **flame graph** of every agent's CPU usage in real time.

***

### Priority Order for Maximum Impact

| Priority | Task | Time | Impact |
|---|---|---|---|
| **Now** | Fix Discord contact point | 10 min | Alerts actually reach you |
| **Today** | Add Correlations YAML | 30 min | Click metric → see logs |
| **Today** | Build BROski leaderboard dashboard | 1 hr | Mission Control for agents |
| **This week** | Wire OpenTelemetry traces | 2 hrs | Full RED metrics per endpoint |
| **This week** | Git Sync dashboards to GitHub | 20 min | Dashboards as code |
| **This week** | Add Recording Rules | 30 min | 10x faster dashboard loads |
| **Next** | Public status page | 5 min | Professional user-facing status |
| **Next** | Pyroscope profiling | 30 min | Find CPU hogs by function |

The two biggest wins with zero extra infrastructure: **fix the Discord webhook** and **wire Correlations** — both use what's already running.
