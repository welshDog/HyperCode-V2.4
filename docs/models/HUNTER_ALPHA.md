# 🦅 Hunter Alpha

## Purpose

Hunter Alpha is HyperCode’s meta-architect model for repo-wide planning, evolution design, and long-horizon missions.

## Use It For

- Whole-system planning across multiple subsystems
- Multi-agent mission design
- Repo-wide reasoning across docs, logs, architecture, and reports
- Long-horizon “design the next version” tasks
- Evolutionary pipeline proposals

## Do Not Use It For

- Secrets or sensitive production data
- Small one-file edits
- High-volume background chatter
- Tasks that local Ollama can already handle

## Recommended Routing Triggers

Use Hunter Alpha when any of these are true:

- Task spans multiple subsystems
- Context estimate exceeds local model capacity (e.g. > 120k tokens)
- Task requires long-horizon planning
- Output is strategy, design, roadmap, architecture, or cross-doc synthesis

## Privacy Rules

- Do not send raw secrets, credentials, customer data, or private media.
- Redact tokens/passwords/API keys before routing.
- Prefer summarizing raw logs before routing when possible.

## Environment Variables

```env
HUNTER_ALPHA_ENABLED=true
HUNTER_ALPHA_MODEL=openrouter/openrouter/hunter-alpha
HUNTER_ALPHA_BASE_URL=https://openrouter.ai/api/v1
HUNTER_ALPHA_ROUTE_TAG=meta-architect
HUNTER_ALPHA_MAX_TOKENS=16000
HUNTER_ALPHA_PRIVACY_MODE=redact
OPENROUTER_API_KEY=changeme
```

## Example Use Cases

- “Read RUNBOOK.md + health reports and propose HyperCode V2.1.”
- “Design a Proposer–Solver–Judge evolution graph for Agent X.”
- “Map hyper-mission-system into HyperCode Core endpoints.”

