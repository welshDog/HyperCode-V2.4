# 💊 Healer Alpha

## Purpose

Healer Alpha is HyperCode’s incident and recovery model, designed for multimodal debugging and cross-signal correlation.

## Use It For

- Incident diagnosis and recovery planning
- Multimodal debugging (screenshots, dashboards, audio-assisted diagnosis)
- Log + metric + alert correlation
- Safe recovery playbook generation across multiple services

## Do Not Use It For

- Routine code autocomplete
- Simple CRUD backend edits
- High-frequency cheap automation
- Sensitive production secrets

## Recommended Routing Triggers

Use Healer Alpha when any of these are true:

- Inputs include images/screenshots/audio or mixed media
- Task is incident response or self-healing
- Multiple signals must be correlated (logs + metrics + traces + screenshots)
- A recovery plan is needed (not just a diagnosis)

## Privacy Rules

- Never send raw secrets, credentials, or private customer media.
- Redact screenshots containing tokens or internal URLs.
- Require human approval before destructive actions.

## Environment Variables

```env
HEALER_ALPHA_ENABLED=true
HEALER_ALPHA_MODEL=openrouter/openrouter/healer-alpha
HEALER_ALPHA_BASE_URL=https://openrouter.ai/api/v1
HEALER_ALPHA_ROUTE_TAG=incident-healing
HEALER_ALPHA_MAX_TOKENS=12000
HEALER_ALPHA_PRIVACY_MODE=redact
OPENROUTER_API_KEY=changeme
```

## Example Use Cases

- “Analyze this Grafana screenshot and tell me what’s failing.”
- “Correlate celery logs, Prometheus alerts, and service health.”
- “Generate a safe recovery playbook for Docker flapping + DB drift.”

