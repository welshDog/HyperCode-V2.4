# HS-053 — Pet Rarity Roll Formula

> **Extracted from:** `BROSKI_PETS_INTEGRATION_PLAN.md §Phase 1` · HyperCode-V2.4
> **What it is:** The formula that converts course progress into mint rarity odds

---

## The Core Idea

**The more you learn, the better the pet you can mint.** Learning has a tangible reward.

---

## Rarity Table (by modules completed)

| Modules Completed | Common | Uncommon | Rare | Legendary | Quantum |
|---|---|---|---|---|---|
| 0–1 | 80% | 18% | 2% | — | — |
| 2–4 | 50% | 35% | 13% | 2% | — |
| 5+ | 20% | 30% | 35% | 13% | 2% |

## Species by Rarity

```python
SPECIES_BY_RARITY = {
    "Common":    ["CatEep", "DogEep", "RabbitEep", "FishEep", "BirdEep"],
    "Uncommon":  ["FoxEep", "WolfEep", "BearEep", "TigerEep"],
    "Rare":      ["SharkEep", "OwlEep", "DragonEep"],
    "Legendary": ["SpiderEep", "VenomEep", "PhoenixEep"],
    "Quantum":   ["WelshDogEep"]  # NEVER available in Phase 1
}
```

## Implementation

```python
import random

def roll_rarity(modules_completed: int) -> str:
    if modules_completed <= 1:
        weights = {"Common": 80, "Uncommon": 18, "Rare": 2}
    elif modules_completed <= 4:
        weights = {"Common": 50, "Uncommon": 35, "Rare": 13, "Legendary": 2}
    else:
        weights = {"Common": 20, "Uncommon": 30, "Rare": 35, "Legendary": 13, "Quantum": 2}

    rarities = list(weights.keys())
    probabilities = [w / 100 for w in weights.values()]
    return random.choices(rarities, weights=probabilities, k=1)[0]

def pick_species(rarity: str) -> str:
    return random.choice(SPECIES_BY_RARITY[rarity])
```

## Provision Endpoint (V2.4)

```python
POST /api/v1/pets/provision
{
  "discord_id": "...",
  "broski_to_spend": 300,
  "modules_completed": 5  # drives rarity roll
}
# Returns: { pet_id, name, species, rarity, initial_state }
```

## The WelshDogEep Special Rule

- **Quantum rarity** — only 3 can EVER be minted across all time
- Requires: All course modules + Stage 4+ pet + 700+ commits in V2.4
- Never available in Phase 1 — it's the endgame graduation reward

---

> 🎲 Progress → better odds → better pet. The game rewards real learning.
