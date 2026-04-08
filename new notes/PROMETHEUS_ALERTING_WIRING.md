# Wiring Prometheus Alert Rules (HyperCode)

This pack provides: `healthfix/monitoring/prometheus/alert_rules_hypercode.yml`

## 1) Put the file where Prometheus can read it

Recommended in-repo path after copying this pack into your repo:

```
HyperCode-V2.0/healthfix/monitoring/prometheus/alert_rules_hypercode.yml
```

## 2) Add it to Prometheus configuration

In your Prometheus config (often `monitoring/prometheus/prometheus.yml`), add or extend:

```yaml
rule_files:
  - /etc/prometheus/alert_rules.yml
  - /etc/prometheus/alert_rules_hypercode.yml
```

## 3) Mount the rules file into the Prometheus container (Docker Compose)

In your `prometheus:` service volumes, add something like:

```yaml
volumes:
  - ./healthfix/monitoring/prometheus/alert_rules_hypercode.yml:/etc/prometheus/alert_rules_hypercode.yml:ro
```

## 4) Reload Prometheus

If you have web reload enabled:
```bash
curl -X POST http://localhost:9090/-/reload
```

Otherwise restart Prometheus:
```bash
docker compose restart prometheus
```

## 5) Validate rules loaded

- Prometheus UI → **Status → Rules**
- Alertmanager UI → verify receivers/routes are configured

## Notes / troubleshooting

- These rules assume cAdvisor-style metrics with the label:
  `container_label_com_docker_compose_service`
- If your metrics use a different label (e.g., `name`), adapt the selectors accordingly.

