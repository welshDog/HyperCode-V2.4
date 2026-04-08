# 🎓 Prometheus Mastery Plan: From "Getting Started" to Production Pro

This comprehensive learning path is designed to take you from the basic concepts of the [Prometheus Getting Started Guide](https://prometheus.io/docs/prometheus/latest/getting_started/) to mastering the production-grade observability stack currently deployed in HyperCode V2.0.

---

## 🗺️ Learning Roadmap Overview

| Module | Focus Area | Key Concepts | Success Criteria |
|:---:|:---|:---|:---|
| **1** | **Architecture & Config** | Server, Scrapers, Exporters, YAML | Understand `prometheus.yml` & Architecture |
| **2** | **The Data Model** | Metrics, Labels, Time Series | Read raw metrics from `/metrics` endpoints |
| **3** | **PromQL Basic** | Selectors, Instant Vectors, Ranges | Query `up` status & basic counters |
| **4** | **PromQL Advanced** | `rate()`, Aggregation, Histograms | Calculate Request Rates & Latency |
| **5** | **Instrumentation** | Client Libraries, Custom Metrics | Add a custom metric to HyperCode Core |
| **6** | **Alerting** | AlertManager, Rule Files | Fix Config Mismatch & Create Alert Rules |
| **7** | **Visualization** | Grafana Data Sources & Panels | Build a "Mission Control" Dashboard |

---

## 🚀 Module 1: Architecture & Configuration
**Goal:** Understand how Prometheus collects data (Pull Model).

### 📖 Concepts
- **Scraping:** Prometheus *pulls* data from targets (unlike pushing).
- **Targets:** Endpoints exposing metrics (e.g., `localhost:9090/metrics`).
- **Job:** A collection of similar targets.

### 🛠️ Practical Exercise: Dissect the Config
1. Open `prometheus.yml` in the project root.
2. Identify the `scrape_interval` (How often we pull data).
3. Identify the `scrape_configs` section.
4. **Task:** Find the `job_name` for the HyperCode Core API.

### 🎯 Milestone
- [ ] I can explain why `prometheus.yml` is the "brain" of the operation.

---

## 🔬 Module 2: The Data Model
**Goal:** Read and understand raw metric formats.

### 📖 Concepts
- **Metric Name:** e.g., `http_requests_total`.
- **Labels:** Key-value pairs, e.g., `{method="POST", handler="/api"}`.
- **Metric Types:** Counter (goes up), Gauge (goes up/down), Histogram (buckets).

### 🛠️ Practical Exercise: Raw Data Inspection
1. Open your browser to `http://localhost:9090/metrics`.
2. Search for `prometheus_http_requests_total`.
3. **Task:** Run the following command to see HyperCode Core's raw metrics:
   ```bash
   curl -s https://localhost/api/metrics | head -n 20
   ```
   *(Note: You might need to use the internal port if Nginx blocks it, or check the container logs)*

### 🎯 Milestone
- [ ] I can distinguish between a Metric Name and its Labels.

---

## 🧠 Module 3: PromQL Basics (Querying)
**Goal:** Ask questions to your data.

### 📖 Concepts
- **Expression Browser:** The UI at `http://localhost:9090/graph`.
- **Instant Vector:** Values at a single point in time.

### 🛠️ Practical Exercise: First Queries
1. Go to `http://localhost:9090/graph`.
2. **Check Health:** Execute `up`.
   - Result: `1` means healthy, `0` means down.
3. **Check Traffic:** Execute `http_requests_total`.
4. **Filter:** Execute `http_requests_total{status="200"}`.

### 🎯 Milestone
- [ ] I can verify which services are online using PromQL.

---

## 📈 Module 4: PromQL Advanced (Rates & Latency)
**Goal:** Calculate actionable insights.

### 📖 Concepts
- **Range Vector:** `[5m]` (Data over the last 5 minutes).
- **Rate:** `rate()` calculates per-second speed.
- **Histogram:** `histogram_quantile()` for latency (e.g., P95).

### 🛠️ Practical Exercise: Real-world Analysis
1. **Traffic Rate:** How many requests per second?
   ```promql
   rate(http_requests_total[1m])
   ```
2. **Error Rate:** How many 500 errors?
   ```promql
   rate(http_requests_total{status=~"5.."}[5m])
   ```
3. **Latency (P99):**
   ```promql
   histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
   ```

### 🎯 Milestone
- [ ] I can write a query to show the "Requests Per Second" (RPS) of the API.

---

## 🔌 Module 5: Instrumentation (Code Level)
**Goal:** Create custom metrics in Python.

### 📖 Concepts
- **Client Library:** `prometheus_client` (Python).
- **Registry:** Where metrics are stored in memory.

### 🛠️ Practical Exercise: Add a Metric
1. Open `THE HYPERCODE/hypercode-core/app/main.py` (or equivalent).
2. **Task:** Define a new counter:
   ```python
   from prometheus_client import Counter
   FEATURE_USAGE = Counter('feature_usage_total', 'Usage of specific features', ['feature_name'])
   ```
3. Increment it in an endpoint: `FEATURE_USAGE.labels(feature_name='magic').inc()`.
4. Rebuild and verify in Prometheus.

### 🎯 Milestone
- [ ] I have successfully added and scraped a custom metric.

---

## 🚨 Module 6: Alerting (Real-World Project)
**Goal:** Get notified when things break.

### 📖 Concepts
- **Alerting Rules:** PromQL expressions that trigger alerts.
- **AlertManager:** Routes alerts to Email/Slack.

### 🛠️ Practical Exercise: Fix & Deploy
1. **Discovery:** We noticed a mismatch. `prometheus.yml` looks for rules in `/etc/prometheus/monitoring/rules/*.yml`, but `docker-compose` mounts `./alert.rules.yml` to `/etc/prometheus/alert.rules.yml`.
2. **Task:** Fix the path in `prometheus.yml`.
3. **Task:** Create a rule in `alert.rules.yml`:
   ```yaml
   groups:
   - name: operations
     rules:
     - alert: InstanceDown
       expr: up == 0
       for: 1m
   ```
4. Restart Prometheus and verify in the "Alerts" tab.

### 🎯 Milestone
- [ ] I have an active alert firing when I stop a container.

---

## 📊 Module 7: Visualization (Grafana Integration)
**Goal:** Build a dashboard.

### 📖 Concepts
- **Data Source:** Prometheus.
- **Panels:** Graphs, Gauges, Stat blocks.

### 🛠️ Practical Exercise: The Mission Control
1. Log in to Grafana (`admin`/`admin`).
2. Add Prometheus as a Data Source (`http://prometheus:9090`).
3. Create a Dashboard.
4. **Task:** Add 3 Panels:
   - **RPS:** `sum(rate(http_requests_total[1m]))`
   - **Errors:** `sum(rate(http_requests_total{status=~"5.."}[1m]))`
   - **Active Agents:** `count(up{job="agents"})`

### 🎯 Milestone
- [ ] I have a saved Dashboard showing the health of HyperCode.

---

## 🏁 Final Project: The "Chaos Test"
1. Start the full stack.
2. Run `verify_launch.ps1` to generate traffic.
3. Watch your Grafana Dashboard light up.
4. Stop the `hypercode-core` container.
5. Verify your Alert fires.

**Ready to begin? Start with Module 1 by opening `prometheus.yml`!**
