# HS-055 — dNFT On-Chain Portfolio Pattern

> **Extracted from:** `BROSKI_PETS_INTEGRATION_PLAN.md §Phase 4` · HyperCode-V2.4
> **What it is:** How the NFT evolves on-chain to become a verifiable developer portfolio

---

## The Core Concept

A standard NFT = static image. A **dNFT (dynamic NFT)** = living record.

Every dev action updates the NFT metadata. The NFT IS the portfolio.
**No recruiter can fake it. Every attribute is earned through real work.**

---

## NFT Metadata Schema

```json
{
  "name": "SpiderEep #042",
  "description": "Companion of Lyndz Williams — HyperCode Builder",
  "image": "ipfs://Qm.../spiderEep-stage4.png",
  "attributes": [
    {"trait_type": "Level",           "value": 4},
    {"trait_type": "XP",              "value": 5240},
    {"trait_type": "Commits",         "value": 847},
    {"trait_type": "CVEs Patched",    "value": 23},
    {"trait_type": "Course Modules",  "value": 7},
    {"trait_type": "Longest Streak",  "value": 14},
    {"trait_type": "Focus Sessions",  "value": 31},
    {"trait_type": "Special Power",   "value": "Vulnerability Scanner"}
  ]
}
```

## When Metadata Updates

| Trigger | What Updates |
|---|---|
| Stage evolution (500/2000/5000 XP) | `Level`, `XP`, `image` (new IPFS hash) |
| Every 50 commits | `Commits` counter |
| Trivy clean scan | `CVEs Patched` counter |
| Course module complete | `Course Modules` counter |
| Streak milestone (7, 14, 30 days) | `Longest Streak` |
| Focus session complete | `Focus Sessions` counter |

## On-Chain Update Flow

```
1. XP threshold hit → evolution detected in Redis
2. Build new metadata JSON with updated attributes
3. Upload new image variant to IPFS (Pinata)
4. Upload new metadata JSON to IPFS → get new CID
5. Call evolve() on ERC-721 contract with new tokenURI
6. Contract stores new IPFS hash on-chain
7. Discord notification: "Your NFT evolved! New portfolio entry added 🎉"
```

## Smart Contract Requirements

```solidity
// Required function on the contract
function evolve(uint256 tokenId, string calldata newTokenURI) external;
// Only callable by the authorised BROskiPets backend
// Emits: Evolved(tokenId, newLevel, newTokenURI)
```

## Network Decision

| Network | Status | Why |
|---|---|---|
| Sepolia testnet | ✅ Current | Free, safe for dev/testing |
| Polygon mainnet | 📝 Future | Low gas, high throughput |
| Ethereum mainnet | ❌ Not planned | Too expensive for frequent updates |

## Why This Matters

- ✅ Verifiable — on-chain, immutable history
- ✅ Composable — any app can read the NFT attributes
- ✅ Earnable — can't be bought, only built
- ✅ Portable — wallet-bound, follows the dev everywhere
- ✅ Credential — "Show me your SpiderEep" = show me your commit history

---

> 🏆 Your NFT is your CV. Built by working, not by buying.
