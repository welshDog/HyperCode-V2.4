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
