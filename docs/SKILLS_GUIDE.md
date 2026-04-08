# 🧠 HyperCode Claude Skills 2.0 Guide

> Skills are folders of Markdown + scripts that teach Claude HOW to work with HyperCode systems. They load on-demand — zero token cost until needed.

## 📁 Skills Directory

```
.claude/skills/
├── hypercode-agent-spawner/     # Spawn + register new agents
├── hypercode-self-improver/     # Skills 2.0 self-improvement loop
├── hypercode-docker-ops/        # Docker + compose management
├── hypercode-redis-pubsub/      # Inter-agent pub/sub comms
├── hypercode-code-review/       # Code quality + security review
├── hypercode-broski-economy/    # BROski$ coins + XP system
└── hypercode-mcp-gateway/       # MCP server config + tools
```

## ⚡ How Skills Work

1. Claude scans all `SKILL.md` frontmatter at session start (tiny token cost)
2. When your request matches a skill description, Claude loads that skill's full instructions
3. Claude uses scripts/sub-files inside the skill folder only when needed
4. **Result**: Claude gets specialist knowledge on-demand, not all at once

## 🔥 Skills 2.0 — Self-Improvement Loop

Run the improve loop on any skill:

```bash
python scripts/skill_eval.py --skill hypercode-agent-spawner --mode improve
```

This will:
- Run binary pass/fail evals
- Identify failure patterns  
- Rewrite the skill's description and instructions
- Re-run evals to confirm improvement
- Commit the improved skill automatically

## 🛠️ Create a New Skill

1. Create folder: `.claude/skills/your-skill-name/`
2. Create `SKILL.md` with frontmatter:

```markdown
---
name: your-skill-name
description: What it does. When to use it. Key trigger words.
---

# Your Skill Title
...
```

3. Rules:
   - `name`: lowercase, hyphens only, max 64 chars
   - `description`: max 1024 chars, third person, include trigger phrases
   - `SKILL.md` body: keep under 500 lines
   - Put reference docs in separate files, linked from SKILL.md

## 🧩 Skill vs MCP

| | Skills | MCP |
|--|--------|-----|
| **What it is** | Markdown instructions + scripts | Protocol for tool access |
| **Best for** | How-to knowledge, workflows, patterns | Live data, external APIs |
| **Token cost** | Near-zero until triggered | Can be high (GitHub MCP = 10k+ tokens) |
| **Complexity** | A folder of `.md` files | Full server implementation |

Use **both** together for max power: MCP for connectivity, Skills for knowledge.

## 🦅 Agent X + Skills

Agent X can:
- Read all skill metadata to understand system capabilities
- Trigger the self-improver skill to evolve other skills overnight
- Spawn new agents using the agent-spawner skill
- Wire new skills into the registry automatically

This is the **Evolutionary Pipeline** in action.
