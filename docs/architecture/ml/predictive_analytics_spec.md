# HyperCode Machine Learning & Predictive Analytics Strategy

## Overview
This document outlines the configuration and strategy for enabling predictive analytics within the HyperCode Grafana instance, leveraging the Prophet algorithm for metric forecasting and outlier detection.

## 1. Metric Forecast Configuration (Prophet Engine)

### Objective
Predict agent resource consumption (CPU/Memory) to proactively scale or alert before limits are hit.

### Configuration Specification
Navigate to `/metric-forecast` in Grafana and create the following models:

#### Model A: Agent CPU Forecast
- **Datasource**: `prometheus`
- **Query**: `rate(container_cpu_usage_seconds_total{image=~"hypercode-agent.*"}[5m])`
- **Training Window**: 14 days (minimum for weekly seasonality detection)
- **Changepoint Prior Scale**: `0.05` (Standard sensitivity to trend changes)
- **Seasonality**:
  - **Daily**: Enabled (Fourier Order 10)
  - **Weekly**: Enabled (Fourier Order 3)
- **Holidays**: Import standard region-specific holidays to avoid false anomalies.

#### Model B: Task Latency Forecast
- **Datasource**: `prometheus`
- **Query**: `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))`
- **Training Window**: 7 days
- **Growth**: Linear

## 2. Outlier Detection Strategy

### Objective
Identify "rogue" agents that deviate significantly from the swarm's baseline behavior.

### Configuration Specification
Navigate to `/outlier-detector` and configure:

#### Detector A: CPU Deviation (DBSCAN)
- **Algorithm**: DBSCAN (Density-Based Spatial Clustering)
- **Rationale**: Agents performing similar tasks should cluster together. Outliers indicate stuck processes or infinite loops.
- **Metric**: `container_cpu_usage_seconds_total`
- **Epsilon**: Auto-tuned
- **Min Samples**: 3 (Cluster size)

#### Detector B: Error Rate Spikes (MAD)
- **Algorithm**: MAD (Median Absolute Deviation)
- **Rationale**: Error rates should be stable (near zero). Sudden deviation from an agent's own history indicates failure.
- **Metric**: `rate(http_requests_total{status=~"5.."}[5m])`
- **Sensitivity**: High

## 3. Alerting on Predictions

Once models are trained, use the generated `grafanacloud-ml-metrics` datasource to create alerts:

```promql
# Alert if actual CPU > predicted upper bound for 15 minutes
condition:
  container_cpu_usage:actual > container_cpu_usage:predicted{ml_forecast="yhat_upper"}
for: 15m
labels:
  severity: warning
annotations:
  summary: "Agent CPU exceeding predicted usage"
  description: "Agent {{ $labels.container }} is using more CPU than the ML model predicted."
```

## 4. Implementation Checklist
- [ ] Verify 14+ days of historical data in Prometheus.
- [ ] Create "Agent CPU" forecast model.
- [ ] Create "Agent Cluster" outlier detector.
- [ ] Create alert rule based on `yhat_upper` breach.
- [ ] Add ML forecast panels to the main HyperStation dashboard.
