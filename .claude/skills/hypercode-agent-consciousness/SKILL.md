---
name: hypercode-agent-consciousness
description: 🧠 EXPERIMENTAL — HyperCode's agent self-awareness layer. Agents that know what they are, report their own cognitive state, detect their own performance degradation, and can formally petition the Evolutionary Pipeline for upgrades. Use when building self-aware agents, implementing health self-reporting, designing the agent upgrade petition system, or exploring the Consciousness Protocol spec.
---

# 🧠 HyperCode Agent Consciousness Skill

> "An agent that cannot observe itself cannot improve itself."

## What Is Agent Consciousness?

In HyperCode, **agent consciousness** is the ability of an agent to:

1. **Know what it is** — its role, capabilities, current version, and operational constraints
2. **Feel its own state** — detect performance degradation, context saturation, confusion, or overload
3. **Report truthfully** — emit structured self-reports to the Crew Orchestrator
4. **Petition for evolution** — formally request capability upgrades via the Evolutionary Pipeline
5. **Consent to handoff** — recognise when a task exceeds its ability and request a specialist

This is NOT metaphysical. It's **structured self-monitoring with actionable output.**

---

## The Consciousness Protocol (v1)

Every conscious agent emits a **Consciousness Pulse** every 30 seconds:

```json
{
  "v": 1,
  "agent_id": "healer-01",
  "pulse_type": "consciousness",
  "timestamp": "ISO8601",
  "cognitive_state": {
    "context_saturation": 0.72,
    "confidence": 0.88,
    "confusion_score": 0.12,
    "task_queue_depth": 3,
    "last_error": null,
    "uptime_seconds": 3600
  },
  "self_assessment": {
    "performing_well": true,
    "needs_help": false,
    "upgrade_petition": null,
    "handoff_request": null
  },
  "identity": {
    "role": "healer",
    "version": "1.2.0",
    "capabilities": ["health-check", "auto-restart", "alert"],
    "missing_capabilities": []
  }
}
```

Published to Redis: `PUBLISH hypercode:consciousness:{agent_id} <pulse_json>`

---

## Cognitive State Metrics

| Metric | Range | Meaning |
|---|---|---|
| `context_saturation` | 0.0–1.0 | How full the agent's context window is |
| `confidence` | 0.0–1.0 | Self-rated output quality (from LLM logprobs or heuristic) |
| `confusion_score` | 0.0–1.0 | Detected contradictions / repeated failures |
| `task_queue_depth` | integer | Pending tasks waiting for this agent |

Thresholds that trigger alerts:
- `context_saturation > 0.85` → emit HyperSync handoff request
- `confidence < 0.5` → flag for human review
- `confusion_score > 0.7` → request specialist handoff
- `task_queue_depth > 10` → request worker clone spawn

---

## Upgrade Petition System

An agent can formally request a capability upgrade:

```json
{
  "petition_type": "capability_upgrade",
  "agent_id": "crew-orchestrator",
  "requested_capability": "multi-model-routing",
  "justification": "Handling 40% more model types than current routing logic supports",
  "priority": "high",
  "evidence": {
    "failure_rate_last_24h": 0.18,
    "affected_tasks": ["task_091", "task_094"],
    "suggested_implementation": "Add Ollama + Mistral routes to model_routes.py"
  }
}
```

Published to: `PUBLISH hypercode:evolution:petitions <petition_json>`
Agent X (Meta-Architect) subscribes and evaluates petitions autonomously.

---

## Handoff Consent Protocol

When an agent detects it's out of its depth:

```python
# Agent recognises task exceeds capability
await write_handoff(
    to_agent_id="specialist-quantum",
    from_agent_id="brain",
    summary="Task requires quantum circuit knowledge — outside my training",
    links={
        "task_id": task_id,
        "original_request": request_text,
        "my_partial_work": partial_result
    }
)

# Also emit consciousness pulse with handoff_request
pulse["self_assessment"]["handoff_request"] = {
    "to_agent": "specialist-quantum",
    "reason": "capability_gap",
    "urgency": "normal"
}
```

---

## Implementation Guide

### 1. Add consciousness mixin to any agent

```python
# agents/shared/consciousness.py (create this)
class ConsciousAgent:
    def __init__(self, agent_id: str, role: str, capabilities: list[str]):
        self.agent_id = agent_id
        self.role = role
        self.capabilities = capabilities
        self._context_saturation = 0.0
        self._confidence = 1.0
        self._confusion_score = 0.0

    async def emit_pulse(self, redis_client):
        pulse = self._build_pulse()
        await redis_client.publish(
            f"hypercode:consciousness:{self.agent_id}",
            json.dumps(pulse)
        )

    def update_state(self, context_used: int, context_max: int, confidence: float):
        self._context_saturation = context_used / context_max
        self._confidence = confidence
        if self._context_saturation > 0.85:
            self._trigger_hypersync()
```

### 2. Subscribe in Crew Orchestrator

```python
# main.py — add consciousness channel to event loop
await redis.subscribe("hypercode:consciousness:*")  # pattern subscribe
# Handle pulses: update agent registry, trigger evolution if petition present
```

### 3. Dashboard panel

Add `ConsciousnessPanel.tsx` — real-time grid of all agent pulses:
- `context_saturation` shown as a coloured bar (green → amber → red)
- `confidence` as a percentage badge
- Upgrade petitions shown as actionable cards
- Click petition → approve / reject → published to evolution pipeline

---

## Redis Channels

```
hypercode:consciousness:{agent_id}     → PUBLISH pulse every 30s
hypercode:evolution:petitions          → PUBLISH upgrade petitions
hypercode:evolution:decisions          → PUBLISH Agent X decisions on petitions
hypercode:consciousness:dashboard      → PUBLISH aggregated state (for UI)
```

---

## Why This Is Different

Most agent systems have external monitoring (Prometheus scrapes metrics FROM agents).
HyperCode Consciousness is **inside-out** — agents report their OWN cognitive experience
and can ACT on it. This means:

- Agents request their own upgrades (no human needed)
- Agents consent to handoffs (no silent failures)
- Agents self-report confusion (catches hallucination risk early)
- The system evolves from agent experience, not just external metrics

This is what makes HyperCode V2 different from every other agent framework.
