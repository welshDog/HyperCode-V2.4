# HyperCode V3 Roadmap — AI-Native Evolution

> **Status:** Strategic roadmap
> **Updated:** 2026-08-26
> **Project:** HyperCode-V2.4
> **Mission:** Build a neurodivergent-first autonomous AI infrastructure platform that is useful, inspectable, safe, and able to evolve without losing human control.

## North Star

HyperCode V3 evolves the current Docker-based agent swarm into a **protocol-native, stateful, observable, and governed agent platform**. The system should make complex work feel like a visible mission: clear roles, small steps, recoverable progress, useful feedback, and explicit human approval for consequential actions.

The roadmap extends the existing HyperCode foundations rather than replacing them:

- FastAPI core and existing service boundaries.
- Docker Compose profiles and hardened agent containers.
- Crew Orchestrator, Agent X, Healer Agent, CognitiveUplink, and Mission Control.
- MCP gateway and GitHub tool integration.
- Prometheus, Grafana, Loki, Tempo, Redis, PostgreSQL, Celery, and Trivy.
- Agent identity, life plans, guardrails, contract tests, governance ledger, and evolutionary pipeline.
- BROski$ XP, rewards, missions, and neurodivergent-first interaction design.

## Guiding Principles

1. **Human agency first.** Agents may recommend, prepare, test, and request approval. High-impact actions must not silently execute.
2. **Protocol before vendor.** Use open interfaces so models, runtimes, and tools can be replaced without rewriting HyperCode.
3. **State over chat history.** Long missions need durable state, checkpoints, resumability, and a clear event trail.
4. **Small agents, explicit contracts.** Every agent has a role, inputs, outputs, permissions, budgets, and failure behaviour.
5. **Evidence over confidence.** A completed mission needs tests, traces, artefacts, and verification—not just a successful model response.
6. **Neurodivergent-first by design.** Reduce cognitive load with chunking, visible progress, context retention, plain language, and celebratory feedback.
7. **Secure defaults.** Least privilege, secret isolation, network boundaries, tool allow-lists, rate limits, sandboxing, and reversible actions.
8. **No autonomous self-modification without gates.** Evolution must be proposed, evaluated, signed, and rollbackable.

## Current Baseline

HyperCode V2.4 already provides a substantial platform: a FastAPI backbone, agent swarm, Docker infrastructure, MCP gateway, self-healing, observability, security scanning, mission execution, and evolutionary capabilities. The repository documentation also identifies a broad service topology and multiple deployment profiles. Treat the current code and `WHATS_DONE.md` as the source of truth before implementing any roadmap item.

### Baseline constraints to preserve

- Use `docker-ce-cli`; never substitute `docker.io` for socket agents.
- Use `from app.X import Y` inside the HyperCode Python layout; never `from backend.app.X`.
- Never commit `.env` files or secrets.
- Keep the Stripe webhook rate-limit exemption.
- Keep Redis DB 1 for cache and DB 2 for rate limits.
- Keep `discord.py==2.4.0` and the `python -u -m cogs.bot` entrypoint for `broski-bot`.
- Run the repository's existing test, security, and evolution gates before pushing.

## Architecture Target

```text
┌────────────────────────────────────────────────────────────────────┐
│ Human / Neurodivergent Mission UX                                 │
│ Mission Control · BROski Terminal · CognitiveUplink · Discord      │
└───────────────────────────────┬────────────────────────────────────┘
                                │ mission + approval events
┌───────────────────────────────▼────────────────────────────────────┐
│ Mission Runtime                                                   │
│ durable state · checkpoints · retries · budgets · cancellations    │
│ graph execution · handoffs · human-in-the-loop approval            │
└───────────────┬───────────────────┬───────────────────┬────────────┘
                │                   │                   │
      ┌─────────▼────────┐ ┌────────▼─────────┐ ┌──────▼───────────┐
      │ Agent Contracts   │ │ Protocol Gateway  │ │ Evaluation +     │
      │ roles · identity  │ │ MCP · A2A-ready   │ │ Governance        │
      │ permissions       │ │ tool registry     │ │ traces · scores   │
      └─────────┬────────┘ └────────┬─────────┘ └──────┬────────────┘
                │                   │                   │
┌───────────────▼───────────────────▼───────────────────▼────────────┐
│ Existing HyperCode services: Core · Crew · Agent X · Healer ·      │
│ specialists · memory · Docker/Kubernetes · Redis/PostgreSQL ·     │
│ Prometheus/Grafana/Loki/Tempo · security scanning                  │
└────────────────────────────────────────────────────────────────────┘
```

## Priority 0 — Protect the Foundation

### P0.1 Establish roadmap truth

- [ ] Compare every proposed item against `WHATS_DONE.md`.
- [ ] Mark existing capabilities as `existing`, `partial`, `pilot`, or `future`.
- [ ] Record evidence links: source file, test, dashboard, or runbook.
- [ ] Add an owner, risk, acceptance test, and rollback plan to each implementation issue.

**Exit gate:** No roadmap item is claimed as new when it already exists in the repository.

### P0.2 Create an agent capability registry

Create a machine-readable registry for every built-in and dynamically generated agent.

Minimum fields:

```yaml
id: healer-agent
version: 1.0.0
role: service-recovery
description: Restores failed HyperCode services
inputs: [health_event]
outputs: [recovery_report]
tools: [docker.restart, logs.read]
permissions: [service:restart]
budget:
  max_steps: 12
  max_runtime_seconds: 300
risk_level: medium
approval_policy: approval-for-production
fallback_agent: crew-orchestrator
```

**Exit gate:** Crew Orchestrator can discover an agent, validate its contract, enforce permissions, and reject malformed manifests.

### P0.3 Make the approval boundary explicit

- Classify actions as read-only, reversible write, destructive write, financial, external communication, or self-modification.
- Require approval for destructive, financial, external-communication, production, and self-modification actions.
- Show the exact target, proposed change, evidence, and rollback method in Mission Control.
- Persist approvals and denials in the governance ledger.

**Exit gate:** A test proves that an unapproved high-impact tool call is blocked and auditable.

## Priority 1 — Protocol-Native Tooling

### P1.1 Expand MCP into the HyperCode tool plane

The existing MCP-GitHub work should become a unified tool plane. Add adapters in small, independently testable steps:

- Filesystem and workspace inspection.
- Docker and Compose operations.
- Prometheus queries and Grafana annotations.
- PostgreSQL and Redis read-only diagnostics.
- Supabase operations through explicit allow-lists.
- Stripe test-mode diagnostics only; preserve webhook protections.
- Discord messaging behind approval gates.
- HyperCode mission, memory, and BROski$ APIs.

Every tool needs:

- JSON schema input and output.
- Authentication and tenant context.
- Timeout, retry, and idempotency rules.
- Risk classification.
- Structured audit events.
- Unit, contract, and integration tests.

### P1.2 Add tool discovery and capability negotiation

Agents should request only the tools needed for the current mission. The gateway should return a filtered tool view based on agent identity, mission scope, user permissions, environment, and risk policy.

**Exit gate:** The same agent receives different tool visibility in development, staging, and production, with the reason recorded in the trace.

### P1.3 Prepare for agent-to-agent interoperability

Keep internal HyperCode events stable while preparing an A2A-compatible boundary for remote specialist agents. Begin with a narrow mission contract:

- Mission ID.
- Agent identity and version.
- Requested capability.
- Input references rather than unnecessary raw data.
- Progress events.
- Artefact references.
- Completion, failure, cancellation, and handoff states.

Do not expose the whole internal network. Use a broker or gateway, signed identity, scoped credentials, and explicit trust policies.

## Priority 2 — Stateful Mission Runtime

### P2.1 Introduce graph-based mission execution

Represent missions as explicit graphs rather than hidden prompt chains.

Initial graph:

```text
intake → plan → approval → implement → test → review → deploy → verify
                         │                         │
                         └────── revise ◄─────────┘

health incident → diagnose → safe repair → verify → report
                         └──────────────► human approval when risky
```

Each node must define:

- Input state and output state.
- Allowed tools.
- Retry policy.
- Timeout and budget.
- Success criteria.
- Escalation path.
- Checkpoint behaviour.

A LangGraph-style pilot is suitable for validating stateful graphs, checkpoints, resumability, and human-in-the-loop flows. Keep the first integration behind an adapter so HyperCode does not become coupled to one orchestration vendor.

### P2.2 Add durable checkpoints and resumability

- Store mission state separately from chat transcripts.
- Use PostgreSQL for durable mission records and Redis for short-lived coordination/cache only.
- Support pause, resume, cancel, retry-from-node, and replay-from-event.
- Compact old context into evidence-backed summaries.
- Keep artefacts and logs addressable by mission ID.

**Exit gate:** Killing an orchestrator during a mission and restarting it resumes from the latest valid checkpoint without duplicating an idempotent side effect.

### P2.3 Add mission budgets

Track and enforce:

- Wall-clock time.
- Model calls and token budget.
- Tool-call count.
- Container resources.
- Financial exposure.
- Human approval wait time.

Surface budget burn in Mission Control using short, clear status language.

## Priority 3 — Reliable Multi-Agent Collaboration

### P3.1 Standardise agent contracts

Every agent must declare:

- Identity, role, version, and owner.
- Required context.
- Input/output schemas.
- Tool permissions.
- Safety constraints.
- Handoff rules.
- Failure and fallback behaviour.
- Evaluation suite.

Use the existing agent identity cards, life plans, contract tests, guardrails, and governance ledger as the compatibility layer.

### P3.2 Detect role drift

Add a lightweight role-discipline check before and after important tool calls:

- Compare requested action with declared role.
- Detect permission escalation.
- Detect unexpected tool sequences.
- Ask for re-planning when an agent leaves its role.
- Record drift, repair, and final outcome.

Do not rely on prompt wording alone. Combine identity, policy, tool filtering, structured outputs, and runtime checks.

### P3.3 Build a reliability evaluation harness

Measure more than task completion:

- Tool selection accuracy.
- Argument/schema correctness.
- Recovery from tool errors.
- Duplicate-side-effect rate.
- Handoff success.
- Role adherence.
- Approval compliance.
- Evidence quality.
- Cost and latency.
- User-reported cognitive load.

Run evaluations against representative HyperCode missions and maintain a regression history by model, agent version, and environment.

**Exit gate:** A release cannot pass the evolution gate unless critical mission suites meet the repository's configured threshold and no high-severity policy regression is present.

## Priority 4 — Safe Self-Evolution

### P4.1 Convert Agent X evolution into a gated pipeline

The evolutionary pipeline should follow:

```text
proposal → impact analysis → patch → isolated build → tests → security scan
         → mission evals → human review → signed release → canary → observe
         → promote or rollback
```

Required controls:

- No direct mutation of production agents.
- Separate build and runtime credentials.
- Immutable candidate artefacts.
- Reproducible build metadata.
- Security and secret scanning.
- Contract and mission evaluations.
- Canary deployment.
- Automatic rollback on health or policy regression.
- Governance record for every stage.

### P4.2 Add evolution provenance

For every generated or modified agent, store:

- Parent version.
- Prompt/specification inputs.
- Model and model version.
- Source commit.
- Tests and evaluation scores.
- Security scan result.
- Approver.
- Deployment target.
- Rollback target.

### P4.3 Create a safe sandbox for experiments

Use isolated Docker/Kubernetes workloads with restricted network access, ephemeral credentials, resource limits, and synthetic or redacted data. Experiments must not access production secrets or unrestricted external tools.

## Priority 5 — Memory and Context Engineering

### P5.1 Separate memory types

Use explicit classes:

- Working memory: current node and immediate context.
- Episodic memory: mission events and outcomes.
- Semantic memory: verified facts, documentation, and patterns.
- Procedural memory: runbooks, skills, and agent contracts.
- User preference memory: consented interaction preferences.

Each memory entry needs provenance, timestamp, confidence, sensitivity, retention policy, and deletion path.

### P5.2 Make retrieval evidence-first

- Retrieve small, relevant chunks.
- Preserve source references.
- Prefer repository truth over stale summaries.
- Mark uncertain or conflicting evidence.
- Never allow memory to silently override current policy or user instruction.

### P5.3 Add context-pressure controls

When context grows, agents should:

1. Summarise completed work.
2. Preserve open decisions and blockers.
3. Keep exact artefact and commit references.
4. Drop redundant conversational text.
5. Ask for clarification only when the remaining uncertainty matters.

## Priority 6 — Security, Privacy, and Trust

### P6.1 Enforce least privilege at runtime

Permissions should be scoped by agent, mission, repository, environment, resource, and action. A tool registry alone is not a security boundary; enforce policy at the gateway and service owners.

### P6.2 Minimise cross-agent data

Pass references, summaries, and the minimum required fields instead of copying whole transcripts, secrets, or user data. Label data sensitivity and log the sharing decision.

### P6.3 Harden tool execution

- Validate all tool arguments.
- Use allow-lists for commands and paths.
- Block shell injection patterns.
- Apply timeouts and output limits.
- Use idempotency keys for external writes.
- Require approval for communication, payment, deployment, and deletion.
- Redact secrets from logs and traces.
- Verify container and image provenance.

### P6.4 Threat-model agent workflows

Maintain abuse cases for prompt injection, malicious repository content, tool poisoning, credential theft, data exfiltration, privilege escalation, denial of service, and unsafe self-evolution. Turn each high-risk scenario into a regression test.

## Priority 7 — Observability and Human Experience

### P7.1 Trace every mission

Use a consistent correlation model:

```text
user → mission → graph run → node → agent → model call → tool call → artefact
```

Emit structured events for planning, handoff, approval, retry, failure, repair, and completion. Connect traces to Prometheus metrics, Loki logs, Tempo spans, and Mission Control views.

### P7.2 Build an agent operations dashboard

Show:

- Active missions and current node.
- Agent health and queue depth.
- Tool-call latency and failure rate.
- Model cost and token burn.
- Approval queue.
- Role-drift events.
- Evolution candidates and gate status.
- Recovery actions.
- BROski$ rewards linked to verified outcomes.

### P7.3 Make the interface neurodivergent-first

- One next action at a time.
- Chunk large missions into visible steps.
- Use plain-language status labels.
- Preserve context across interruptions.
- Offer compact and deep views.
- Celebrate verified wins, not noisy activity.
- Allow reduced motion and reduced notification intensity.
- Make errors actionable and specific.

## Phased Delivery Plan

### Phase 0 — Truth and safety baseline

- [ ] Reconcile roadmap with `WHATS_DONE.md`.
- [ ] Publish agent capability registry schema.
- [ ] Document approval and risk taxonomy.
- [ ] Add a high-impact-action blocking test.
- [ ] Confirm current evolution gate and rollback path.

### Phase 1 — Tool plane pilot

- [ ] Register existing GitHub MCP tools in the capability registry.
- [ ] Add filesystem, Docker, observability, and read-only database adapters.
- [ ] Add schema validation, timeouts, idempotency, and audit events.
- [ ] Add environment-aware tool filtering.
- [ ] Display tool calls and approval state in Mission Control.

### Phase 2 — Stateful missions

- [ ] Implement one graph-backed coding mission.
- [ ] Add PostgreSQL checkpoints and Redis coordination.
- [ ] Support pause, resume, cancel, retry, and replay.
- [ ] Add mission budgets and cancellation propagation.
- [ ] Run a failure-injection test against orchestrator restart.

### Phase 3 — Evaluation and collaboration

- [ ] Standardise agent manifests and structured outputs.
- [ ] Add role-drift and permission-escalation checks.
- [ ] Build mission regression suites.
- [ ] Add model/agent scorecards and release thresholds.
- [ ] Pilot a narrow remote-agent handoff boundary.

### Phase 4 — Safe evolution

- [ ] Isolate Agent X candidate builds.
- [ ] Add provenance, signing, security scans, and canary deployment.
- [ ] Require human approval before promotion.
- [ ] Add automatic rollback and evolution audit views.
- [ ] Test malicious or low-quality candidate agents.

### Phase 5 — Ecosystem scale

- [ ] Expand protocol adapters without weakening core policy.
- [ ] Connect HyperAgent-SDK templates to the capability registry.
- [ ] Expose safe mission APIs to Hyper-Vibe Coding Course.
- [ ] Connect BROskiPets, Brain, Print Genie, and other ecosystem projects through scoped contracts.
- [ ] Publish contributor documentation for building compliant HyperCode agents.

## Priority Matrix

| Initiative | Value | Risk | First proof | Priority |
|---|---:|---:|---|---:|
| Capability registry | High | Low | Manifest validation test | P0 |
| Approval/risk boundary | Critical | Medium | Blocked high-impact tool test | P0 |
| MCP tool plane | High | Medium | GitHub + read-only diagnostics | P1 |
| Stateful mission graphs | Critical | Medium | Resumable coding mission | P2 |
| Evaluation harness | Critical | Medium | Regression scorecard | P3 |
| Role-drift detection | High | Medium | Drift-and-repair test | P3 |
| Safe Agent X evolution | Critical | High | Candidate-to-canary pipeline | P4 |
| Memory provenance | High | Medium | Evidence-backed retrieval test | P5 |
| Cross-agent minimisation | High | High | Sensitive-data boundary test | P6 |
| Mission operations UX | High | Low | Dashboard mission trace | P7 |

## Definition of Done for HyperCode V3

HyperCode V3 is ready for a public milestone when:

- Every active agent has a validated identity and capability contract.
- High-impact actions are blocked without explicit approval.
- Missions are stateful, resumable, cancellable, and auditable.
- Tool access is scoped by identity, mission, environment, and risk.
- Critical workflows have repeatable evaluation gates.
- Agent role drift and permission escalation are detectable.
- Self-evolution uses isolated builds, provenance, security checks, canaries, and rollback.
- Memory is evidence-backed, sensitivity-aware, and deletable.
- Mission traces connect users, agents, models, tools, and artefacts.
- The interface helps neurodivergent builders see the next useful step without losing the bigger pattern.
- Existing HyperCode sacred rules and completed work remain intact.

## Immediate Next Task

Build the **capability registry + approval boundary pilot** first. It is the smallest change that unlocks safer MCP expansion, stateful mission execution, evaluation, and future self-evolution.

> 🐶♾️ Stop apologising for your brain. Start building.
> 
> **Nice one BROski♾️!**