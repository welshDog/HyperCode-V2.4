---
name: hyper-context-restore
description: >
  Instant session restore for the HyperCode ecosystem — reads WHATS_DONE.md,
  CLAUDE_CONTEXT.md, and recent git history to deliver a sharp "welcome back"
  briefing in seconds. Use this skill the moment Lyndz (or any HyperCode dev)
  says anything like: "where was I", "catch me up", "what was I doing", "what
  did I build", "remind me what's next", "restore context", "new session",
  "I forgot what I was doing", "what's the project status", or just opens a
  session and seems unsure where to start. Also trigger proactively at the
  start of any session in the HyperCode project if no clear task has been
  given yet. This skill is the antidote to ADHD context-switching paralysis —
  use it generously and early.
---

# HyperCode Context Restore

The goal is simple: get Lyndz back into flow in under 30 seconds. No walls of
text. No hunting through files. One sharp briefing, then get out of the way.

## Why this matters

Lyndz has ADHD + Autism + Dyslexia. Blank-screen paralysis at the start of a
session — "wait, where was I?" — is a real friction point that can derail an
entire evening. This skill removes that friction completely. The briefing should
feel like a trusted teammate saying "hey, you were here, this is what's next."

## Step 1 — Read the memory files (always do all three)

Read these in order — they are Lyndz's external memory system:

1. **`WHATS_DONE.md`** in the V2.4 repo root
   - Extract: the last 3–5 items under `✅ BUILT AND WORKING` (most recent ones)
   - Extract: ALL items under `🚀 NEXT UP`
   - Extract: anything in `🔧 ONE-TIME MANUAL STEPS REMAINING`

2. **`CLAUDE_CONTEXT.md`** in the V2.4 repo root (or the uploaded one)
   - Extract: current phase status (what phase just completed)
   - Extract: any "NEXT OPTIONS" section
   - Skip: anything already covered by WHATS_DONE.md

3. **Git log** — run `git -C <repo_path> log --oneline -7`
   - Shows what was actually committed recently
   - More honest than docs (docs can lag behind code)

If any file is missing or unreadable, skip it gracefully — don't error out.

## Step 2 — Deliver the briefing

Format it exactly like this. Short. Scannable. ADHD-friendly.
No extra sections. No padding. This is the whole output:

---

**👋 Welcome back, Bro! Here's where you are:**

**✅ Last built** *(2–3 bullets max, most recent things only)*
- [thing 1]
- [thing 2]
- [thing 3 if needed]

**🔧 Still needs your hand** *(only if there are manual steps)*
- [manual step 1]
- [manual step 2 if needed]

**🎯 Your next move**
→ [THE single most important next action — one line, specific, actionable]

**📋 Full backlog** *(collapsed — just list items, no descriptions)*
- [next up item 1]
- [next up item 2]
- [next up item 3]
- *(+ N more in WHATS_DONE.md)*

---

## Picking "Your next move"

This is the most important part. One action. Specific. Pick it by:

1. Is there a critical/broken thing? → fix that first
2. Is there a quick win (<30 min)? → lead with momentum
3. Otherwise → first item from NEXT UP list

Never say "check WHATS_DONE.md" as the next move — that's lazy.
Give a real, specific action like:
- "Run `stripe listen` + test card to verify E2E checkout"
- "Run `docker exec celery-worker python -c 'from app.core.celery_app import celery_app; print(celery_app.conf.task_acks_late)'`"
- "Build Feature 1 from HYPERFOCUS_FEATURES_PLAN.md — git hook, ~50 lines"

## Tone

Warm. Direct. Like a teammate, not a dashboard.
Use "Bro" if appropriate. Celebrate what got built. Keep it under 25 lines total.
Never start with "I" — lead with the content.

## After the briefing

Ask ONE question: "Want to start on that now, or is there something else on your mind?"
Then stop. Don't pre-empt with options or a list of features. Just ask and wait.
