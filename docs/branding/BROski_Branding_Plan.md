
# 🧠 BROski Hyper Branding & Enhancement Plan

Based on the strategic audit (`BROski Hyper Branding`), here is the concrete plan to transform HyperCode into the "BROski Orchestrator" – an ADHD-friendly, dopamine-driven AI agent hub.

## 🚀 Phase 1: Identity & Personality (Quick Wins)

**Goal:** Shift from "Corporate LinkedIn" to "Hype-Man Orchestrator".

- [ ] **Emoji-fication of Logs**: Update `structlog` configuration to prefix log levels with emojis (e.g., `INFO` -> `🧠 INFO`, `ERROR` -> `🔥 ERROR`, `WARNING` -> `⚠️ WARN`).
- [ ] **Agent Persona Injection**: Update system prompts for the Orchestrator and Agents to adopt the "BROski" persona.
    - *Example*: "Yo, I'm BROski Orchestrator. I break down massive tasks into dopamine snacks. Let's cook. 🍳"
- [ ] **Visual Status Updates**: Change "Mission Assigned" logs to something like "🚀 Mission Locked: Agent X is on the case!"

## 🛠 Phase 2: User Experience & Documentation

**Goal:** Make the "Ferrari" driveable for everyone.

- [ ] **README Overhaul**:
    - Add "🚀 Run Your First Workflow" section with exact `curl` commands.
    - Add "Hyperfocus-Optimized" badge.
- [ ] **Architecture Diagram**: Create `docs/ARCHITECTURE.md` with a Mermaid chart showing the flow (User -> API -> Redis -> Orchestrator -> Agents).
- [ ] **Example Workflow**: Add `examples/quickstart_workflow.json` that users can POST to the API.

## 🎮 Phase 3: Gamification & Neurodivergent UX

**Goal:** Leverage the unique value prop: "ADHD-optimized AI agent crews".

- [ ] **Dopamine Micro-Tasks**: Update the `TaskChunker` logic (in Orchestrator) to explicitly break tasks into 15-25 minute "Pomodoro" blocks.
- [ ] **Visual Output Mode**:
    - Instruct agents to output Markdown with Mermaid diagrams by default.
    - Use ASCII art for wireframes in CLI output.
- [ ] **BROski Coins (Concept)**: Plan the database schema for a "Gamification" table tracking completed missions as "XP" or "Coins".

## 🤖 Phase 4: Tools & Agency

**Goal:** Give agents hands to touch the world.

- [ ] **Tool Registry**: Implement the `Tool` interface (similar to the TypeScript example in the audit, but in Python).
- [ ] **Web Search Tool**: Integrate a search API (Brave/DuckDuckGo) for the `Researcher` agent.
- [ ] **File I/O**: Allow agents to read/write to a sandboxed `workspace/` directory.

## 📅 Action Plan (Next Session)

1.  **Execute Phase 1**: Update `app/core/logging.py` and `app/services/orchestrator.py` with emojis and personality.
2.  **Execute Phase 2**: Update `README.md` with the curl example.
3.  **Brainstorm Phase 3**: Detail the "BROski Coin" economy.

Let's get this party started. 🔥
