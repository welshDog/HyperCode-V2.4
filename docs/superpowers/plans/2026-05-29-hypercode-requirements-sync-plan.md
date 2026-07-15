# HyperCode Requirements Sync (P0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove duplicates in `requirements.txt` and align its pinned versions with the solved set in `requirements.lock`.

**Architecture:** Treat `requirements.lock` as authoritative. Update `requirements.txt` only where it is clearly duplicated or conflicts with the lock. Do not regenerate the lock in this pass.

**Tech Stack:** Python packaging (`pip`, `pip-compile` conventions), git.

---

### Task 1: Align `requirements.txt` with `requirements.lock`

**Files:**
- Modify: `requirements.txt`
- Reference: `requirements.lock`

- [ ] **Step 1: Identify duplicates/conflicts in `requirements.txt`**
  - `Authlib` vs `authlib`
  - `aiohttp` duplicated with `>=` + `==`
  - `nltk` duplicated with `>=` + `==`
  - `urllib3` duplicated with conflicting versions

- [ ] **Step 2: Update `requirements.txt` so each package appears once**
  - Keep one canonical line per package.
  - Prefer the exact version currently present in `requirements.lock`.

- [ ] **Step 3: Spot-check the chosen versions against `requirements.lock`**
  - Example: `urllib3==2.6.3`, `aiohttp==3.13.3`, `starlette==0.52.1` (if pinned), etc.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: sync requirements.txt with lock"
```

### Task 2: Commit spec/plan docs + push

**Files:**
- Add: `docs/superpowers/specs/2026-05-29-hypercode-requirements-sync-design.md`
- Add: `docs/superpowers/plans/2026-05-29-hypercode-requirements-sync-plan.md`

- [ ] **Step 1: Commit docs**

```bash
git add docs/superpowers/specs/2026-05-29-hypercode-requirements-sync-design.md docs/superpowers/plans/2026-05-29-hypercode-requirements-sync-plan.md
git commit -m "docs: add hypercode requirements sync spec"
```

- [ ] **Step 2: git fetch + rebase + push**

```bash
git fetch
git pull --rebase
git push
```

