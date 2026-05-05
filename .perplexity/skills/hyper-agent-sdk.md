---
name: hyper-agent-sdk
description: Use for HyperAgent-SDK tasks — CLI commands, agent spec validation, npm publishing, studio, templates, or SDK Phase 2 work. Triggers on: "SDK", "hyper-agent", "CLI", "validate", "npm publish", "studio", "agent spec", "graduate".
---

# 🤖 HyperAgent SDK Skill

## Repo
- [HyperAgent-SDK](https://github.com/welshDog/HyperAgent-SDK)
- Published: `npm install @w3lshdog/hyper-agent` (current: 0.1.7)

## CLI Commands
```bash
hyper validate    # validate agent against hyper-agent-spec.json
hyper registry    # list registered agents
hyper studio      # open studio at http://localhost:4040
hyper status      # check agent health
hyper agents      # list all agents
hyper tokens      # check BROski$ balance
hyper graduate    # graduate an agent to production
```

## Key Files
- hyper-agent-spec.json — JSON Schema contract (shared across all 3 repos)
- cli/ — CLI source
- studio/ — Studio UI (port 4040)
- templates/ — Python + TypeScript starter templates
- types/ — TypeScript type definitions
- tests/ — test suite

## CI
- GitHub Actions: npm test on every push + PR ✅ (April 16)
- NOTE: GitHub Actions billing lock = CI blocked — fix at github.com/settings/billing

## Phase 2 Roadmap (NEXT UP)
- [ ] Validator UX improvements
- [ ] Python starter template
- [ ] TypeScript starter template
- [ ] npm publish 0.2.0
- [ ] Spec versioning

## Agent Spec Contract
- All agents must pass hyper-agent-spec.json validation
- Spec is the single source of truth across HyperCode-V2.4, SDK, and Course repos
- Use `hyper validate` before deploying any new agent
