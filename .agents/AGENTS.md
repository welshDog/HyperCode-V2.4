# 🧠 AGENTS.md — HyperCode-V2.4

> **Dream it. Vibe it. Build it. HYPERFOCUS z0ne ♾️**

---

## 🗺️ What is this repo?

**HyperCode-V2.4** is the backend engine and wallet authority for the Hyperfocus z0ne 5-repo ecosystem.

- Runs the core AI agent swarm (48 containers healthy).
- Hosts all Supabase Edge Functions including `mint-pet-confirm`.
- Controls wallet authority for BROskiPets NFT minting on Base Sepolia.
- Acts as the source of truth for backend logic across the ecosystem.

---

## 🏗️ Ecosystem Architecture

```
HyperCode-V2.4 (backend / wallet authority)
    ↕
Hyper-Vibe-Coding-Course (frontend / earns XP + BROski$)
    ↕
BROskiPets-LLM-dNFT (reads progress → unlocks pets / Web3 minting)
    ↕
HyperAgent-SDK (shared agent interface / write once deploy anywhere)
    ↕
BROski-Obsidian-Brain (meta-layer / living knowledge vault)
```

---

## 🎯 Current Sprint (May 2026)

1. Deploy `mint-pet-confirm` Edge Function → Supabase
2. Set `VITE_MINT_VIA_RELAY=true` on Vercel → Phase 2A live
3. E2E tests: BROskiPets minting (Base Sepolia) + Stripe Checkout
4. Invite first real students to Hyper-Vibe-Coding-Course

---

## 🛠️ Skills Available (Antigravity)

| Skill | Location | Purpose |
|-------|----------|---------|
| `mint-pet-confirm` | `.agents/skills/mint-pet-confirm/` | Deploy + manage the mint confirmation edge function |

> Add new skills to `.agents/skills/<skill-name>/SKILL.md`

---

## 🔧 Tools & Connections

- **Supabase** — Edge Functions, DB, Auth, Storage
- **Base Sepolia** — Testnet for BROskiPets NFT minting
- **Vercel** — Frontend deploys for Course + BROskiPets
- **Stripe** — Payments for course access
- **GitHub** — Source control for all 5 repos
- **Docker** — 48 containers running the agent swarm
- **HyperAgent-SDK** — Shared agent interface (write once, deploy anywhere)

---

## 📜 Sacred Rules (never break these)

- Short sentences. No walls of text.
- **Bold key info** where it adds clarity.
- PowerShell first for all commands.
- Bullet points over paragraphs.
- Never debate the sacred rules.

---

## 🏆 Major Wins So Far

- 48 containers healthy ✅
- Gamification stack LIVE ✅
- Stripe LIVE ✅
- BROskiPets Web3 mint LIVE on Base Sepolia ✅
- All 78 EEP pets minted ✅
- Level 20 mapped out ✅
- Container #30 LIVE ✅

---

## 🚀 How to Boot Into Hyperfocus Mode

1. Read `CLAUDE.md` — master brain, sacred rules, architecture.
2. Read `CLAUDE_CONTEXT.md` — current context snapshot.
3. Read `WHATS_DONE.md` — latest wins and sprint state.
4. Check `.agents/skills/` — available skills for this repo.
5. Ask: **"What are we shipping first today?"**

---

*Built with ADHD superpowers by Lyndz @ Hyperfocus Zone, S.Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁿♾️*
