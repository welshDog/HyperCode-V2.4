# 💳 Stripe Integration — Full Audit Report

**Date:** 2026-05-20 · **Auditor:** Claude (Opus 4.7) + Lyndz
**Repos covered:** `Hyper-Vibe-Coding-Course` · `HyperCode-V2.4`
**Status of integration:** ✅ LIVE (Stripe live mode, webhook secret rotated May 5) · 🟡 has surfaced risks
**Status of automated E2E coverage:** ❌ **NONE** — the `4242 4242 4242 4242` test is still a human gate

---

## 🟢 TL;DR — Read This First

- **Three independent payment paths exist** in the Course frontend. They diverged over time and now use different mechanisms — easy to break one without noticing.
- **Two webhook handlers are both implemented** (V2.4 FastAPI + Supabase Edge Function). Whether Stripe is configured to fan out to both is a **deploy-config question that must be verified in the Stripe Dashboard** — if both receive events, users get **double tokens / double enrollments** on every purchase. This is the highest-impact unknown in this audit.
- **Code compiles cleanly** (build green) and the security model is sound (webhook signature verified; PaymentSuccess never self-grants).
- **Five Pricing-page env vars are NOT documented in `.env.example`** — silent breakage risk on a fresh Vercel deploy.
- **No automated test** exists for any Stripe code path in either repo's E2E suite. The `4242` card test is documented manually only.

---

## 🗺️ The Three Payment Paths

| # | Surface | Mechanism | Backend hop | Stripe object |
|---|---|---|---|---|
| **A** | `TokensPage.tsx` (token packs £5/£15/£35) | `createCheckoutSession(slug, userId)` → V2.4 → returns hosted URL | **V2.4** `/api/stripe/checkout` | one-time `payment` Session |
| **B** | `Pricing.tsx` (course tiers £29/£79/£149 + monthly variants) | Direct `window.location.href = VITE_STRIPE_*_URL` | **NONE** (Stripe Payment Link) | Pre-baked Stripe Payment Link |
| **C** | `CourseDetail` → `ShipFullStackThing` etc. (individual course purchase) | `createCourseCheckoutSession({id,title,price_pence}, userId)` → V2.4 | **V2.4** `/api/stripe/checkout` (with `price_id="course_purchase"`) | one-time `payment` Session w/ inline `price_data` |

> Path **B bypasses V2.4 entirely** — it relies on the Stripe Payment Link being correctly configured in the Stripe Dashboard with success_url back to the app. The webhook is the only thing that connects the payment to the user.

---

## 🔗 End-to-End Chain (Path A — Token Pack purchase)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. TokensPage.tsx                                                            │
│    Buy "Builder Pack £15" button → handleBuyPack('builder')                  │
│    → createCheckoutSession('builder', user.id)                               │
└────────────────────────────────────────┬────────────────────────────────────┘
                                         │ POST  Content-Type: application/json
                                         │ body: { price_id: 'builder',
                                         │         user_id: 'uuid…',
                                         │         success_url: window.origin+'/payment-success',
                                         │         cancel_url:  window.origin+'/pricing' }
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. V2.4 FastAPI  POST /api/stripe/checkout   (rate-limited 10/min)           │
│    backend/app/routes/stripe.py                                              │
│    backend/app/services/stripe_service.py                                    │
│                                                                              │
│    PRICE_MAP['builder']  → os.getenv('STRIPE_PRICE_BUILDER') = price_xxx     │
│    CHECKOUT_MODE['builder']='payment'  TOKEN_GRANT['builder']=800            │
│    TIER_MAP['builder']='pro'                                                 │
│                                                                              │
│    stripe.checkout.Session.create(                                           │
│      line_items=[{price: price_xxx, quantity:1}], mode='payment',            │
│      metadata={user_id, price_key:'builder'},                                │
│      success_url=...+'session_id={CHECKOUT_SESSION_ID}', cancel_url=...)     │
│                                                                              │
│    → returns { checkout_url: 'https://checkout.stripe.com/c/pay/cs_…',       │
│               session_id: 'cs_test_xxx' }                                    │
└────────────────────────────────────────┬────────────────────────────────────┘
                                         │ window.location.assign(checkout_url)
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. Stripe-hosted Checkout page (checkout.stripe.com)                         │
│    User enters card 4242 4242 4242 4242, any future date, any CVC, any ZIP   │
│    Payment confirms                                                          │
└─────────┬───────────────────────────────────────────────┬──────────────────┘
          │  Stripe fires webhook(s):                     │  Stripe redirects user
          ▼                                               ▼
┌──────────────────────────────────┐    ┌──────────────────────────────────────┐
│ 4a. V2.4 POST /api/stripe/webhook │    │ 5. Course /payment-success           │
│     RATE-LIMIT EXEMPT (sacred #4) │    │    ?session_id=cs_xxx                 │
│     verifies Stripe-Signature     │    │                                      │
│     handle_webhook_event(event)   │    │    PaymentSuccess.tsx polls          │
│                                   │    │      supabase.from('enrollments')    │
│     IF event.type=                │    │      .eq(user_id).limit(1)            │
│       'checkout.session.completed'│    │    15× over 15s                       │
│     THEN:                         │    │                                      │
│       _save_payment(payments)     │    │    → ✓ enrolled → celebration         │
│       _update_user_subscription   │    │    → ✗ timeout → support card         │
│         (users.subscription_tier) │    │                                      │
│       _award_tokens               │    │    DISPLAY-ONLY — never self-grants  │
│         (token_transactions       │    │    Webhook is the sole truth.        │
│          + users.broski_tokens)   │    └──────────────────────────────────────┘
│                                   │
└──────────────────────────────────┘
          │
          ▼ ⚠️ ALSO (if configured in Stripe Dashboard):
┌──────────────────────────────────────────────────────────────────────────────┐
│ 4b. Supabase Edge Function: stripe-webhook                                   │
│     supabase/functions/stripe-webhook/index.ts                               │
│     verifies Stripe-Signature                                                │
│                                                                              │
│     PRICE_TO_TIER[priceId]  → { tier, tokens, modules }                      │
│     (5 hard-coded Stripe price IDs in the source!)                           │
│                                                                              │
│     awardTokensAndUnlock():                                                  │
│       UPDATE users SET broski_tokens = current + tokens,                     │
│                        subscription_tier = tier,                             │
│                        subscription_status = 'active'                        │
│       INSERT token_transactions  ← NO unique constraint here!                 │
│       enrollUser  (UPSERT into enrollments — onConflict user_id,course_id)    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Path B (Pricing tiers) is shorter
- Frontend reads `STRIPE_LINKS[tier.stripeKey]` from `import.meta.env.VITE_STRIPE_*_URL`.
- `window.location.href = url` — straight to Stripe-hosted Payment Link.
- **No V2.4 hop.** Stripe records `client_reference_id` and fires the webhook(s) when paid.
- Webhook handles it identically to Path A (5).

### Path C (Course purchase) uses inline price_data
- `createCourseCheckoutSession()` posts `price_id: 'course_purchase'` + `course_id`, `course_title`, `price_pence`.
- V2.4 builds the session with `line_items[0].price_data = { currency:'gbp', unit_amount: pence, product_data:{name} }` and sets `client_reference_id = course_id`.
- No pre-created Stripe Price ID needed (dynamic per-course pricing).
- Webhook reads `client_reference_id` to enroll the buyer in that specific course (no token grant — `enrollVerifiedBuyer` path).

---

## ⚙️ Configuration Surface

### Course frontend env vars

| Var | Required? | Used by | In `.env.example`? |
|---|---|---|---|
| `VITE_SUPABASE_URL` | ✅ yes | everything | ✅ |
| `VITE_SUPABASE_ANON_KEY` | ✅ yes | everything | ✅ |
| `VITE_HYPERCODE_API_URL` | ✅ yes (prod) | Path A, Path C | ✅ |
| `VITE_STRIPE_PAYMENT_LINK_URL` | optional | legacy `buildStripePaymentLinkUrl` helper (not used by current pages) | ✅ |
| `VITE_STRIPE_STARTER_URL` | ✅ yes for Path B | `Pricing.tsx` | ❌ **MISSING** |
| `VITE_STRIPE_BUILDER_URL` | ✅ yes for Path B | `Pricing.tsx` | ❌ **MISSING** |
| `VITE_STRIPE_HYPER_LEGEND_URL` | ✅ yes for Path B | `Pricing.tsx` | ❌ **MISSING** |
| `VITE_STRIPE_BUILDER_MONTHLY_URL` | ✅ yes for Path B | `Pricing.tsx` | ❌ **MISSING** |
| `VITE_STRIPE_HYPER_LEGEND_MONTHLY_URL` | ✅ yes for Path B | `Pricing.tsx` | ❌ **MISSING** |

> A fresh Vercel deploy with only the documented env vars will have **Path B silently broken** (all Pricing buttons show "Checkout temporarily unavailable" toast). The code does fail safely — no free unlocks — but the buyer can't pay.

### V2.4 backend env vars (mapped in `stripe_service.py` `PRICE_MAP`)

```
STRIPE_SECRET_KEY          # sk_live_… (server-side only, never frontend)
STRIPE_WEBHOOK_SECRET      # whsec_… (rotated 2026-05-05)
STRIPE_PRICE_STARTER       # price_xxx for token pack £5
STRIPE_PRICE_BUILDER       # price_xxx for token pack £15
STRIPE_PRICE_HYPER         # price_xxx for token pack £35
STRIPE_PRICE_PRO_MONTHLY   # price_xxx subscription
STRIPE_PRICE_PRO_YEARLY    # price_xxx subscription
STRIPE_PRICE_HYPER_MONTHLY # price_xxx subscription
STRIPE_PRICE_HYPER_YEARLY  # price_xxx subscription
```

### Supabase Edge Function env vars
```
STRIPE_SECRET_KEY          # also needed here for webhook signature verification
STRIPE_WEBHOOK_SECRET      # must match the secret used by the Dashboard webhook config
SUPABASE_URL               # auto-injected
SUPABASE_SERVICE_ROLE_KEY  # auto-injected, used to bypass RLS for trusted writes
```

### Hardcoded Stripe price IDs (Supabase Edge Function)

```ts
'price_1TXn1T2LoEeIEPVE2YULkFsI' → starter      / 200  tokens / modules [1-4]
'price_1TXn1Z2LoEeIEPVEHSj3TDBF' → builder      / 800  tokens / modules [1-11]
'price_1TXn1e2LoEeIEPVE00MmiaYj' → builder      / 800  tokens / modules [1-11]
'price_1TXn1j2LoEeIEPVEjzzhcJny' → hyper_legend / 2500 tokens / modules [1-13]
'price_1TXn1o2LoEeIEPVEWICzEMHV' → hyper_legend / 2500 tokens / modules [1-13]
```

> 5 IDs, 3 tiers. Duplicates per tier are the one-time vs monthly variants of the same product.
> **These price IDs MUST match what V2.4's `STRIPE_PRICE_*` env vars resolve to.** Two sources of truth for the same data — silent drift risk.

---

## ✅ What's Verified Working

| Check | Method | Result |
|---|---|---|
| Course frontend Stripe code compiles | `npm run build` | ✅ green, 11.78s |
| `tsc` and `eslint` clean on payments.ts + call sites | `npx tsc --noEmit`, `npx eslint` | ✅ green |
| Sacred rule #4 — V2.4 `/api/stripe/webhook` is rate-limit EXEMPT | Inspected `stripe.py` — no `@limiter.limit()` on the webhook route | ✅ confirmed |
| Webhook signature verification | V2.4: `stripe.Webhook.construct_event(payload, sig, secret)`; Supabase Edge: `stripe.webhooks.constructEvent(...)`; both reject on failure | ✅ both verify |
| PaymentSuccess does NOT self-grant | Reviewed `PaymentSuccess.tsx`: comment "DISPLAY-ONLY — never writes enrollments"; only reads, polls, shows support card on timeout | ✅ confirmed |
| Webhook resilient to user-table miss | V2.4 logs `❌ User not found`; Supabase Edge function bails gracefully and logs | ✅ both safe |
| Course CHECKOUT_MODE separation | Token packs → `payment`, subscriptions → `subscription` (`stripe_service.py:63`) | ✅ correct |
| Server-side trust model | V2.4 derives `user_id` from session metadata (not from frontend `success_url` query) — buyer cannot enroll a victim by swapping a query param | ✅ trustworthy |
| Test suites exist in V2.4 | `backend/tests/test_stripe.py` + `test_rate_limiting.py` | ✅ present (not run as part of this audit) |

---

## 🔴 Risks — Highest Impact First

### R1 — DOUBLE-WRITE if Stripe is configured to fan out to both webhook endpoints

**The architecture:** both V2.4's `/api/stripe/webhook` AND Supabase Edge Function `stripe-webhook` are fully implemented webhook handlers. Both:
- verify signature and accept the same `checkout.session.completed` event,
- award BROski$ tokens,
- update `users.subscription_tier`,
- write to the `users` table.

**The risk:** if both URLs are registered in the Stripe Dashboard (or with the Stripe CLI in dev), **every purchase fires both handlers**. Result:
- User gets **2× BROski$** (V2.4 awards via `token_transactions` INSERT + `users.broski_tokens` UPDATE; Supabase Edge function ALSO does `UPDATE users SET broski_tokens = current + tokens`).
- V2.4 has dedup via `stripe_payment_intent_id UNIQUE` on `token_transactions` — **but Supabase Edge function does not.** Its `INSERT token_transactions` has no idempotency guard.
- Enrollment is `UPSERT onConflict(user_id,course_id)` in Supabase, so that side is safe.
- `users.subscription_tier` overwrite is harmless (both set the same value).

**Verification required (Stripe Dashboard, human gate):**
1. Open dashboard.stripe.com → Developers → Webhooks
2. List endpoints. Expected: ONE active endpoint. If both V2.4 (`https://api.hypercode.broski.dev/api/stripe/webhook`) AND the Supabase Edge URL are listed and enabled → this is the bug.
3. Pick one as the canonical handler. The Supabase Edge function is the lighter, no-Docker option and gives faster Stripe → DB latency; V2.4 is heavier but co-located with the user-tier logic.

**Fix path (if both are active):**
- Disable the redundant Stripe Dashboard webhook endpoint.
- Reduce the unused handler to a stub or delete entirely so no dead-code drift.

> **This is the most important thing to verify before the next paid transaction.**

### R2 — Pricing.tsx env vars not documented → fresh Vercel deploy silently breaks Path B

5 vars (`VITE_STRIPE_STARTER_URL`, `VITE_STRIPE_BUILDER_URL`, `VITE_STRIPE_HYPER_LEGEND_URL`, `VITE_STRIPE_BUILDER_MONTHLY_URL`, `VITE_STRIPE_HYPER_LEGEND_MONTHLY_URL`) are read by `Pricing.tsx` but live nowhere in `.env.example`. Anyone seeding a new env (CI, preview deploy, new dev) breaks Path B without realising.

**Fix:** add these to `.env.example` with placeholder values + a comment pointing to Stripe Dashboard → Payment Links.

### R3 — Naming inconsistency between webhook tier IDs

| Source | Tier name |
|---|---|
| V2.4 `PRICE_MAP` | `starter` `builder` `hyper` `pro_monthly` `pro_yearly` `hyper_monthly` `hyper_yearly` |
| V2.4 `TIER_MAP` | `pro` `pro` `hyper` `pro` `pro` `hyper` `hyper` |
| Supabase Edge `PRICE_TO_TIER` | `starter` `builder` `hyper_legend` |
| Pricing.tsx tier IDs | `starter` `builder` `hyper-legend` (kebab) / `hyperLegend` (camel) |

`hyper` (V2.4 token pack £35) and `hyper_legend` (Supabase course tier £149) are **different products** but the names overlap dangerously. The slug `builder` is **used by both** TokensPage (£15 token pack) AND Pricing (£79 course tier) but routed by different paths. If someone wires `createCheckoutSession('builder', user.id)` from a tier card by mistake → they'd charge the £15 token-pack price for a £79 course tier.

**Fix:** rename one side. Recommend prefixing: `pack_starter`, `pack_builder`, `pack_hyper` (V2.4 token packs) vs `tier_starter`, `tier_builder`, `tier_hyper_legend` (course tiers).

### R4 — Hardcoded Stripe price IDs in source (Supabase Edge Function)

`PRICE_TO_TIER` lists real Stripe price IDs in committed source. They're not secrets (price IDs are not sensitive), but they're a hardcoded coupling: if V2.4's `STRIPE_PRICE_*` env vars drift from these IDs, the webhook silently fails to award tokens.

**Fix:** mirror the env-var pattern from V2.4 — read `STRIPE_PRICE_STARTER` etc. from Supabase function env, build PRICE_TO_TIER at runtime. One source of truth.

### R5 — Stale marketing copy on Pricing.tsx

Line 168: `"72/72 tests passing · Platform LIVE · BROski$ economy active"`. Current is 251 tests passed / 6 skipped per V2.4 CLAUDE.md. Visible on the public marketing page.

### R6 — Pricing.tsx uses raw Tailwind colours, not `hfz-*` tokens

`bg-gray-950`, `bg-purple-600`, `bg-green-600`, `bg-yellow-500` etc. Hits the design-brain "colour slop" blacklist and breaks Sacred Rule #9 (Course): "Lab pages = `hfz-*` Tailwind tokens. Landing page = inline styles + CSS vars." Pricing is neither — it's drifted to generic Tailwind. Visual inconsistency on a load-bearing money-path page.

### R7 — Zero automated test coverage of any Stripe path in the Course repo

`frontend/tests/` has no `stripe-*` or `payment-*` spec. The button → checkout-URL handoff (Path A, C) is fully Playwright-automatable with route interception (mock V2.4 response) — same pattern as the existing `auth.spec.ts`. Currently nothing guards against `payments.ts` regressing.

---

## 🟡 Polish & Drift

- `payments.ts:50` `buildStripePaymentLinkUrl()` is legacy — not called by current `Pricing.tsx` (which uses per-tier env vars). Dead code, or kept for future use? Worth annotating or removing.
- V2.4 `success_url` default is `http://localhost:3000/success` but Course frontend runs on Vite at `:5173` and overrides via the body. The default is misleading.
- V2.4 webhook in dev mode silently skips signature verification when `STRIPE_WEBHOOK_SECRET` is unset (`stripe.py:128-136`). This is a deliberate dev-friendly choice but worth a sacred-rule entry so it can't accidentally ship.
- `Admin.tsx` queries a `payments` table — make sure RLS allows admin role to read it (Admin route is `<AdminRoute role="admin">`-gated, so the policy must permit `users.role = 'admin'`).

---

## 🧪 Manual E2E Test Runbook — `4242 4242 4242 4242`

**Pre-flight (terminal):**

```powershell
# 1. V2.4 stack up
cd "H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4"
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
curl http://localhost:8000/health   # expect 200

# 2. Stripe CLI webhook forwarding (so V2.4 webhook gets the test event)
stripe listen --forward-to localhost:8000/api/stripe/webhook
# Copy the whsec_… it prints — that's the dev webhook secret

# 3. Set V2.4 STRIPE_WEBHOOK_SECRET in docker-compose.secrets.yml or .env to that whsec_
# (or stop+start V2.4 with it set)

# 4. Course frontend dev server
cd "H:\HYPERFOCUSZONE\HperCore\Hyper-Vibe-Coding-Course\frontend"
$env:VITE_HYPERCODE_API_URL = "http://localhost:8000"
npm run dev   # opens on :5173
```

**Path A — Token Pack purchase (TokensPage):**

1. Browser → http://localhost:5173/login → sign in as a known test user.
2. Browser → http://localhost:5173/tokens → note current BROski$ balance in the header.
3. Click "Buy for £5" on the Starter Pack.
4. **Expected:** redirect to `checkout.stripe.com/c/pay/cs_test_…`. If you get `Failed to fetch` or a toast saying "checkout failed" → V2.4 is not running, `VITE_HYPERCODE_API_URL` is wrong, or V2.4 `STRIPE_PRICE_STARTER` env var is unset.
5. On the Stripe page, fill in:
   - Card: `4242 4242 4242 4242`
   - Expiry: any future date (e.g. `12/29`)
   - CVC: any 3 digits (e.g. `123`)
   - ZIP: any (e.g. `LL14 8XY`)
   - Email: an address you can verify in the DB
6. Click "Pay £5".
7. **Expected:** redirected to `localhost:5173/payment-success?session_id=cs_test_…`.
8. Watch the page — it should show "Wiring up the Z0ne…" for 1–5s while polling, then "You're in! 🚀" with the celebration ring.
9. **Verify in stripe-cli terminal:** a `checkout.session.completed` event was forwarded with HTTP 200 from V2.4.
10. **Verify in V2.4 logs:** `docker compose logs hypercode-core -n 50` — expect lines like `📨 Stripe webhook: checkout.session.completed` → `💾 Payment saved` → `🌟 User … → tier=pro` → `🪙 Awarded 200 BROski$ to user …` → `💳 10G complete: … results={'payment':True,'subscription':True,'tokens':True}`.
11. **Verify in Supabase (SQL via MCP `execute_sql` — wrap in `BEGIN;…ROLLBACK;`):**
    ```sql
    SELECT broski_tokens, subscription_tier, subscription_status FROM users WHERE id = '<test-user-uuid>';
    -- expect +200 tokens, tier='pro', status='active'

    SELECT amount, reason, stripe_payment_intent_id, created_at
    FROM token_transactions
    WHERE user_id = '<test-user-uuid>' ORDER BY created_at DESC LIMIT 3;
    -- expect a row: amount=200, reason='stripe_purchase', session_id non-null
    ```
12. **Verify Stripe Dashboard:** the test payment appears in Payments tab with status `Succeeded`.
13. ⚠️ **Critical R1 check:** open the Supabase Edge function logs (`supabase functions logs stripe-webhook --tail` or via dashboard). If you ALSO see `✅ Awarded 200 BROski$ to <email>` from the Edge function → you've reproduced the double-write. Pick one handler to keep, disable the other in the Stripe Dashboard.

**Path B — Pricing tier purchase:**

1. Browser → http://localhost:5173/pricing.
2. Click "Get Builder 🔥" on the Builder card.
3. **Expected:** redirect directly to Stripe Payment Link URL (no V2.4 hop — the link is pre-baked). If you see the amber "Checkout temporarily unavailable" toast → the `VITE_STRIPE_BUILDER_URL` env var is unset.
4. Pay with `4242 4242 4242 4242` as above. Stripe redirects to the Payment Link's configured success URL.
5. Verification steps 10–13 as Path A — the webhook chain is identical from step 10 onwards.

**Path C — Individual course purchase:**

1. Sign in. Browser → http://localhost:5173/catalog/<some-course-id>.
2. Click the buy button (course-specific).
3. Pay with `4242`. On return, PaymentSuccess polls `enrollments` for `(user_id, course_id)` — should resolve within 5s and show "Start learning now →".
4. Verify: `SELECT * FROM enrollments WHERE user_id = '<uuid>' AND course_id = '<course-uuid>';` returns one row.

**Negative tests worth running:**

- Card `4000 0000 0000 0002` → decline. Verify Stripe returns to `cancel_url=/pricing`, no DB write, no token grant.
- Card `4000 0027 6000 3184` → 3D Secure challenge. Verify the auth flow completes and the webhook still fires once on success.
- Refresh the PaymentSuccess page mid-poll (don't wait for the celebration). Verify it idempotently shows the right state from the DB — no double-grant.

---

## 🛠️ Recommended Next Moves

| # | Action | Effort | Risk if skipped |
|---|---|---|---|
| 1 | **Verify webhook fan-out in Stripe Dashboard** (R1) | 5 min, human | 🔴 Double-grants on every paid transaction |
| 2 | **Add the 5 missing `VITE_STRIPE_*_URL` vars to `.env.example`** (R2) | 5 min, code | 🟡 Silent Path B break on fresh deploys |
| 3 | **Write a Playwright spec for Path A**: mock V2.4 `/api/stripe/checkout` → assert TokensPage button → `window.location.assign(...)` to a `checkout.stripe.com/…` URL. Mirror `auth.spec.ts` pattern. | ~30 min, code | 🟡 No regression guard on the most-trafficked checkout button |
| 4 | **De-duplicate naming** (R3) — prefix token packs vs tiers | ~1h | 🟡 Future bug magnet |
| 5 | **Read Supabase Edge `PRICE_TO_TIER` from env vars** (R4) | ~30 min | 🟡 Silent drift on price-ID rotation |
| 6 | **Migrate `Pricing.tsx` to `hfz-*` tokens** (R6) — design-brain skill task | ~1–2h | 🟢 Cosmetic but on a money-path page |
| 7 | **Add a sacred rule** for "V2.4 webhook signature check is BYPASSED in dev when `STRIPE_WEBHOOK_SECRET` is unset" so it can't ship as prod default | 5 min, doc | 🟡 Production webhook spoofing risk if env var ever missing |
| 8 | **Run V2.4 stripe test suite** to confirm existing coverage: `pytest backend/tests/test_stripe.py backend/tests/test_rate_limiting.py -q` | 5 min | 🟢 Already exists, just unverified in this audit |

---

## 📦 Files Touched / Referenced in This Audit

```
Hyper-Vibe-Coding-Course/
  frontend/.env.example                                       ← missing 5 VITE_STRIPE_*_URL vars
  frontend/src/lib/payments.ts                                ← Paths A + C client
  frontend/src/pages/TokensPage.tsx                           ← Path A button
  frontend/src/pages/Pricing.tsx                              ← Path B buttons + slop colours
  frontend/src/pages/PaymentSuccess.tsx                       ← display-only confirmation
  frontend/src/pages/Admin.tsx                                ← payments dashboard view
  supabase/functions/stripe-webhook/index.ts                  ← R1 candidate handler #2
  frontend/tests/                                             ← no Stripe tests exist

HyperCode-V2.4/
  backend/app/routes/stripe.py                                ← /api/stripe/checkout + /webhook
  backend/app/services/stripe_service.py                      ← PRICE_MAP, handle_webhook_event
  backend/tests/test_stripe.py                                ← exists, not exercised in this audit
  backend/tests/test_rate_limiting.py                         ← verifies webhook is exempt
```

---

## ✅ Bottom Line

The Stripe integration is **production-functional and security-sound** — webhook signatures verified, PaymentSuccess never self-grants, V2.4 webhook is rate-limit exempt per sacred rule. Money has flowed through it (per CLAUDE.md "E2E proven April 25").

But the architecture has accumulated **silent failure modes** through honest evolution:
- Two webhook handlers exist; whether both fire is a 5-minute Dashboard check that's not been done.
- Five env vars on the marketing-critical Pricing page are not documented.
- Three diverging tier-naming schemes that work today only because the paths are separate.
- Zero automated coverage of the most-trafficked checkout buttons.

None of these are emergencies. **R1 (the webhook double-write) is the only thing that can corrupt user balances right now** — that's the next 5 minutes. Everything else is hygiene that compounds.

---

*Built by @welshDog · Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁧 · Audit by Claude (Opus 4.7) · 2026-05-20*
*"Stop apologising for your brain. Start building." ♾️*
