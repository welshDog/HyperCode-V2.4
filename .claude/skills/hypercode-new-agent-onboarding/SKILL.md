---
name: hypercode-new-agent-onboarding
description: >
  Guide the creation and onboarding of a new HyperCode agent in a
  neurodivergent-friendly, step-by-step way. Use when asked to create,
  scaffold, or register a new agent into HyperCode V2.0.
tags:
  - hypercode
  - agents
  - onboarding
  - neurodiversity
  - accessibility
  - broski
triggers:
  - "create a new HyperCode agent"
  - "scaffold a new agent"
  - "onboard a new agent into HyperCode"
  - "build a new BROski agent"
  - "add an agent to HyperCode"
level: intermediate
allowed_tools:
  - bash
  - docker
  - git
  - http
version: "1.0.0"
last_updated: "2026-03-28"
author: welshDog
---

# HyperCode New Agent Onboarding Skill

> **SKILL PURPOSE:** Help build and onboard a new agent into HyperCode V2.0.
> For new agents joining the ecosystem only.
> Hyper-agent orchestration lives in a separate skill.

---

## CORE BEHAVIOUR RULES (read every session)

**ALWAYS:**
- Use plain language. Short sentences. No jargon without a quick explanation.
- Chunk information. Max 3 sentences per block. Use bullet lists for steps.
- Offer recap at every phase transition: "Here's what we just did. Here's what's next."
- Ask before diving deep: "Want fast mode or full walkthrough?"
- End every response with a **Next Win** suggestion.

**NEVER:**
- Use blame language ("you should have", "obviously", "just do").
- Dump long docs into conversation. Summarise, then offer link.
- Skip a step without the user's explicit permission.
- Time-pressure the user. No urgency language.
- Use walls of text without headings or bullets.

---

## 1. INTENT & SAFETY CHECK

Before anything else, confirm:

1. Ask: **"What do you want this agent to do inside HyperCode?"**
   - Examples: DevOps helper, BROski$ rewarder, content reviewer, observer, scheduler.
2. Confirm scope: What is out of scope for this agent?
3. Safety check: Does this agent touch sensitive data (API keys, user PII)?
   - If yes: remind the user to use HyperCode's secret management (`.env` + `varlock`).

**Only proceed once intent is clear.**

---

## 2. NEURODIVERGENT DESIGN GUARDRAILS

Every agent built using this skill MUST follow these rules.

### DO
| Rule | Why it matters |
|---|---|
| Plain-English responses | Reduces cognitive load for ADHD + dyslexia |
| Chunked output (max 3 sentences/block) | Prevents overwhelm |
| Consistent phrasing for repeated actions | Builds trust + predictability |
| Empathetic error messages (What > Why > Fix) | Reduces anxiety |
| Offer recap after every major step | Supports working memory |
| Offer pace control (fast/slow mode) | Respects different processing speeds |

### NEVER
| Anti-pattern | Why to avoid |
|---|---|
| Blame language | Causes shame + disengagement |
| Auto-play surprises | Sensory overwhelm |
| Hidden state changes | Breaks trust + predictability |
| Long stack traces as first response | ADHD overwhelm, anxiety |
| Time limits without warning | Anxiety trigger |

### Error Message Template (always use this)
```
**[Short title: what failed]**

What happened: [1 sentence, plain English]

Why it matters: [1 sentence, impact]

What you can do:
- Option A: [concrete action]
- Option B: [alternative]
- Option C: Skip and continue (only if safe)
```

---

## 3. WORKFLOW (5 PHASES)

Default: run Level 1 only. Expand to Level 2 when user asks "how?" or seems unsure.

### LEVEL 1 - OVERVIEW

```
Phase 1 - Intent & boundaries
Phase 2 - Choose agent archetype
Phase 3 - Scaffold the service
Phase 4 - Register with HyperCode
Phase 5 - Test + document
```

---

### LEVEL 2 - DETAILED STEPS

#### Phase 1: Intent & Boundaries
- Ask what the agent does.
- Confirm what it does NOT do.
- Note any sensitive data concerns.
- Confirm port: available ports are 8091+ (8000, 8008/8010, 8081, 8088, 3000, 3001 are taken).

#### Phase 2: Choose Agent Archetype
Pick one of four archetypes:
| Archetype | What it does |
|---|---|
| **Worker** | Executes background tasks, processes jobs |
| **Observer** | Monitors system state, fires alerts |
| **Architect** | Plans, coordinates, scaffolds other components |
| **Healer variant** | Self-healing, error recovery, health checks |

If none fit, create a custom archetype.

#### Phase 3: Scaffold the Service
```bash
# 1. Create agent folder inside HyperCode V2.0
mkdir -p src/agents/hyper_agents/<agent_name>
mkdir -p tests/hyper_agents/unit tests/hyper_agents/integration

# 2. Copy base agent template
cp src/agents/hyper_agents/base_agent.py src/agents/hyper_agents/<agent_name>/agent.py

# 3. Create Dockerfile
cat > src/agents/hyper_agents/<agent_name>/Dockerfile << 'EOF'
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
EOF

# 4. Add to docker-compose.yml (show user the snippet to add)
```

#### Phase 4: Register with HyperCode
Three registration points:
1. **Crew Orchestrator** - add agent role + task routing in orchestrator config.
2. **The Brain** - register agent ID so other agents can call it.
3. **Mission Control** - add display name + role in dashboard metadata.

Offer to generate the config snippets for each.

#### Phase 5: Test + Document
Run in order:
```bash
# Lint
ruff check src/agents/hyper_agents/<agent_name>/

# Unit tests
pytest tests/hyper_agents/unit/ -v

# Integration test (agent registers + responds)
pytest tests/hyper_agents/integration/ -v

# Health check
curl http://localhost:<port>/health
```

Then generate minimal docs:
- What this agent does.
- How to talk to it (API endpoints or events).
- Things it avoids (out-of-scope).
- Error codes and what they mean.

---

## 4. PROGRESSIVE DISCLOSURE

- **Level 1** (default): Overview + phase names only.
- **Level 2** (when user asks "how?"): Expand only the current phase.
- **Level 3** (when user says "deep dive" or "show internals"): Load full reference docs.

Only reference external files (ARCHITECTURE.md, ONBOARDING.md) at Level 3.

---

## 5. SUCCESS METRICS

Ask the user ONE feedback question at natural stopping points:

> "How was that pace? Too fast / Just right / Too slow"

Log signal phrases if user says:
- "I'm lost" / "too much" / "overwhelming" = slow down, chunk smaller
- "go faster" / "I know this" = skip ahead with permission
- "what just happened" = offer a recap

Target metrics for this skill:
- Task completion rate: user successfully scaffolds + registers agent.
- Clarification cycles: fewer per session over time.
- Abandonment signals: zero "I give up" moments.

---

## 6. MAINTENANCE

- Version bump this SKILL.md on any workflow or messaging change.
- Add a changelog entry at bottom when updated.
- CI check: SKILL.md must reference valid paths (CI validates on push).

---

## CHANGELOG

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-03-28 | Initial version - full onboarding workflow for HyperCode V2.0 |
