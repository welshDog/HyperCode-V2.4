# 🛣️ Agent Factory v2 Implementation Roadmap

**Version**: 2.0.0
**Status**: Active
**Owner**: Agent X (The Architect)
**Goal**: Transform the Agent Factory into an enterprise-grade **Agent Orchestration Platform (AOP)** capable of managing dynamic, secure, and resilient multi-agent crews.

This roadmap breaks down the implementation into four distinct phases, ensuring a balanced approach to functionality, reliability, performance, and security.

---

## 🏗️ Phase 1: The Core (Orchestration & Lifecycle)
**Timeline**: Weeks 1-2
**Focus**: Enabling multi-agent crew assembly and robust lifecycle tracking.

### 🔴 Issue A: Crew Manifest & Assembly System
**Objective**: Implement the foundational logic to spawn and manage teams of agents from a single definition.

#### Implementation Tasks
- [ ] **Define `CrewManifest` Schema** (Pydantic/JSON Schema)
    - `crew_id`: UUID for the session/mission.
    - `agents`: List of `AgentProfile` references with overrides (tools, env vars).
    - `network_config`: Shared context settings (Redis bus, vector store namespace).
- [ ] **Implement `/crews/assemble` Endpoint**
    - **Logic**: Validate manifest -> Request resources -> Spawn agents in parallel.
    - **Output**: JSON object with `crew_id`, `endpoints` map, and `status`.
- [ ] **Develop Dynamic Composition Logic**
    - Support "Just-in-Time" (JIT) role assignment.
    - Inject `CREW_ID` and `REDIS_URL` into agent environments during spawn.

#### Acceptance Criteria
- [ ] Valid manifest spawns N agents successfully.
- [ ] All agents in a crew can ping the shared Redis bus.
- [ ] `/crews/{id}/status` returns aggregated health of all members.

#### Risks & Mitigation
- **Risk**: Slow spawn times causing timeouts. -> **Mitigation**: Implement async spawning with Webhooks/SSE for status updates.

---

### 🔴 Issue B: Extended Lifecycle & Watchdog
**Objective**: Move beyond simple "running/stopped" to a self-healing state machine.

#### Implementation Tasks
- [ ] **Extend Registry Schema**
    - Add state enum: `PROVISIONING`, `WARMING`, `READY`, `BUSY`, `HIBERNATING`, `DRAINING`.
    - Add `last_heartbeat` and `restart_count` fields.
- [ ] **Implement Watchdog Service** (Celery Beat / Background Task)
    - **Monitor**: Check `last_heartbeat` every 10s.
    - **Logic**: 
        - If > 30s: Mark `UNHEALTHY`.
        - If `UNHEALTHY` > 60s: Trigger `restart_agent` workflow.
- [ ] **Event Tracking**
    - Log all state transitions to `audit_logs` table (PostgreSQL).

#### Acceptance Criteria
- [ ] Registry accurately reflects real-time agent state.
- [ ] Killing a container manually triggers an automatic restart within 60s.
- [ ] Full audit trail of lifecycle events is queryable.

---

## 🧪 Phase 2: Reliability (The Turing Gym)
**Timeline**: Weeks 3-4
**Focus**: Automated validation to ensure agents are functional before production use.

### 🔴 Issue C: Automated Validation Framework
**Objective**: Create "The Turing Gym" to continuously test agent cognitive and functional capabilities.

#### Implementation Tasks
- [ ] **Design Test Case Schema**
    - Input: Prompt/Task.
    - Expected Output: Regex match, File existence, or Function call signature.
- [ ] **Implement "Hello World" Scenarios**
    - **Task**: "Write a Python script that prints 'Hello HyperCode' to `hello.py`".
    - **Validation**: Check file existence and content inside container.
- [ ] **Develop Reporting Engine**
    - Generate JSON/HTML reports: Pass/Fail rate, Latency, Token usage.
    - Integrate with Prometheus for long-term benchmarking.
- [ ] **Regression Detection**
    - Run Gym suite on every Agent Profile update.

#### Acceptance Criteria
- [ ] CI pipeline fails if critical Gym tests fail.
- [ ] Performance benchmarks (latency/tokens) are recorded for every release.
- [ ] "Hello World" test passes reliably for all standard coding agents.

---

## 🚀 Phase 3: Performance (Warm Pools & Scaling)
**Timeline**: Weeks 5-6
**Focus**: Minimizing latency and optimizing resource throughput.

### Implementation Tasks
- [ ] **Implement Warm Pool Manager**
    - Maintain a pool of `N` generic "base" containers (Python + Common Libs).
    - **Logic**: On spawn request, grab from pool -> Mount specific code/tools -> Promote to `READY`.
- [ ] **Resource Allocation Algorithms**
    - Implement "Bin Packing" strategy for placing agents on Docker hosts (if multi-node).
    - Enforce CPU/Memory limits based on Profile tier.
- [ ] **Scaling Policies**
    - **Scale Out**: Increase pool size during high load (metrics-driven).
    - **Scale In**: Hibernate idle agents after TTL (e.g., 10 mins idle).

#### Acceptance Criteria
- [ ] Agent startup latency < 2s (using warm pool).
- [ ] System handles 50 concurrent agent spawns without degradation.
- [ ] Idle resources are reclaimed within defined TTL.

---

## 🔒 Phase 4: Security (Isolation & RBAC)
**Timeline**: Weeks 7-8
**Focus**: Hardening the platform against unauthorized access and breakouts.

### Implementation Tasks
- [ ] **Container Isolation Strategy**
    - **Network**: Implement Docker Network Policies (deny-all ingress/egress by default).
    - **Filesystem**: Read-only root filesystem with ephemeral `/workspace` volume.
- [ ] **Role-Based Access Control (RBAC)**
    - **Agent Identity**: Issue short-lived JWTs for each agent on startup.
    - **Scopes**: `crew:read`, `tool:exec`, `file:write`.
    - **Middleware**: Validate JWT scopes on all Factory API calls.
- [ ] **Security Auditing**
    - Log all privileged actions (spawn, stop, tool execution) to immutable audit log.

#### Acceptance Criteria
- [ ] Agents cannot access other crews' data (network isolation verified).
- [ ] Agents cannot modify their own root filesystem.
- [ ] API rejects requests without valid JWTs/Scopes.

---

## 📅 Milestones & Success Metrics

| Phase | Milestone | Success Metric |
| :--- | :--- | :--- |
| **1. Core** | Crew Assembly API Live | Spawn 5-agent crew in < 10s |
| **1. Core** | Watchdog Active | Auto-recovery from crash in < 60s |
| **2. Reliability** | Turing Gym Integrated | 100% Pass rate for Prod profiles |
| **3. Performance** | Warm Pools Active | Startup Latency < 2s (p95) |
| **4. Security** | RBAC Enforced | Zero unauthorized cross-crew access |
