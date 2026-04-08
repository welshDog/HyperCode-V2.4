# Grafana AI & Machine Learning — Master Guide for HyperCode

Right, let's go full deep-dive. Here's everything you need to become a master of the `grafana-ml-app` on your **hypercode** Grafana Cloud instance. [hypercode.grafana](https://hypercode.grafana.net/a/grafana-ml-app/home)

***

## The 3 Core ML Features

Your instance lives at `/a/grafana-ml-app/home` and has three main tools plus a suite of AI-powered extras: [hypercode.grafana](https://hypercode.grafana.net/a/grafana-ml-app/home)

| Feature | What it does | URL path |
|---|---|---|
| **Metric Forecasts** | Predict future metric values + anomaly detection | `/metric-forecast` |
| **Outlier Detection** | Find series behaving differently from their group | `/outlier-detector` |
| **Sift Investigations** | Automated diagnostic assistant for incidents | `/investigations` |

***

## 1. METRIC FORECASTS — The Prophet Engine

### How it works
Grafana ML uses **Meta's Prophet algorithm** — an additive/multiplicative time series model that fits non-linear trends with yearly, weekly, and daily seasonality, plus holiday effects. It's robust to missing data and trend shifts, and handles outliers well. Ideal for metrics with strong seasonal patterns (e.g. request rates, CPU usage over days/weeks). [hypercode.grafana](https://hypercode.grafana.net/a/grafana-ml-app/metric-forecast/create?ds=grafanacloud-prom)

### Two Tabs in the creation form:

**Query Builder tab**
- Select datasource (`grafanacloud-hypercode-prom` — your Prometheus) [hypercode.grafana](https://hypercode.grafana.net/a/grafana-ml-app/metric-forecast/create?ds=grafanacloud-prom)
- Pick a metric + label filters (Builder or raw PromQL Code mode)
- Add PromQL Operations (rate, sum, etc.)
- Toggle "Explain" to get AI-powered query explanations

**Training Model tab** — the power settings: [hypercode.grafana](https://hypercode.grafana.net/a/grafana-ml-app/metric-forecast/create?ds=grafanacloud-prom)

| Parameter | Default | What it controls |
|---|---|---|
| Training data range | 90 days | How far back Prophet learns from |
| Training data interval | 5 minutes | Granularity of training data |
| **Changepoint Prior Scale** | 0.05 | Trend flexibility — higher = more reactive to trend shifts. Range 0.01–0.5 [mbrenndoerfer](https://mbrenndoerfer.com/writing/prophet-time-series-forecasting-trend-seasonality-holiday-effects) |
| **Changepoint Range** | 0.8 | What proportion of historical data is considered for changepoints (0.8 = last 20% excluded) [mbrenndoerfer](https://mbrenndoerfer.com/writing/prophet-time-series-forecasting-trend-seasonality-holiday-effects) |
| **Seasonality Prior Scale** | 10 | Controls how strongly seasonal patterns are followed. Higher = bigger seasonal swings [grafana](https://grafana.com/docs/plugins/grafana-ml-app/latest/dynamic-alerting/forecasting/config/) |
| **Seasonality Mode** | Additive | Use **Multiplicative** if seasonal fluctuations grow proportionally with the trend magnitude [grafana](https://grafana.com/docs/plugins/grafana-ml-app/latest/dynamic-alerting/forecasting/config/) |
| **Uncertainty Interval Width** | 0.95 | Width of the confidence band (0.95 = 95% CI) |
| **Growth** | Linear | Can be set to Logistic for S-curve growth |
| Holidays Prior Scale | 10 | Strength of holiday effects |
| Weekly/Daily Fourier Order | — | Controls complexity of seasonal curves — higher = more flexible but can overfit |

**Holidays tab**
Create named holiday groups (via iCalendar) to exclude from forecast training — prevents spikes on Black Friday, bank holidays, etc. from poisoning your model. [grafana](https://grafana.com/blog/how-to-forecast-holiday-data-with-grafana-machine-learning-in-grafana-cloud/)

### The ML Prometheus Datasource (Master tip!)
Once you train a forecast, a special datasource called `grafanacloud-ml-metrics` appears. You can query it with PromQL: [grafana](https://grafana.com/docs/plugins/grafana-ml-app/latest/dynamic-alerting/querying/)

```promql
# Get the predicted value
request_rate:predicted{ml_forecast="yhat"}

# Get upper/lower confidence bounds
request_rate:predicted{ml_forecast="yhat_upper"}
request_rate:predicted{ml_forecast="yhat_lower"}

# Get actual values
request_rate:actual

# Calculate prediction error (residual)
abs(request_rate:predicted{ml_forecast="yhat"} - ignoring(ml_forecast) request_rate:actual)

# Only anomalous points
request_rate:actual and ignoring(ml_forecast) (request_rate:anomalous != 0)

# Anomalies below lower bound only
request_rate:actual and ignoring(ml_forecast) (request_rate:anomalous < 0)
```

This means you can **build Grafana alerts based on ML predictions** — the real power move.

***

## 2. OUTLIER DETECTION — DBSCAN vs MAD

Your instance's outlier detector defaults to `grafanacloud-hypercode-prom` and supports two algorithms: [grafana](https://grafana.com/blog/introducing-outlier-detection-in-grafana-machine-learning-for-grafana-cloud/)

### DBSCAN (Density-Based Spatial Clustering)
- **Best for**: Series that **move closely together** — e.g. multiple pods/replicas that normally track each other
- Compares data across all series at each timestamp, identifies the primary cluster, flags anything outside it
- DBSCAN = "if most pods are at ~50ms latency and one jumps to 500ms, flag it"

### MAD (Median Absolute Deviation)
- **Best for**: Series that stay in a **stable band** individually — e.g. a steady metric that occasionally spikes
- Compares a series' *current* behaviour to its *own historical* behaviour
- MAD = "if this metric is usually around X ± Y, flag deviations beyond that"

**Sensitivity slider**: Low / Medium / High — controls how aggressive the flagging is. [hypercode.grafana](https://hypercode.grafana.net/a/grafana-ml-app/outlier-detector/create?algorithm=dbscan&ds=grafanacloud-prom)

### When to use which:
| Scenario | Use |
|---|---|
| Monitoring N replicas that should behave identically | DBSCAN |
| Monitoring a stable metric for sudden spikes/drops | MAD |
| Mixed/trending data | DBSCAN |
| HTTP error rates per service (stable baseline) | MAD |

***

## 3. SIFT INVESTIGATIONS — Automated Incident Diagnosis

"Grafana Sift is a powerful diagnostic assistant designed to perform investigations on your data" — it's essentially an **automated incident commander**. [hypercode.grafana](https://hypercode.grafana.net/a/grafana-ml-app/investigations/configuration)

### How Sift works [grafana](https://grafana.com/docs/grafana-cloud/machine-learning/sift/)
When you trigger an investigation, Sift runs a battery of pre-configured checks across your datasources (Prometheus + Loki), groups the results into categories, and surfaces what's **interesting**:
- **Application** — logs + HTTP errors
- **Infrastructure** — resource contentions + container stability
- **Other** — status page outages, related alerts, correlated series

### Creating an Investigation [hypercode.grafana](https://hypercode.grafana.net/a/grafana-ml-app/investigations/create)
- **Investigation name**: label it by incident or symptom
- **Labels**: `cluster` and `namespace` — Sift uses these to scope all its queries
- **Services**: optional additional scoping
- **Time range**: -1h, -3h, -6h presets or custom (defaults to 30m window)
- **Time zone**: auto-detected (Europe/London for you)

### The 8 Pre-Configured Sift Checks (all enabled on your instance): [hypercode.grafana](https://hypercode.grafana.net/a/grafana-ml-app/investigations/configuration)

| Check | What it does |
|---|---|
| **Error Pattern Logs** | Groups error log lines by pattern, highlights ones with surging rates [grafana](https://grafana.com/docs/grafana-cloud/machine-learning/sift/analyses/error-pattern-logs/) |
| **HTTP Error Series** | Finds Prometheus series with elevated 4xx/5xx HTTP errors, identifies the worst 5-minute window [grafana](https://grafana.com/docs/grafana-cloud/machine-learning/sift/analyses/http-error-series/) |
| **Kube Crashes** | Finds pods that crashed (Error or OOMKill), uses kube-state-metrics + Loki logs for root cause [grafana](https://grafana.com/docs/grafana-cloud/machine-learning/sift/analyses/kube-crashes/) |
| **Log Query** | Custom Loki query check (you configure the LogQL) |
| **Metric Query** | Custom Prometheus query check |
| **Recent Deployments** | Correlates deployments with the investigation time window |
| **Resource Contention** | Finds pods with >25% CPU throttling or packet loss [grafana](https://grafana.com/docs/grafana-cloud/machine-learning/sift/analyses/resource-contentions/) |
| **Unhealthy Nodes** | Detects node-level issues in your cluster |

**The Kube Crashes check** uses this Loki pattern to find root causes:
```
%s |~`(?i)(panic:|traceback |error:|fatal)` !~`(?i)(info|debug)`
```


**The Resource Contention check** uses this Prometheus query under the hood:
```promql
sum by (cluster, namespace, pod, container) (
  rate(container_cpu_cfs_throttled_periods_total[5m])
) /
sum by (cluster, namespace, pod, container) (
  rate(container_cpu_cfs_periods_total[5m])
) > 0.25
```


***

## 4. The AI-Powered Extras (Beyond the ML App)

These are baked into Grafana Cloud itself: [hypercode.grafana](https://hypercode.grafana.net/a/grafana-ml-app/home)

### Adaptive Telemetry (New!)
- **Adaptive Metrics**: Identifies low-usage metrics and recommends dropping them to cut Prometheus costs
- **Adaptive Logs**: Analyses log patterns, checks which ones you actually query in the last 15 days, then recommends drop rates [grafana](https://grafana.com/docs/grafana-cloud/adaptive-telemetry/adaptive-logs/introduction/)
- Covers all 4 pillars: metrics, logs, traces, and profiles [apmdigest](https://www.apmdigest.com/grafana-labs-introduces-adaptive-telemetry-bring-your-own-cloud-and-fedramp-authorized-cloud)

### AI Observability
- Monitors your **LLMs** (token throughput, latency, error rates) via OpenLIT (OpenTelemetry SDK)
- Instruments **50+ gen AI tools** automatically — including LangChain and LlamaIndex (directly relevant to your BROski agents!) [grafana](https://grafana.com/whats-new/2025-02-06-generative-ai-observability--now-with-gpu-monitoring/)
- **GPU monitoring**: utilization %, temperature, power consumption, memory allocation [grafana](https://grafana.com/docs/grafana-cloud/monitor-applications/ai-observability/gpu-observability/setup/)

### Flamegraph AI
Analyses continuous profiling data and highlights performance bottlenecks and anomalies automatically.

### SLO Monitoring
Uses statistical techniques to predict the probability you'll breach an SLO threshold before it happens.

### Dashboard Assistant
Suggests panel titles and descriptions based on your query content — great for quick dashboard scaffolding.

### Incident Summaries
One-click AI-generated synopsis of incidents from your logs and timeline — surfaces the key details instantly.

### Grafana Assistant (the sparkle button ✨ in the top bar)
Can write, explain, and optimize PromQL/LogQL/TraceQL queries for you. Reference datasources with `@` syntax: [grafana](https://grafana.com/docs/grafana-cloud/machine-learning/assistant/guides/querying/)
```
Create a PromQL query in @grafanacloud-hypercode-prom 
that shows p95 latency for the HyperCode API over the last hour
```

***

## Master-Level Workflow for HyperCode

Here's how to put it all together for your stack:

1. **Create a forecast** for key metrics like `http_requests_total`, CPU usage, or memory usage on your HyperCode services. Set training range to 90 days, interval to 5 minutes.

2. **Build Grafana alerts** using the `grafanacloud-ml-metrics` datasource — alert when `actual` diverges from `yhat_upper` or `yhat_lower` — far smarter than static thresholds.

3. **Set up outlier detectors** with DBSCAN if running multiple replicas/pods of HyperCode components, MAD if monitoring stable baseline metrics.

4. **Pre-configure Sift** with your cluster + namespace labels so that during any incident you can fire a one-click investigation and get automated root-cause analysis across all 8 checks.

5. **Hook up AI Observability** via OpenLIT to monitor your BROski AI agent LLM calls — track token usage, latency, and errors per agent. [grafana](https://grafana.com/whats-new/2025-02-06-generative-ai-observability--now-with-gpu-monitoring/)

6. **Use Adaptive Logs** to cut log costs — since you're on Grafana Cloud free tier, this is critical to stay within limits. [grafana](https://grafana.com/docs/grafana-cloud/adaptive-telemetry/adaptive-logs/introduction/)
