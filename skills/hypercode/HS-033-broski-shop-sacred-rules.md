# HS-033 — Sacred Rules — BROski$ Shop (8 Rules)

> **Extracted from:** `CLAUDE.md §5` · HyperCode-V2.4
> **Warning:** Break these = wrong prices charged, duplicate grants, or fulfillment silently breaks.

---

| # | Rule | Why | Consequence if broken |
|---|---|---|---|
| 1 | **`TIER_DISCOUNT_PCT` lives in TWO places — keep both in sync** | `ShopPage.tsx` (UI) + `supabase/functions/shop-purchase/index.ts` (server truth) | UI shows wrong price vs what server charges |
| 2 | **Server is ALWAYS the discount source of truth** | Client discount is preview-only | Tampered client tier gets unearned discount |
| 3 | **`metadata.image_url` is inside JSONB `metadata`** | Schema: `item.metadata?.image_url` | Direct column access → `undefined`, image gone |
| 4 | **`metadata.consumable = true` = re-buyable, never locks to "Owned"** | Consumables use count-based ownership | Blocks re-purchase, breaks economy |
| 5 | **`shop-purchase` Edge Function: `verify_jwt: ON` always** | All spend is authenticated | Unauthenticated users drain real token balances |
| 6 | **Auto-refund is server-side via `award_tokens`** — never add a client-side refund path | Server refunds if purchase row fails after spend | Client refund = double-grant + balance corruption |
| 7 | **Agent access polls `provision_status` every 6s, max 10 attempts** | Race between frontend poll and async V2.4 provisioner | Too fast = hammers DB; too slow = looks broken |
| 8 | **`price_gbp` is nullable** — always use `price_gbp != null` before rendering | Some items are token-only | Renders `£undefined` or crashes `toFixed()` |

---

> 🔴 Sacred = non-negotiable. Surface violations immediately.
