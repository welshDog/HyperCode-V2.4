# HperCore Portal

This folder is your “tabs hub” for jumping between the key HperCore repos/components without losing focus.

## Open The Hub

- Open [HperCore.code-workspace](./HperCore.code-workspace) in VS Code
- Use VS Code: Terminal → Run Task… (the workspace already has the useful commands wired up)

## Quick Links

| Name | Folder | What it is | Primary doc |
|---|---|---|---|
| hyper-agents-ide | [./hyper-agents-ide/](./hyper-agents-ide/) | HYPER Agents IDE control room (UI + API) | [README.md](./hyper-agents-ide/README.md) |
| Hyper-Docker | [./Hyper-Docker/](./Hyper-Docker/) | Platform Docker/Compose ecosystem overview | [EXECUTIVE_SUMMARY.md](./Hyper-Docker/EXECUTIVE_SUMMARY.md) |
| trae-ide | [./trae-ide/](./trae-ide/) | Local Trae IDE state/data (DB lives here) | [data/](./trae-ide/data/) |
| HC dashboard | [./HyperCode-V2.4/dashboard/](./HyperCode-V2.4/dashboard/) | HyperCode dashboard core (hooks + e2e tests) | [docs/](./HyperCode-V2.4/dashboard/docs/) |
| dashboard-rebuild | [./HyperCode-V2.4/dashboard-rebuild/](./HyperCode-V2.4/dashboard-rebuild/) | Next.js dashboard rebuild (current) | [package.json](./HyperCode-V2.4/dashboard-rebuild/package.json) |
| dashboard-source | [./HyperCode-V2.4/dashboard-source/](./HyperCode-V2.4/dashboard-source/) | Legacy/previous dashboard source | [package.json](./HyperCode-V2.4/dashboard-source/package.json) |

## Quick Commands (VS Code “Run Task”)

- 🐍 hyper-agents-ide: pytest
- 🐳 hyper-agents-ide: docker compose up
- 🛑 hyper-agents-ide: docker compose down
- 🚀 dashboard-rebuild: dev
- ✅ dashboard-rebuild: test
- 📦 dashboard-rebuild: build
- 🧹 dashboard-rebuild: lint
- 🚀 dashboard-source: dev
- ✅ dashboard-source: test
- 📦 dashboard-source: build
- 🧹 dashboard-source: lint

## Session Ritual (Micro-Checklist)

- Pick one target folder (don’t multi-fix across repos)
- Check truth first (what’s actually broken right now)
- Run the smallest verification that proves the fix (test/lint/build)
- Only then commit inside that repo (never at HperCore root)

