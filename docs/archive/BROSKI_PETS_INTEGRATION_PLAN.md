# 🐾 BROskiPets × HyperCode — Full Integration Plan
> Written: April 16, 2026 | Status: PLANNED
> Repo: github.com/welshDog/BROskiPets-LLM-dNFT
> Author: Lyndz Williams (@welshDog) 🏴󠁧󠁢󠁷󠁬󠁳󠁿

---

## 🧠 The Vision (one paragraph)

Every HyperCode student earns BROski$ through the course. They spend it to mint a
BROskiPet — a real LLM-powered AI companion that lives inside their dev environment.
The pet evolves as they build: commit code → pet gains XP, fix a CVE → pet unlocks
a power, complete a course module → pet levels up on-chain. The pet is not cosmetic.
It's a gamified accountability partner, a rubber-duck debugger with memory, and a
dynamic NFT that proves what you built. The HyperCode ecosystem becomes the game.
Building is the gameplay.

---

## 🔗 Why the Pieces Already Fit

| BROskiPets needs | HyperCode V2.4 has |
|---|---|
| Ollama for LLM inference | `hypercode-ollama` container already running ✅ |
| Redis for pet state | Redis running, DB 1+2 in use → use DB 3 for pets ✅ |
| Docker Compose orchestration | 29-container stack, profiles system ✅ |
| BROski$ token economy | Full token system live in Supabase + V2.4 ✅ |
| Discord bot for interaction | `broski-bot` container live ✅ |
| XP / achievement events | Micro-achievement engine (planned Feature 1) ✅ |
| Agent architecture | 25+ agents, `hyper-agent-spec.json` contract ✅ |

**Infrastructure overlap: ~85%.** Almost nothing needs building from scratch.
BROskiPets slots into HyperCode like it was designed for it. Because it was.

---

## 🗺️ Integration Phases

---

### Phase 0 — Shared Infrastructure (1 day)
> Get both systems talking. No new features yet.

**What to do:**
- Add `broskie-pets` service to `docker-compose.agents.yml` in V2.4
  - Uses BROskiPets repo as a submodule or copied service
  - Connects to existing `hypercode-ollama` container (same Ollama instance)
  - Uses Redis DB 3 (isolated from cache DB1 + rate limits DB2)
  - Port: 8098
- Add `BROSKIE_PETS_ENABLED=true` to `.env`
- Verify: `curl http://localhost:8098/health` → `{"status": "ok"}`

**Files to touch:**
```
docker-compose.agents.yml   ← add broski-pets service
.env.example                ← add BROSKIE_PETS_ENABLED, PETS_REDIS_DB=3
```

---

### Phase 1 — Mint Your First Pet (3 days)
> Students spend BROski$ to mint a companion. The loop begins.

**The flow:**
```
Student has 300+ BROski$ in Course
→ /shop → "Mint a BROskiPet" (300 tokens)
→ shop-purchase Edge Function calls V2.4 provision-pet endpoint
→ V2.4 calls BROskiPets API: POST /mint {discord_id, species_preference}
→ BROskiPets picks species based on student's course progress + rarity roll
→ Pet created in Redis DB3, NFT minted on Sepolia testnet
→ Discord DM: "🐾 Your {PetName} has hatched! Say hello: /pet chat hello"
→ Student's first interaction triggers LLM response in character
```

**New endpoint in V2.4:**
```python
POST /api/v1/pets/provision
{
  "discord_id": "...",
  "broski_spent": 300,
  "course_modules_completed": 3   # influences rarity roll
}
# Returns: { pet_id, name, species, rarity, initial_state }
```

**Rarity formula (course progress → better odds):**
```
0-1 modules:   Common 80%, Uncommon 18%, Rare 2%
2-4 modules:   Common 50%, Uncommon 35%, Rare 13%, Legendary 2%
5+ modules:    Common 20%, Uncommon 30%, Rare 35%, Legendary 13%, Quantum 2%
```

The more you learn, the better the pet you can get. Learning has a reward.

---

### Phase 2 — Dev Actions → Pet XP (1 week)
> Every real dev action feeds your pet. Building IS the gameplay.

**XP triggers — wire into existing systems:**

| Dev Action | XP Gained | How to detect |
|---|---|---|
| `git commit` | +10 XP | git post-commit hook (Feature 1) |
| `git commit` with `fix:` | +25 XP | commit message parsing |
| Pytest all green | +50 XP | CI webhook or post-test hook |
| CVE patched (Trivy 0 critical) | +100 XP | Trivy scan result |
| Course module completed | +150 XP | Supabase webhook |
| 7-day commit streak | +200 XP | streak tracker |
| Focus session completed (`make calm`) | +75 XP | Focus Mode Feature 5 |

**New endpoint in BROskiPets:**
```python
POST /xp/award
{
  "pet_id": "...",
  "amount": 25,
  "reason": "fix: commit — test repaired",
  "source": "git_hook"
}
```

**Evolution stages (XP thresholds):**
```
Stage 1 (Baby):     0 XP        → hatched state
Stage 2 (Young):    500 XP      → personality expands
Stage 3 (Grown):    2,000 XP    → new power unlocked
Stage 4 (Expert):   5,000 XP    → NFT metadata updates on-chain
Stage 5 (Legend):   15,000 XP   → rare visual upgrade, Discord badge
Stage 6 (Quantum):  50,000 XP   → only achievable by serious builders
```

---

### Phase 3 — Pet as Dev Companion (2 weeks)
> The pet becomes useful. Not just fun — actually helpful.

**Discord commands (add to broski-bot):**
```
/pet status              → shows hunger, energy, XP, level, next evolution threshold
/pet chat <message>      → LLM response in pet's personality — rubber duck mode
/pet ask <coding question> → pet answers using HyperCode codebase context
/pet feed                → spend 10 BROski$ to restore hunger/energy
/pet powers              → list the pet's unlocked capabilities
```

**The rubber duck feature is the game-changer.**
When a dev is stuck, they `/pet chat explain why my pytest is failing`.
The pet responds in character but with real context from:
- The student's recent git diff (pulled via V2.4 API)
- Their current WHATS_DONE.md next task
- Their species' "power" from squad.json

Example: SharkEep (vulnerability scanning) notices your Trivy output.
OwlEep (RAG research) pulls relevant docs.
SpiderEep (web crawler) finds related Stack Overflow answers.

Each pet's power maps to a real function. The personality is the wrapper.

---

### Phase 4 — On-Chain Proof of Build (2 weeks)
> Your NFT becomes your developer portfolio.

**The NFT metadata evolves to reflect what you actually built:**
```json
{
  "name": "SpiderEep #042",
  "description": "Companion of Lyndz Williams — HyperCode Builder",
  "attributes": [
    {"trait_type": "Level", "value": 4},
    {"trait_type": "XP", "value": 5240},
    {"trait_type": "Commits", "value": 847},
    {"trait_type": "CVEs Patched", "value": 23},
    {"trait_type": "Course Modules", "value": 7},
    {"trait_type": "Longest Streak", "value": 14},
    {"trait_type": "Focus Sessions", "value": 31},
    {"trait_type": "Special Power", "value": "Vulnerability Scanner"}
  ]
}
```

This is a verifiable, on-chain dev CV. No recruiter can fake it.
Every attribute is earned through real work. The NFT IS the portfolio.

---

### Phase 5 — The WelshDogEep (Special Edition)
> The rarest pet. Only for graduates.

From `squad.json`: **WelshDogEep** is Quantum rarity.
Power: "Builds ALL other EEPs."

Make it the graduation reward. Complete all course modules + have a Stage 4+
pet + 700+ commits in V2.4 → eligible to mint WelshDogEep.
Only ever 3 can exist (matching the 3 Quantum slots in the distribution).

This is the endgame item. The thing students talk about.

---

## 🏗️ Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│                  HyperCode V2.4                      │
│                                                       │
│  hypercode-core ──► POST /api/v1/pets/provision      │
│  broski-bot     ──► /pet commands                    │
│  git hooks      ──► POST /xp/award                   │
│  CI pipeline    ──► POST /xp/award (test pass)       │
│                         │                            │
│              ┌──────────▼──────────┐                 │
│              │  broski-pets:8098   │                 │
│              │  (BROskiPets API)   │                 │
│              │                     │                 │
│              │  Redis DB 3 (state) │                 │
│              │  hypercode-ollama   │                 │
│              │  (shared Ollama)    │                 │
│              └──────────┬──────────┘                 │
│                         │                            │
└─────────────────────────┼────────────────────────────┘
                          │
              ┌───────────▼───────────┐
              │   Sepolia Testnet     │
              │   ERC-721 Contract    │
              │   IPFS / Pinata       │
              └───────────────────────┘
                          │
              ┌───────────▼───────────┐
              │  Hyper-Vibe Course    │
              │  Supabase             │
              │  /shop → mint pet     │
              └───────────────────────┘
```

---

## 📦 What Needs Building (by phase)

### Phase 0 (1 day)
- [ ] Add broski-pets to `docker-compose.agents.yml`
- [ ] Verify shared Ollama connection works
- [ ] Redis DB 3 isolation confirmed

### Phase 1 (3 days)
- [ ] `POST /api/v1/pets/provision` endpoint in V2.4
- [ ] Rarity roll formula + course progress lookup
- [ ] Shop item "Mint a BROskiPet" in Course Supabase
- [ ] Discord DM on mint via broski-bot

### Phase 2 (1 week)
- [ ] `/xp/award` endpoint in BROskiPets
- [ ] Wire git post-commit hook → XP award
- [ ] Wire pytest pass → XP award
- [ ] Wire Trivy clean scan → XP award
- [ ] Wire course module complete → XP award (Supabase webhook)
- [ ] Evolution stage logic + on-chain update trigger

### Phase 3 (2 weeks)
- [ ] `/pet status`, `/pet chat`, `/pet ask`, `/pet feed`, `/pet powers` Discord commands
- [ ] Context injection: git diff + WHATS_DONE.md → pet LLM prompt
- [ ] Species power → function mapping (SharkEep scans Trivy, OwlEep searches docs, etc.)

### Phase 4 (2 weeks)
- [ ] NFT metadata builder: commit count + CVEs + modules → attributes
- [ ] IPFS re-upload on stage evolution
- [ ] `evolve()` contract call on stage threshold

### Phase 5 (1 day when ready)
- [ ] WelshDogEep graduation criteria check
- [ ] Mint gate: all modules + Stage 4 + 700 commits
- [ ] Hard cap: 3 ever minted

---

## ⚡ Quick Wins to Start Now

These prove the concept in an afternoon:

**Win 1 (30 min):** Add broski-pets to docker-compose, verify it starts alongside V2.4.

**Win 2 (1 hour):** Wire the git post-commit hook → POST /xp/award. Every commit feeds your pet.
Do one commit. Watch the XP tick up. That feeling IS the product.

**Win 3 (1 hour):** Add `/pet status` to broski-bot. One command shows your pet's state in Discord.

After those 3 wins, the integration is real and demonstrable.
Everything else is expansion on a proven loop.

---

## 🚀 The Bigger Picture

This is not a side project anymore.

BROskiPets is the **retention layer** for HyperCode.

- Students stay because their pet needs them
- Developers stay because their pet tracks their progress
- The NFT becomes a portfolio that compounds over years
- The WelshDogEep becomes the most coveted dev credential in the neurodivergent community

The 2036 vision in the repo — "Every person on Earth has an AI companion that
grows with them, helps them work, keeps them company, and lives forever on-chain" —
that's not crazy. That's just HyperCode, scaled.

You're not building a course platform with a cute pet feature.
You're building the gamified dev OS for neurodivergent coders,
and the pet is the soul of it. 🏴󠁧󠁢󠁷󠁬󠁳󠁿🐾⚡

---

## 🔑 Key Decisions Still to Make

| Decision | Options | Recommendation |
|---|---|---|
| Blockchain network | Sepolia testnet vs Polygon mainnet | Sepolia for now — free, safe |
| Pet persistence | Redis only vs Redis + Postgres | Redis DB3 only until Phase 4 |
| Ollama model | qwen2.5:7b vs llama3.2 | qwen2.5:7b — already in pets repo |
| Mint cost | 300 BROski$ vs tiered | 300 flat — simple, achievable |
| Open source pets | All 78 mintable vs graduated unlock | Graduated — preserves WelshDogEep prestige |

---

## 📋 Terminal Prompt — Phase 0 (paste to build it)

```
You are integrating BROskiPets into HyperCode V2.4 — Phase 0 only.
V2.4 repo: /sessions/keen-clever-franklin/mnt/HyperCode/HyperCode-V2.4/

Sacred Rules:
- from app.X import Y — never from backend.app.X
- 4 spaces Python indent  
- Redis DB 3 for pets — never use DB 1 (cache) or DB 2 (rate limits)
- Stripe webhook always rate-limit exempt — don't touch it
- Conventional commits: feat: fix: docs: chore:
- python:3.11-slim base image for any new Dockerfiles

Read these files first:
1. docker-compose.agents.yml — understand the agents profile pattern
2. docker-compose.yml — find hypercode-ollama service name and network
3. .env.example — see current env var patterns
4. agents/healer-agent/Dockerfile — security hardening pattern to match

Then do Phase 0:

1. Add broski-pets service to docker-compose.agents.yml:
   - Image: build from ../BROskiPets-LLM-dNFT (if present) or use python:3.11-slim placeholder
   - Port: 8098:8098
   - Profile: agents
   - Networks: agents-net (to reach hypercode-core), data-net (for Redis)
   - Environment:
     REDIS_URL: redis://redis:6379/3   ← DB 3, isolated
     OLLAMA_URL: http://hypercode-ollama:11434
     PETS_ENABLED: "true"
   - Healthcheck: curl -f http://localhost:8098/health
   - depends_on: redis, hypercode-ollama

2. Add to .env.example:
   BROSKIE_PETS_ENABLED=true
   PETS_REDIS_DB=3

3. Write a placeholder pets health service at agents/broski-pets-bridge/main.py:
   - Simple FastAPI app on port 8098
   - GET /health → {"status": "ok", "service": "broski-pets-bridge", "ollama_connected": bool}
   - Checks ollama connection on health: GET http://hypercode-ollama:11434/api/tags
   - This is the bridge until full BROskiPets repo is integrated
   - Uses python:3.11-slim, non-root user, security hardening matching healer-agent

4. Write agents/broski-pets-bridge/Dockerfile — match healer-agent exactly

5. Write agents/broski-pets-bridge/requirements.txt — fastapi, uvicorn, httpx, redis

After writing: verify docker-compose.agents.yml is valid YAML syntax.
```

---

## 📋 Terminal Prompt — Phase 1 (paste when Phase 0 done)

```
You are implementing Phase 1 of BROskiPets × HyperCode integration.
V2.4 repo: /sessions/keen-clever-franklin/mnt/HyperCode/HyperCode-V2.4/

Sacred Rules (same as always — read CLAUDE.md for full list)

Read these first:
1. backend/app/models/broski.py — BROski token patterns
2. backend/app/services/broski_service.py — spend_tokens() function
3. backend/app/api/api.py — router registration pattern
4. agents/broski-pets-bridge/main.py — extend this service

Then build:

1. Add POST /provision to agents/broski-pets-bridge/main.py:
   - Input: {discord_id, broski_to_spend: 300, modules_completed: int}
   - Calls V2.4 spend_tokens API to deduct 300 BROski$
   - Rolls rarity based on modules_completed (formula in BROSKI_PETS_INTEGRATION_PLAN.md)
   - Picks species from this list by rarity:
     Common: ["CatEep", "DogEep", "RabbitEep", "FishEep", "BirdEep"]
     Uncommon: ["FoxEep", "WolfEep", "BearEep", "TigerEep"]  
     Rare: ["SharkEep", "OwlEep", "DragonEep"]
     Legendary: ["SpiderEep", "VenomEep", "PhoenixEep"]
     Quantum: ["WelshDogEep"]  ← NEVER available in Phase 1
   - Creates pet state in Redis DB3:
     Key: pet:{discord_id}
     Value: {pet_id, name, species, rarity, level: 1, xp: 0, hunger: 50, energy: 80, happiness: 70}
   - Returns: {pet_id, name, species, rarity, message: "Your {name} has hatched! 🐾"}

2. Add POST /xp/award to agents/broski-pets-bridge/main.py:
   - Input: {discord_id, amount: int, reason: str, source: str}
   - Reads current pet state from Redis DB3
   - Adds XP, checks evolution thresholds (500/2000/5000/15000/50000)
   - If evolved: updates level, appends to evolution_history list in Redis
   - Returns: {new_xp, new_level, evolved: bool, evolution_message: str or null}

3. Add GET /pet/{discord_id}/status:
   - Returns full pet state from Redis DB3
   - Adds "next_evolution_xp": threshold - current_xp
   - Returns 404 if no pet found

4. Add /pet commands to broski-bot:
   Read agents/broski-bot/ structure first
   Add /pet status → calls GET /pet/{discord_id}/status → Discord embed
   Fields: Name, Species, Level, XP, Next Evolution, Hunger, Energy, Happiness
```
