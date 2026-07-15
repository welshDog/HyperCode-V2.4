# Contributing to HyperCode-V2.4

First off — thank you! 🧠 This is a 32-container AI agent platform and we welcome all contributors.

## 🌟 How to Contribute

1. **Fork** the repo
2. **Create a branch** — `git checkout -b feature/your-idea`
3. **Make your changes** — keep commits small and focused
4. **Test locally** — `npm run dev:frontend` (NOT `npm run dev`)
5. **Push** — `git push origin feature/your-idea`
6. **Open a PR** — describe what you changed and why

## ⚠️ Critical Rules

- Never `supabase db push` — use `apply_migration` only
- Use `docker-ce-cli` not `docker.io`
- Always `git fetch` before push — auto-commits are running
- Never commit `.env` files or secrets

## 💬 Questions?

Open a [Discussion](https://github.com/welshDog/HyperCode-V2.4/discussions) or check `CLAUDE.md` for full context.

*HyperFocus Zone — Stop apologising for your brain. Start building.* ✨
