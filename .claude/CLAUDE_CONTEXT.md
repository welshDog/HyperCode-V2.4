# 🤖 HyperAgent-SDK — Claude Context Handoff
> Read this first if you're a new Claude session picking up this project.

---

## Who You're Talking To
- **Lyndz** (GitHub: @welshDog, npm: @w3lshdog) — indie dev, South Wales
- Autistic + dyslexic + ADHD — be direct, chunked, no waffle
- Windows primary (PowerShell), also runs Linux + Raspberry Pi + Docker
- Building the **Hyperfocus Zone** — a suite of interconnected open-source tools

---

## The Ecosystem (3 repos, 1 mission)

```
Hyper-Vibe-Coding-Course  ──── manifest.json ────▶  HyperCode V2.4
   (Supabase/Vercel)          (hyper-agent-spec)     (Docker, 26 containers)
         |                           |
         └──────── HyperAgent-SDK ───┘
                  (the passport layer)
                  npm: @w3lshdog/hyper-agent
```

- **Hyper-Vibe-Coding-Course** — gamified dev school (XP, BROski$ tokens, shop, 22 Supabase migrations, all green)
- **HyperCode-V2.4** — production platform (FastAPI, Docker, Grafana, MCP gateway ports 3100–3999)
- **HyperAgent-SDK** — the glue. Shared agent spec + CLI validator + templates. **This is what you're working on.**

---

## HyperAgent-SDK — Current State

**Repo:** https://github.com/welshDog/HyperAgent-SDK  
**npm:** @w3lshdog/hyper-agent@0.1.0-alpha.1 (PUBLISHED ✅)  
**Commits:** ~6 on main

### File structure (what's there):
```
HyperAgent-SDK/
├── cli/validate.js          ✅ Real AJV validator, coloured output, exit codes
├── templates/
│   ├── python-starter/      ✅ manifest.json + main.py + requirements.txt
│   └── node-starter/        ✅ manifest.json + index.js + package.json
├── docs/
│   ├── MASTER_PLAN.md       ✅ 6-phase ecosystem integration roadmap
│   └── BROSKU_TOKEN_STRATEGY.md ✅ Token economy deep-dive
├── README.md                ✅ Updated — pre-release warning, real tool examples
├── hyper-agent-spec.json    ✅ JSON Schema with if/then port enforcement
├── package.json             ✅ @w3lshdog/hyper-agent, 0.1.0-alpha.1, bin entry
├── CONTRIBUTING.md          ✅ ADHD-friendly, 3-step flow
├── LICENSE                  ✅ MIT 2026 welshDog
└── node_modules/            (local only, not committed)
```

---

## 🚨 CURRENT BUG — Not Fixed Yet

**`npm test` fails with:**
```
Error: strict mode: unknown keyword: "errorMessage"
```

**Why:** `hyper-agent-spec.json` has `"errorMessage"` in the `then` block of the `if/then` conditional. This keyword requires the `ajv-errors` plugin which isn't installed. AJV 8 strict mode rejects unknown keywords.

**The fix** — remove `errorMessage` from `hyper-agent-spec.json`. The `then` block currently looks like:
```json
"then": {
  "required": ["port"],
  "errorMessage": "port is required when mcp_compatible is true..."
}
```

Change it to just:
```json
"then": {
  "required": ["port"]
}
```

**PowerShell one-liner:**
```powershell
(Get-Content hyper-agent-spec.json) -replace '^\s*"errorMessage":.*$', '' | Where-Object { $_ -ne '' } | Set-Content hyper-agent-spec.json
```

**Then verify + commit + republish:**
```powershell
npm test
git add hyper-agent-spec.json
git commit -m "fix: remove errorMessage keyword — AJV strict mode rejects it without ajv-errors plugin"
git push
npm version patch --no-git-tag-version
npm publish --access public --tag alpha
```

Expected `npm test` output after fix:
```
✓ my-python-agent v0.1.0 — 1 tool(s), python, mcp: ✗
✓ my-node-agent v0.1.0 — 1 tool(s), node, mcp: ✗

Results: 2 passed, 0 failed
All templates valid ✅
```

---

## What's Done (Tonight's Session)

| Task | Status |
|---|---|
| SDK scaffolded with cli/ + templates/ | ✅ |
| validate.js — real AJV validator | ✅ |
| hyper-agent-spec.json — full JSON Schema | ✅ |
| if/then port enforcement for mcp_compatible | ✅ |
| Templates — python + node with real input_schema | ✅ |
| README updated — pre-release warning + real examples | ✅ |
| LICENSE (MIT) + CONTRIBUTING.md | ✅ |
| docs/ — MASTER_PLAN + TOKEN_STRATEGY moved here | ✅ |
| extra/ folder cleaned up | ✅ |
| npm scope fixed (@welshdog → @w3lshdog) | ✅ |
| ajv-formats added to dependencies | ✅ |
| Published to npm as 0.1.0-alpha.1 | ✅ |
| npm test passing | ❌ errorMessage bug |

---

## What's Next (Priority Order)

1. **Fix the errorMessage bug** (above) — unblocks green tests
2. **Re-publish** as 0.1.0-alpha.2 after fix
3. **Update README** — change `npx hyper-agent` → `npx @w3lshdog/hyper-agent`
4. **GitHub Actions CI** — auto-run `npm test` on every push/PR
5. **Phase 0 of MASTER_PLAN** — Alembic migration adding `discord_id` to V2.4 users table (this unlocks the entire 6-phase integration)
6. **npm run graduate** — Phase 4 flagship feature (8-step agent graduation script)

---

## Key Technical Decisions Made

- **No `ajv-errors` plugin** — drop `errorMessage`, AJV's built-in errors are sufficient
- **Port convention:** 3100–3199 writing, 3200–3299 code, 3300–3399 data, 3400–3499 discord, 3500–3599 automation
- **`mcp_compatible: true` requires `port`** — enforced via JSON Schema `if/then`
- **`input_schema` requires `type` + `properties`** — prevents empty `{}` tools passing validation
- **Windows PowerShell first** — all scripts must work on PowerShell, WSL2 secondary
- **Conventional commits** — `feat:`, `fix:`, `docs:`, `chore:`
- **No merging repo databases** — Supabase (Course) and Postgres (V2.4) stay separate forever

---

## Tone / Working Style

- Call Lyndz "Bro" — that's how we roll
- Short. Direct. No waffle.
- Use ✅ ⚠️ ❌ 🔧 🚀 for status signals
- PowerShell copy-paste commands always
- Honest feedback — don't sugarcoat issues
- ADHD-friendly: chunked output, quick wins first, one action per step
