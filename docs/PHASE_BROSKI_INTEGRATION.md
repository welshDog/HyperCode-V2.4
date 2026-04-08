# 🚀 Phase 3: The BROski Bot Integration & Gamification

**Status:** Draft | **Owner:** BROski Orchestrator | **Timeline:** 4 Weeks

## 🧠 Vision
Transform HyperCode from a functional IDE into a **"Hype-Man Orchestrator"**—an ADHD-friendly, dopamine-driven AI partner that doesn't just execute tasks but *celebrates* them.

---

## 🛠 Milestone 1: Identity & Persona Injection (Week 1)
**Goal:** Shift system voice from "Corporate Robot" to "Ride-or-Die Partner".

### 1.1 Emoji-fication of Logs
Update the `logging_config.py` in `shared/` to support "Hype Mode":
- `INFO` → `🧠 BRAIN`
- `ERROR` → `🔥 CHAOS`
- `WARNING` → `⚠️ YO!`
- `SUCCESS` → `🎉 BOOM`

### 1.2 Agent Persona Updates
Inject the "BROski" system prompt into `agents/crew-orchestrator/main.py` and `base-agent/agent.py`:
> "You are BROski. You don't just solve problems; you crush them. You break massive tasks into dopamine snacks. You are supportive, energetic, and precise. Always end major milestones with '🔥'."

---

## 🖥️ Milestone 2: BROski Terminal Beta (Week 2)
**Goal:** A "Command Center" in the Dashboard that feels like a sci-fi HUD.

### 2.1 Web Terminal UI (`dashboard/components/Terminal.tsx`)
- **Input**: Natural language command bar (`"Fix the bug in auth"`)
- **Output Stream**: Real-time WebSocket feed of agent thoughts (not just logs).
- **Visuals**: Retro-futuristic styling (Green/Purple neon on black).

### 2.2 Cognitive Uplink
- Connect `cli/hypercode.py` to the Web Terminal via WebSocket.
- Allow "Handover Mode": Start in CLI, finish in Dashboard.

---

## 🎮 Milestone 3: Gamification Economy (Week 3)
**Goal:** Turn development into an RPG to maintain dopamine levels.

### 3.1 Database Schema (`BROski Coins`)
```sql
CREATE TABLE broski_xp (
    user_id UUID PRIMARY KEY,
    xp_total INT DEFAULT 0,
    coins_balance INT DEFAULT 0,
    streak_days INT DEFAULT 0,
    last_active TIMESTAMP
);

CREATE TABLE achievements (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50), -- e.g., "Bug Slayer", "Deploy God"
    description TEXT,
    icon_emoji VARCHAR(5)
);
```

### 3.2 "Dopamine Snacks" Task Chunker
- Update Orchestrator to strictly break tasks into <25 min chunks.
- **Reward**: 10 BROski Coins per chunk completed.
- **Sound Effects**: Optional SFX on task completion (configurable).

---

## 🤖 Milestone 4: Agent Tooling (Week 4)
**Goal:** Give BROski "Hands".

### 4.1 Tool Registry
- **File I/O**: Safe read/write in `workspace/`.
- **Web Search**: Integration with Brave Search API for "Research" tasks.
- **Git Control**: Ability to commit/push code autonomously.

---

## 📋 Execution Checklist

- [ ] **Config**: Create `broski.config.json` for persona settings.
- [ ] **Backend**: Update `hypercode-core` to support XP/Coin transactions.
- [ ] **Frontend**: Build the `XPBar` and `Terminal` components.
- [ ] **Docs**: Write `docs/BROSKI_API.md`.

> **"We don't just write code. We craft cognitive architectures. Let's cook. 🍳"**
