---
name: hyper-vibe-course
description: Use for anything related to the Hyper-Vibe Coding Course — student invites, Supabase, Stripe payments, course frontend, token shop, quiz system, or enrollment flow. Triggers on: "course", "student", "invite", "Supabase", "/welcome", "payment", "enrollment".
---

# 🎓 Hyper-Vibe Course Skill

## Stack
- Frontend: React + Vite + Tailwind
- Backend: Supabase (Postgres + RLS + Edge Functions)
- Payments: Stripe (checkout → webhook → BROski$ award)
- Deploy: Vercel
- Dev command: `npm run dev:frontend` (NOT `npm run dev`)
- Path: `H:\Hyper-Vibe-Coding-Course`

## What's Live ✅
- /welcome page verified: `localhost:5174/welcome`
- /pricing → Stripe checkout → /payment-success → enrolled
- BROski$ balance card on dashboard
- TokensPage wired to checkout API
- Certificates, Quiz/exercise system, Referral system
- 7 courses seeded in Supabase (price_pence + is_active)
- RLS enabled — security_invoker = on

## Pending Manual Steps
- [ ] Register Supabase DB Webhook: token_transactions → INSERT → sync-tokens-to-v24
- [ ] Set COURSE_WEBHOOK_SECRET in V2.4 .env AND Supabase Edge Function env vars
- [ ] Set VITE_STRIPE_PAYMENT_LINK_URL in .env.local + Vercel
- [ ] Fix any hardcoded port 8081 → 8000 in frontend hooks

## Token Grants (Stripe tiers)
- starter = 200 BROski$
- builder = 800 BROski$
- hyper = 2500 BROski$

## Key Supabase facts
- Table: courses uses price_pence (int) + is_active (bool)
- Token sync: POST /api/v1/economy/award-from-course (X-Sync-Secret header)
- Idempotency: CourseSyncEvent model — never double-awards

## First Student Invite — Steps
1. Confirm /welcome is live: `localhost:5174/welcome`
2. Open Supabase dashboard → Auth → Users → Invite
3. Send invite email
4. Mark done in WHATS_DONE.md
