# HS-054 — Dev Action XP Trigger System

> **Extracted from:** `BROSKI_PETS_INTEGRATION_PLAN.md §Phase 2` · HyperCode-V2.4
> **What it is:** Every real dev action awards XP to your pet. Building IS the gameplay.

---

## XP Trigger Table

| Dev Action | XP | How to Detect |
|---|---|---|
| `git commit` | +10 XP | git post-commit hook |
| `git commit` with `fix:` prefix | +25 XP | commit message parsing |
| Pytest all green | +50 XP | CI webhook or post-test hook |
| CVE patched (Trivy 0 critical) | +100 XP | Trivy scan result |
| Course module completed | +150 XP | Supabase webhook |
| 7-day commit streak | +200 XP | streak tracker |
| Focus session completed (`make calm`) | +75 XP | Focus Mode Feature 5 |

## XP Award Endpoint

```python
POST /xp/award
{
  "discord_id": "...",
  "amount": 25,
  "reason": "fix: commit — test repaired",
  "source": "git_hook"  # or: ci_webhook, trivy_scan, course_module, focus_session
}
# Returns: { new_xp, new_level, evolved: bool, evolution_message: str | null }
```

## Evolution Stages (XP Thresholds)

| Stage | Name | XP Required | What Unlocks |
|---|---|---|---|
| 1 | Baby | 0 XP | Hatched state |
| 2 | Young | 500 XP | Personality expands |
| 3 | Grown | 2,000 XP | New power unlocked |
| 4 | Expert | 5,000 XP | NFT metadata updates on-chain |
| 5 | Legend | 15,000 XP | Rare visual upgrade + Discord badge |
| 6 | Quantum | 50,000 XP | Only achievable by serious builders |

## Evolution Logic

```python
EVOLUTION_THRESHOLDS = [0, 500, 2000, 5000, 15000, 50000]

def check_evolution(current_xp: int, new_xp: int, current_level: int) -> tuple[int, bool]:
    next_threshold = EVOLUTION_THRESHOLDS[current_level]  # next level threshold
    if new_xp >= next_threshold and current_level < 6:
        return current_level + 1, True  # evolved!
    return current_level, False
```

## Redis State Schema (DB 3)

```python
# Key: pet:{discord_id}
{
    "pet_id": "uuid",
    "name": "SpiderEep #042",
    "species": "SpiderEep",
    "rarity": "Legendary",
    "level": 3,
    "xp": 2150,
    "hunger": 65,
    "energy": 80,
    "happiness": 90,
    "evolution_history": ["2026-05-07: Baby→Young", "2026-05-14: Young→Grown"]
}
```

## Discord Notification On Evolution

```
🎉 **SpiderEep #042 evolved to Stage 3 — Grown!**
New power unlocked: Vulnerability Scanner
Your pet now helps scan your code for CVEs automatically!
Keep building — next evolution at 5,000 XP (850 to go).
```

---

> 🎮 Building = gameplay. Every commit, test, fix feeds the loop.
