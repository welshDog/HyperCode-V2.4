# Roundtrip Worker Monitoring

## Components
- Prometheus rule at `monitoring/rules/roundtrip.yml` monitors p99 latency > 5s.
- Grafana dashboard `Roundtrip Worker Latency` displays p95 and p99 with a 5s threshold.

## Prometheus
- Target: `roundtrip-worker:9100` must be UP.
- Expression: `histogram_quantile(0.99, sum by (le) (rate(roundtrip_latency_seconds_bucket{job="roundtrip-worker"}[5m])))`.
- Alerts fire immediately when above 5s; evaluated every 5m.

### Troubleshooting
- Check Prometheus `Status → Rules` to see alert state.
- Inspect `Status → Targets` for roundtrip-worker.
- Validate metrics: query `roundtrip_latency_seconds_bucket` and rates.

## Grafana
- Dashboard path: `monitoring/grafana/dashboards/roundtrip.json`.
- Provisioning: `monitoring/grafana/provisioning/dashboards/roundtrip.yml`.
- Time options: 1h, 6h, 12h, 24h, 7d.

### Troubleshooting
- Ensure Prometheus datasource points to `http://prometheus:9090`.
- Verify dashboard provisioning loaded the JSON file.
- Use Explore to run the p95/p99 queries directly.

## Runbook
- If alert fires:
  1. Confirm Ollama service health and logs.
  2. Inspect Jaeger traces for `generate` span from roundtrip-worker.
  3. Check Docker network connectivity on `hypernet`.
  4. Review roundtrip-worker container CPU/memory and restart if necessary.
