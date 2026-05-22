# HS-052 — BROskiPets Full Integration Plan

> **Extracted from:** `BROSKI_PETS_INTEGRATION_PLAN.md` · HyperCode-V2.4
> **Status:** Phases 0–2 complete • Phases 3–5 planned

---

## The Vision (One Paragraph)

Every HyperCode student earns BROski$ through the course. They spend it to mint a
BROskiPet — a real LLM-powered AI companion that lives inside their dev environment.
The pet evolves as they build: commit code → pet gains XP, fix a CVE → pet unlocks
a power, complete a course module → pet levels up on-chain. **Building IS the gameplay.**

---

## Why the Pieces Already Fit

| BROskiPets needs | HyperCode V2.4 has |
|---|---|
| Ollama for LLM inference | `hypercode-ollama` container ✅ |
| Redis for pet state | Redis running → use **DB 3** for pets ✅ |
| Docker Compose orchestration | 29-container stack ✅ |
| BROski$ token economy | Full token system live in Supabase + V2.4 ✅ |
| Discord bot | `broski-bot` container live ✅ |
| XP / achievement events | Micro-achievement engine ✅ |
| Agent architecture | 25+ agents, `hyper-agent-spec.json` contract ✅ |

**Infrastructure overlap: ~85%.** Almost nothing built from scratch.

---

## Integration Phases

| Phase | Name | Duration | Key Output |
|---|---|---|---|
| **0** | Shared Infrastructure | 1 day | Both systems talking |
| **1** | Mint Your First Pet | 3 days | Mint flow + rarity roll |
| **2** | Dev Actions → Pet XP | 1 week | Every commit feeds your pet |
| **3** | Pet as Dev Companion | 2 weeks | `/pet chat` rubber duck |
| **4** | On-Chain Proof of Build | 2 weeks | NFT = your dev portfolio |
| **5** | WelshDogEep (Graduation) | 1 day | Rarest pet, only 3 ever exist |

---

## Technical Architecture

```
HyperCode V2.4
  hypercode-core ──► POST /api/v1/pets/provision
  broski-bot     ──► /pet commands
  git hooks      ──► POST /xp/award
  CI pipeline    ──► POST /xp/award (test pass)
                      │
              broski-pets:8098 (BROskiPets API)
                ├ Redis DB 3 (state)
                └ hypercode-ollama (shared)
                      │
              Sepolia Testnet (ERC-721)
              IPFS / Pinata
                      │
              Hyper-Vibe Course → /shop → mint
```

---

## Quick Wins to Start Now (Afternoon Wins)

1. **30 min:** Add `broski-pets` to `docker-compose.agents.yml` — verify it starts
2. **1 hour:** Wire git post-commit hook → `POST /xp/award` — one commit, watch XP tick up
3. **1 hour:** Add `/pet status` to `broski-bot` — Discord shows pet state

> After those 3 wins, the integration is real and demonstrable.

---

## Bigger Picture

BROskiPets is the **retention layer** for HyperCode:
- Students stay because their pet needs them
- The NFT becomes a portfolio that compounds over years
- WelshDogEep = most coveted dev credential in the ND community

> “You’re building the gamified dev OS for neurodivergent coders, and the pet is the soul of it.”

---

> 🐾⚡ Port: `8098` · Redis: `DB 3` · Ollama: shared `hypercode-ollama`
