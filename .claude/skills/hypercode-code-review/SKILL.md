---
name: hypercode-code-review
description: Reviews code changes in the HyperCode codebase for quality, security, agent safety, and architectural consistency. Use when asked to review a PR, check new agent code, audit a module, or validate changes before merging. Applies HyperCode-specific patterns and checks MCP/Skills compliance.
---

# HyperCode Code Review

## Review checklist

- [ ] FastAPI endpoints have proper error handling and status codes
- [ ] New agents register with Crew Orchestrator on startup
- [ ] Redis channels follow naming convention (`hypercode:<category>:<name>`)
- [ ] Docker healthcheck added for new services
- [ ] No hardcoded secrets or API keys (use `.env`)
- [ ] Safety level set on all new agents
- [ ] Guardian enforcement wired for agents with `open` or `moderate` safety
- [ ] Tests added in `/tests` for new modules
- [ ] CLAUDE.md updated if new patterns introduced

## Security scan

```bash
python scripts/security_scan.py --path <file_or_dir>
```

## Architecture check

New services MUST:
1. Expose `/health` endpoint returning `{"status": "healthy"}`
2. Publish startup event to `hypercode:system`
3. Accept config from environment variables only
4. Use structured logging (JSON format)

## Pattern validation

See [PATTERNS.md](PATTERNS.md) for approved HyperCode code patterns.
