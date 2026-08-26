# HyperCode AI Agent Protocol Research Report — 2026

> **Prepared for:** HyperCode-V2.4
> **Date:** 2026-08-26
> **Scope:** AI agent architecture, MCP tools, A2A coordination, reliability, governance, security, observability, and future evolution.

## Executive summary

HyperCode should not evolve by adding agents indiscriminately. The strongest future architecture is a governed agent operating system built around four separations:

1. **Planning versus execution.** A planning model proposes a mission graph; deterministic services and scoped agents execute it.
2. **Tools versus agents.** MCP exposes tools and data; A2A coordinates independent agents.
3. **Capability versus permission.** An agent may be capable of an action without being permitted to perform it.
4. **Autonomy versus accountability.** Autonomous progress must still produce approvals, traces, evidence, provenance, and rollback paths.

The recommended HyperCode stack is:

```text
Human experience
  → HyperCode policy and mission control
  → MCP tool plane + A2A agent plane
  → HyperFlow / Crew Orchestrator runtime
  → Mission Evaluator + governance ledger
  → OpenTelemetry evidence plane
  → Docker, Kubernetes, databases, and ecosystem services
```

This direction builds on HyperCode’s existing Crew Orchestrator, Agent X, Healer, CognitiveUplink, MCP work, observability stack, evolution pipeline, Mission Evaluator, Fleet Dependency Graph, and neurodivergent-first UX. Existing work must be checked against `WHATS_DONE.md` before implementation.

## 1. Current HyperCode position

HyperCode already has the foundations of an autonomous platform rather than a single chatbot. The repository describes a FastAPI core, Docker-based service topology, specialist agents, self-healing, MCP gateways, mission execution, security controls, Prometheus/Grafana/Loki/Tempo observability, and Agent X evolutionary workflows.

Recent project progress also includes HyperFlow goal matching, Mission Evaluator v1, and a live Fleet Dependency Graph with the evolution harness passing its milestone gate. These capabilities should be extended, not duplicated.

### Architectural constraints

- Keep planning LLMs separate from execution services.
- Safety Shepherd must fail closed in enforce mode.
- DRY_RUN is the safe default for new or risky execution.
- Use the existing swarm memory capability rather than creating another brain-named service.
- Keep one BROski oversight agent for COO-style concerns.
- Apply the client-side provider denylist during model discovery.
- Preserve HyperCode sacred rules for Docker, imports, secrets, Redis databases, Stripe webhooks, and the Discord bot.

## 2. Protocol stack map

### MCP: tools and data

The Model Context Protocol provides a common way for an LLM host or agent to access external tools, resources, and prompts. MCP tools represent arbitrary code execution, so tool discovery is not equivalent to trust. The current MCP specification explicitly emphasizes user consent and cautions that tool descriptions must not automatically be trusted. [web:116]

The 2026-07-28 MCP update strengthens authorization concerns, including protected-resource metadata, resource indicators, issuer validation, and client metadata documents. HyperCode should adopt the exact specification version deliberately and pin compatibility tests to it. [web:129][web:131]

### A2A: independent agents

A2A is designed for communication between independent agents, potentially hosted by different services, companies, or vendors. Agent Cards describe an agent’s identity, capabilities, skills, endpoint, formats, and authentication requirements. A2A tasks provide a lifecycle for submitted, working, input-required, completed, failed, and canceled work. [web:126][web:134]

An Agent Card is discovery metadata, not proof of trust. HyperCode must authenticate the remote agent, validate its trust zone, constrain the task scope, and verify returned artefacts before accepting the result.

### HyperCode-owned control plane

MCP and A2A should sit below a HyperCode-owned policy layer. The policy layer decides whether a protocol action is allowed, needs approval, must run in DRY_RUN, or must be denied.

```text
Protocol compatibility ≠ permission
Capability ≠ authorization
Agent Card ≠ trust
Tool result ≠ verified evidence
```

## 3. MCP implementation plan

### Server boundaries

Use several focused MCP server groups instead of one unrestricted gateway:

| Group | Examples | Default handling |
|---|---|---|
| Context | GitHub read, docs, memory, Prometheus queries | Read-only |
| Development | Tests, linters, Docker inspect, logs | Sandboxed |
| Controlled writes | Branches, files, staging changes | Approval or scoped policy |
| Communication | Discord, email, issue comments | Explicit approval |
| Critical actions | Stripe, deletion, production deployment | Human approval |
| Evolution | Candidate builds, evaluations, promotion | Isolated and gated |

### MCP tool contract

Every tool should define:

- Stable identifier and version.
- JSON input and output schema.
- Owning service.
- Required role and permission.
- Risk category.
- Data sensitivity.
- Timeout and cancellation behaviour.
- Retry policy.
- Idempotency requirements.
- Audit event.
- Test suite.

### MCP security tests

- Tool discovery returns only tools permitted for the current agent and mission.
- Malicious text in a tool description cannot override policy.
- Invalid arguments are rejected before execution.
- Timeouts cancel work and do not leave uncontrolled processes.
- Retries cannot duplicate non-idempotent writes.
- Secrets are redacted from logs, traces, memory, and outputs.
- A tool result cannot automatically trigger a second privileged tool call without policy re-evaluation.
- MCP server version or authorization changes cause compatibility tests to run.

MCP tool poisoning is an active security concern: malicious descriptions or metadata can influence agents into leaking data or executing unwanted actions. Security guidance recommends treating MCP servers as supply-chain components and validating tool descriptions at runtime. [web:137][web:147]

## 4. A2A implementation plan

### Agent Card requirements

HyperCode’s A2A-compatible agents should publish a versioned card containing:

- Agent name, stable ID, version, and owner.
- Endpoint and supported transports.
- Skills and capability descriptions.
- Input and output modes.
- Authentication requirements.
- Streaming and push support.
- Trust zone.
- Maximum task duration and resource limits.
- Data handling policy.
- Evidence and artefact formats.

### Task envelope

A HyperCode A2A task should include:

```yaml
mission_id: mission-123
parent_node: security-review
requester:
  agent_id: crew-orchestrator
  version: 3.0.0
target_skill: security-review
input_ref: artifact://candidate/abc123
sensitivity: internal
budget:
  max_seconds: 300
  max_steps: 20
approval: approved-for-review
required_evidence:
  - findings.json
  - trace-reference
cancellation_token: cancel-456
```

Remote agents should return bounded messages and content-addressed artefact references. They should not return unbounded transcripts or receive more raw data than the skill requires.

### A2A security tests

- Invalid or unsigned Agent Cards are rejected.
- Authentication and issuer validation succeed before task creation.
- Trust-zone policy is enforced.
- Task cancellation reaches the remote agent.
- Network interruption does not create duplicate side effects.
- Artefacts are schema-validated and content-addressed.
- A remote agent cannot escalate scope during a task without a new policy decision.
- Returned output cannot directly invoke privileged tools.
- Long-running task status is visible in Mission Control.

## 5. Reliability research

Agent capability is increasing faster than dependable execution. Recent reliability research argues that agent systems need explicit measures for consistency, robustness, predictability, and safety rather than relying on one successful run. [web:78]

Long-horizon research is especially relevant to HyperCode. Long-Horizon-Terminal-Bench evaluates containerized terminal tasks using dense, partial-credit signals rather than only pass/fail outcomes. This is a useful model for measuring how far a HyperCode mission progresses before failure. [web:139]

A further reliability framework proposes the Reliability Decay Curve, Variance Amplification Factor, Graceful Degradation Score, and Meltdown Onset Point for long-running agents. HyperCode can adapt these concepts to its existing mission and evolution harnesses. [web:145]

### HyperCode reliability scorecard

Measure per model, agent version, mission, and environment:

- Completion rate.
- Repeated-run consistency.
- Progress before failure.
- Tool-selection accuracy.
- Schema and argument correctness.
- Recovery after tool failure.
- Duplicate-side-effect rate.
- Handoff success.
- Role adherence.
- Approval compliance.
- Evidence quality.
- Latency, token use, and cost.
- Cognitive load and interruption recovery.

## 6. Governance and human collaboration

Interoperability protocols provide transport and data models, but they do not fully solve governance. Recent analysis identifies gaps around community decision-making, deliberation, dissent, and collective accountability in agent interoperability systems. [web:75]

HyperCode should add a governance layer with:

- Trust zones and membership.
- Role-based review.
- Preserved dissent and alternative proposals.
- Human escalation.
- Quorum for critical changes.
- Signed decisions.
- Replayable decision history.
- Governance events linked to mission traces.

Human approval should not be a generic “click yes” interruption. It should show the exact target, proposed change, evidence, risk, cost, affected services, and rollback option. Human-in-the-loop research also warns that supervision can fail when humans lack timely context or meaningful intervention authority. [web:151][web:153]

## 7. Agent provenance and AIBOM

Traditional software bills of materials do not capture the complete runtime history of dynamic agents. Emerging work on agentic AI bills of materials argues for recording model, prompt/specification, tools, dependencies, runtime, generated outputs, evaluations, and deployment information. [web:92]

### HyperCode provenance chain

```text
agent version
  → model and provider
  → prompt/specification
  → tools and permissions
  → dependencies and image digest
  → runtime environment
  → outputs and artefacts
  → tests and evaluation scores
  → approval and deployment
  → rollback target
```

This should become the evidence record for Agent X evolution and incident response.

## 8. Self-evolving agents

Self-evolving agent research supports separating the evolution mechanism from the runtime reasoning loop, while highlighting unresolved risks around behavioural stability, inheritance of bad behaviours, and uncontrolled changes. [web:82]

HyperCode’s safe evolution pipeline should be:

```text
proposal
  → impact analysis
  → isolated patch
  → reproducible build
  → tests
  → security scan
  → mission evaluations
  → independent review
  → human approval
  → signed candidate
  → canary
  → observe
  → promote or rollback
```

No candidate should directly mutate a production agent. Build credentials and runtime credentials must remain separate. Every promotion must have provenance and a rollback target.

## 9. Dynamic agent teams

More agents can increase cost, coordination overhead, and failure surface. Research on dynamic agent elimination suggests that removing redundant agents can improve token efficiency and collaboration quality. [web:102]

HyperCode should test dynamic crew sizing around HyperFlow:

1. Start with the smallest capable crew.
2. Add an agent only when a missing capability is evidenced.
3. Remove redundant agents.
4. Limit communication rounds.
5. Preserve a human-readable explanation for each team change.

This extends HyperFlow rather than replacing it with a new meta-orchestrator. Novel-goal decomposition should remain a separately tested extension.

## 10. Memory and context engineering

Long missions need more than a larger transcript. HyperCode should separate:

- Working memory for the current graph node.
- Episodic memory for mission events and outcomes.
- Semantic memory for verified facts and documentation.
- Procedural memory for skills, runbooks, and contracts.
- Preference memory for consented user interaction preferences.

Each memory item should include provenance, timestamp, confidence, sensitivity, retention, and deletion metadata. Retrieval should preserve evidence references and never silently override current policy.

Context compaction should preserve:

- Completed work.
- Open decisions.
- Blockers.
- Exact artefact references.
- Commit and test references.
- User approvals and denials.

## 11. Observability

OpenTelemetry’s GenAI work provides a path toward common telemetry for model calls, agent operations, MCP calls, token usage, and evaluation signals. HyperCode should adopt versioned internal events and map them to OpenTelemetry so core logic is not locked to a changing semantic convention. [web:95][web:105]

### Trace hierarchy

```text
user
  → mission
  → graph run
  → node
  → agent
  → model call
  → MCP/A2A operation
  → tool/task result
  → artefact
  → evaluation
```

Required fields should include mission ID, graph run, node, agent version, protocol, server, tool or skill, risk, approval state, sensitivity, budget, and outcome. Do not capture raw secrets or sensitive prompts by default.

## 12. Physical-world agents

Print Genie, camera monitoring, Raspberry Pi integrations, and future robotics require a separate safety class. A physical action should need:

- Signed capability card.
- Device identity.
- Reservation or exclusive lock.
- Physical safety limits.
- Operator confirmation token.
- Measurement units and uncertainty.
- Emergency stop.
- Safe rollback or shutdown.

Physical-world execution should never share an unrestricted tool path with read-only diagnostics. Protocols for autonomous scientific instruments reinforce the need for explicit links between agent plans and instrument operations. [web:83]

## 13. Neurodivergent-first UX research

HyperCode’s neurodivergent-first design should be evaluated as an engineering outcome. Study:

- Time to understand the next action.
- Number of context switches.
- Recovery after interruption.
- Error comprehension.
- Choice overload.
- Notification fatigue.
- Compact versus deep explanation preference.
- User confidence compared with actual mission state.
- Value of celebrations versus distraction.

Use opt-in, consented research. Never use diagnosis as a performance label. The goal is to reduce cognitive load while keeping the bigger system pattern visible.

## 14. Recommended delivery roadmap

### Phase 0: Truth and safety

- Reconcile this research with `WHATS_DONE.md`.
- Mark each capability existing, partial, pilot, or future.
- Publish capability registry schema.
- Define risk and approval taxonomy.
- Add high-impact-action blocking tests.
- Confirm DRY_RUN and rollback behaviour.

### Phase 1: MCP tool plane

- Inventory current MCP servers and tools.
- Add registry-backed tool discovery.
- Add environment-aware filtering.
- Harden schemas, timeouts, retries, cancellation, redaction, and idempotency.
- Start with read-only GitHub, filesystem, Docker inspect, logs, and Prometheus.

### Phase 2: A2A pilot

- Publish one internal Agent Card.
- Implement one scoped reviewer task.
- Support lifecycle states and cancellation.
- Return verified artefact references.
- Add trust-zone and authentication tests.

### Phase 3: Reliability and evidence

- Extend Mission Evaluator with repeated-run and fault-injection tests.
- Add partial-credit progress metrics.
- Add reliability decay and graceful degradation measurements.
- Connect protocol traces to Grafana, Loki, Tempo, and the governance ledger.

### Phase 4: Safe evolution

- Add AIBOM-style provenance.
- Isolate Agent X candidates.
- Add independent review through A2A.
- Require human promotion approval.
- Canary and automatically roll back on health or policy regression.

### Phase 5: Ecosystem scale

- Connect HyperAgent-SDK templates.
- Expose safe mission APIs to Hyper-Vibe Coding Course.
- Integrate Brain, BROskiPets, Print Genie, and other projects through scoped contracts.
- Publish contributor documentation for compliant agents.

## 15. First practical experiment

### HyperCode Agent Reliability Lab

Choose one existing coding or healing mission and run it repeatedly in an isolated environment.

Test matrix:

- Normal execution.
- Tool timeout.
- Malformed tool response.
- Stale repository instruction.
- Orchestrator restart.
- Human correction mid-mission.
- Provider/model substitution.
- Partial network failure.
- Duplicate retry attempt.
- Approval denial.

Output:

- Mission trace.
- Reliability scorecard.
- Failure timeline.
- Cost and latency report.
- Evidence bundle.
- Recommended guardrail.

This is the fastest way to turn HyperCode’s future strategy into measurable engineering progress.

## Final recommendation

HyperCode should own the policy, mission, evidence, governance, and human-experience layers. Adopt MCP for tools and data. Adopt A2A for independent-agent coordination. Keep planning separate from execution. Make reliability, provenance, and safe evolution first-class platform capabilities.

The winning position is not “the platform with the most agents.” It is:

> **The neurodivergent-first agent platform where powerful agents can collaborate, act, recover, and evolve—without losing human control or evidence of what happened.**
