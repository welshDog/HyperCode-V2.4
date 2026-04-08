# 🤖 Claude AI Integration Guide — HyperCode V2.0

This directory documents how Claude AI integrates with HyperCode V2.0.

---

## Auto-Discovery Files

Claude automatically reads these files when analysing the repo:

| File | Purpose |
|---|---|
| `/CLAUDE.md` | Primary project intelligence file |
| `/.claude/settings.local.json` | Claude permissions & MCP server config |
| `/.claude/skills/` | Skill modules for domain-specific guidance |
| `/.claude/README.md` | Claude config & skills index |
| `/agents/README.md` | Agent crew overview & conventions |
| `/scripts/README.md` | Scripts index (boot, health, backups) |
| `/docs/index.md` | Documentation hub |

---

## MCP Server Integration

HyperCode exposes an MCP server that Claude can call directly:

```json
// .mcp.json
{
  "mcpServers": {
    "hypercode": { ... }
  }
}
```

This gives Claude live access to:
- System health status
- Agent registry
- Active task queue
- Agent-specific health metrics

---

## Claude Skill Modules

The `.claude/skills/` directory contains domain skill guides:

```
.claude/skills/
├── hypercode-new-agent-onboarding/   # Guide for adding new agents
└── technical-skills-audit/           # Full skills analysis & patterns
    ├── README.md
    ├── docker-mastery.md
    ├── fastapi-async-patterns.md
    ├── agent-orchestration.md
    ├── observability-guide.md
    ├── data-architecture.md
    └── security-guide.md
```

---

## How To Use Claude With This Repo

1. **Code generation** — Claude reads `CLAUDE.md` for project conventions before writing any code
2. **Debugging** — Claude can call MCP tools to check live service health
3. **Architecture decisions** — Reference skill modules for established patterns
4. **New agent creation** — Use the `hypercode-new-agent-onboarding` skill
5. **Security review** — Reference `security-guide.md` for secrets hygiene

---

## Contribution to Claude Context

When adding new major features:
1. Update `CLAUDE.md` with new service ports, directories, or conventions
2. Add a skill module under `.claude/skills/` if it's a new domain
3. Update this file if the integration pattern changes
