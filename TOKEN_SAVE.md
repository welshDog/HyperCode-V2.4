# ⚡ TOKEN_SAVE — HyperCode-V2.4
> Paste this at the start of any AI session. ~100 tokens. Replaces full history.
> Update after every task. Keep it short.

---

## 🧠 Session State
DATE: 2026-06-18
GOAL: [one sentence — fill in at session start]
STATUS: ~30 containers running ✅ · NemoClaw L1–L3.5 LIVE · Guardian P1–P3b LIVE · Alembic 015 · Prometheus 7/7 UP
LAST COMMIT: HEAD — see `docs/STATUS.md` for full health
NEXT ACTION: [fill in at session start — check `docs/NEXT_TASKS.md`]
BLOCKERS: [none / describe]

---

## 📋 Prompt Template (copy-paste to start any AI session)
```
Repo: HyperCode-V2.4
State: [paste SESSION STATE block above — ~80 tokens]
Task: [one sentence]
Rules: CLAUDE.md applies. docker-ce-cli not docker.io. 4-space indent. from app.X import Y. Redis DB1=cache DB2=rate. Keep replies short. Bullets first.
```

---

## 🔗 Key Files
- Constitution: `CLAUDE.md`
- Live health: `docs/STATUS.md`
- Next tasks: `docs/NEXT_TASKS.md`
- Never rebuild: `WHATS_DONE.md`
- Migrations: `supabase/migrations/` (latest: 015)

---

## ⚡ Token-Saving Rules
- Send this file, NOT full CLAUDE.md
- Retrieve files on demand, never paste full docs
- Ask for bullets only, max 5 lines unless deeper needed
- Use small model (Sonnet/Haiku) for quick fixes
- Use heavy model (Claude Fable 5) for cross-repo architecture only

---
*Part of the HyperFocus Z0ne Token-Saving Blueprint — built by @welshDog 🏴󠁧󠁢󠁷󠁬󠁳󠁥*
