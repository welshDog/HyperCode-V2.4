---
name: broski-pets
description: Use for anything BROskiPets — pet minting, XP, leaderboard, bridge health, LLM pet chat, dNFT, or pets-bridge integration. Triggers on: "pets", "BROski pet", "mint", "XP", "leaderboard", "pet chat", "Cosmic Dragon".
---

# 🐾 BROski Pets Skill

## Repo
- [BROskiPets-LLM-dNFT](https://github.com/welshDog/BROskiPets-LLM-dNFT)

## Bridge Status (April 29 2026) ✅
- Health endpoint: `http://localhost:8098/health`
- pets_enabled: true
- ollama_connected: true
- redis_connected: true
- mcp_connected: true
- MCP gateway: `http://mcp-gateway:8820` (NOT 8099 — fixed April 29)

## Live Endpoints (via HyperCode core)
- GET /api/v1/pets/leaderboard
- GET /api/v1/pets/status (auth: discord_id match or superuser)
- POST /api/v1/pets/chat (auth)
- GET /api/v1/pets/powers (auth)

## Security
- IDOR hardened: status/chat/powers require logged-in user matches discord_id
- Pets proxy forwards x-api-key to broski-pets-bridge

## XP System
- Git post-commit hook awards pet XP + streak to bridge
- XP confirmed: 0→10, streak day 1 (April 29)
- Cosmic Dragon minted + leaderboard live ✅

## Phase 1 — Pending
- [ ] Mint first pet via BROski$ spend
- POST /api/v1/pets/mint (spend BROski$ → get pet)

## Phase Roadmap
- Phase 0: Bridge live ✅
- Phase 1: First mint via BROski$ 🔜
- Phase 2: LLM personality evolution
- Phase 3: On-chain dNFT
