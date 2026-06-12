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
| Phase 10E rollout (3 of 14 identities ACTIVE 2026-06-12) | LIVE: crew-orchestrator (task events), nemoclaw-agent (health/scan events), broski-pets-bridge (pets/brain-feed events) all publish to `POST /api/v1/events` as THEMSELVES via `X-Agent-Key` (env-or-file pattern, fail-open). 14 keys minted (`scripts/mint_agent_keys.py` — ⚠️ re-running ROTATES). REMAINING: the 11 specialist/util agents get the same pattern when they gain core-bound calls; healer deserves its own pass (MAPE-K heal events would be ops gold). Orchestrator→agent inbound stays shared `${API_KEY}` by design | 🟢 LOW |
