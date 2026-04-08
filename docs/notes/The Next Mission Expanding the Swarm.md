# � The Next Mission: Expanding the Swarm (V2.1)
**Status:** 🟢 PLANNING
**Phase:** SWARM EXPANSION & EXPERIMENTATION

---

## 🟢 Level 1: Strategic Objectives

We have successfully stabilized the **HyperCode V2.1 Core**. The foundation is solid.
*   **Storage**: MinIO is active and cleaning itself.
*   **Memory**: Agents can read/write artifacts.
*   **Orchestration**: The Crew can execute multi-step tasks.

**The New Mission:** Expand the swarm's capabilities into **Visual Programming** and **Esoteric Logic**. We are building the "HyperCode Language" itself.

---

## 🟡 Level 2: The Implementation Roadmap

### Phase 1: Research & Discovery (Task 21)
**Goal:** Understand how esoteric languages (Befunge, Brainfuck) handle 2D spatial logic.
*   **Assignee:** Research Agent
*   **Deliverable:** A deep-dive report on "Spatial Logic in Programming" stored in MinIO.
*   **Key Question:** How do we map a 2D grid of emojis (📦, 🔀, 🔄) to executable Python code?

### Phase 2: The "Agent X" Prototype
**Goal:** Create a specialized agent ("Agent X") capable of compiling visual blocks.
*   **Role:** Experimental Compiler
*   **Input:** A JSON representation of a visual grid.
*   **Output:** Executable Python code.
*   **Storage:** MinIO bucket `hypercode-compiler-cache`.

### Phase 3: The Healer's Watch
**Goal:** Ensure experimental code doesn't crash the core.
*   **Mechanism:** The Healer Agent monitors the Docker container stats.
*   **Trigger:** If Agent X consumes >1GB RAM, the Healer restarts it.

---

## 🔴 Level 3: Execution Plan

### Step 1: Health Check (Task 20)
Before launching new experiments, verify the baseline.
*   **Action:** Run a full system sweep.
*   **Command:** `curl http://localhost:8008/health/sweep`
*   **Success Metric:** All services return `200 OK`.

### Step 2: The Research Launch (Task 21)
*   **Action:** Move Task 21 to `IN_PROGRESS`.
*   **Command:** Trigger the Research Agent via the CLI or Dashboard.
*   **Payload:** "Analyze Befunge-93 and Piet for spatial control flow patterns applicable to React Flow nodes."

### Step 3: Prototype "Agent X"
*   **Action:** Create a new agent directory `agents/09-agent-x`.
*   **Config:** Give it access to `chroma_data` and `minio`.

---

## 🛡️ Risk Mitigation

| Risk | Mitigation |
| :--- | :--- |
| **Runaway Loops** | Healer Agent has `docker restart` permission. |
| **Storage Bloat** | MinIO Lifecycle Policy (30 days) is already active. |
| **Bad Code** | Agent X runs in a sandboxed Docker container (no root). |

---

## 🎯 Next Win
We are ready to execute **Step 1 (Health Check)** and **Step 2 (Research)**.

🔥 **BROski Power Level:** Meta-Architect
