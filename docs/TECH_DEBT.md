# 📌 Known Tech Debt
> For sacred rules + architecture → `CLAUDE.md`
> Completed items → `WHATS_DONE.md`

---

| Issue | Fix | Priority |
|---|---|---|
| Shop Fulfillment v2 not deployed | Deploy + run E2E (every category, buy-confirm, auto-refund, tier discounts) | 🔴 HIGH |
| Guardian P3c smoke pending | Strike-sim; verify ban only on APPROVE; tune veto delay/button delivery | 🟡 MED |
| GitHub Actions billing lock | Fix at github.com/settings/billing (human gate) | 🟡 MED |
| `/welcome` auth-gated | Decide: make public? Sponsors hit login wall from BUSINESS_PLAN | 🟡 |
| `VITE_STRIPE_PAYMENT_LINK_URL` empty | Set in `.env.local` + Vercel env vars | 🟢 LOW |
| `DISCORD_USER_ID` not set | Add to `.env` for `make calm` token awards | 🟢 LOW |
| SDK npm publish pending | `npm publish --access public` (code is v0.4.0, registry on 0.1.7) | 🟡 MED |
| Stripe TEST only | Add LIVE price IDs + LIVE webhook endpoint + pick secret by `event.livemode` | 🔴 HIGH |
| Finish Phase 10E per-agent keys (overrides removed 2026-06-12 as dead config) | Core infra EXISTS (`agent_api_keys` table + `agent_auth.py` SHA-256 middleware + rate limits) but table has 0 rows and agents never read `*_FILE`. To finish: (1) mint keys via `/api/v1/agent-keys` into the table from `secrets/agent_api_key_*.txt`, (2) agents resolve `HYPERCODE_AGENT_KEY` from env-or-file and send it as `X-Agent-Key` on agent→core calls, (3) keep shared `${API_KEY}` for orchestrator→agent inbound (or build a caller-side key map). Until then ALL auth = shared `${API_KEY}` | 🟡 MED |
