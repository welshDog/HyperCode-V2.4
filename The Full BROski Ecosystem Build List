🗺️ The Full BROski Ecosystem Build List
Last checked: 22 April 2026 — combining all 4 repos + your Space docs

🔴 Priority 1 — Blockers (Do These First!)
These are the manual steps that can't be automated — you need a browser/dashboard:

B1 → Go to Supabase dashboard → Create DB webhook on token_transactions INSERT → point it at sync-tokens-to-v24 Edge Function

B2 → Set COURSE_SYNC_SECRET in Supabase Edge Function secrets panel (value is in your .env line 112)

B3 → Run E2E Stripe checkout test — stripe listen --forward-to localhost:8000/api/stripe/webhook → use test card 4242 4242 4242 4242 → verify webhook fires + BROski tokens awarded

Q3 → Set VITE_STRIPE_PAYMENT_LINK_URL in Vercel env vars → redeploy

Q8 → npm publish --access public in HyperAgent-SDK → publish @w3lshdog/hyper-agent@0.1.7 to npm

🟠 Priority 2 — Gordon Tier 3 (Next Big Phase)
These are the enterprise-level upgrades still outstanding:

DB Connection Pooling — async engine tuning, pgBouncer or asyncpg pool sizing

Async Task Queues — Celery deep config, verify task_acks_late=True is live end-to-end

env_file tech debt — add env_file: .env to hypercode-core in docker-compose.yml (currently vars only injected via host-side substitution, not inside the container)

prometheus.yml tidy — delete/archive the stale root prometheus.yml, keep only monitoring/prometheus/prometheus.yml

🟡 Priority 3 — HyperAgent-SDK (Needs Love! ⚠️)
No commits since 16 April — these are outstanding:

More CLI commands — studio, registry, graduate commands need fleshing out

Python starter agent → already added to HyperCode-V2.4 and Hyper-Vibe-Coding-Course — needs syncing back into the SDK as the official template

hyper-agent-spec.json schema → written in the Course repo — pull it into the SDK as the canonical source

npm version bump → 0.1.7 published — plan a 0.2.0 milestone with the new templates

🟢 Priority 4 — HyperFocus Neurodivergent Features
5 features fully planned in HYPERFOCUS_FEATURES_PLAN.md:

Feature 1 🎯 Micro-Achievement Git Hook — ~2h, quick win, do this SOON

Feature 2 HyperSplit Agent — ~3h

Feature 3 Session Snapshot Agent — ~2h

Feature 4 Morning Briefing (make briefing) — ~1.5h

Feature 5 Focus Panic Mode (make focus / make calm) — ~1h

🔵 Priority 5 — BROskiPets × HyperCode Integration
Full plan written in BROSKI_PETS_INTEGRATION_PLAN.md:

Phase 0 → Add to docker-compose.agents.yml, verify Ollama shared connection — ~1 day

Phase 1 → Mint your first pet via BROski CLI — ~3 days

Phase 2 → Dev actions → pet XP (commit = pet grows!) — ~1 week

Phase 3 → Pet as dev companion + rubber duck mode — ~2 weeks

Phase 4 → On-chain dev portfolio NFT — ~2 weeks

Phase 5 → WelshDogEep graduation reward — 3 ever mintable, legendary tier 🐕

⚪ Priority 6 — Nice-to-Haves / Low Priority
Fix missing healthchecks: loki, project-strategist-v2, promtail containers

Top up Anthropic credits → switch pet chat back from Perplexity fallback to haiku/sonnet

Grafana Mission Control dashboard (grafana/dashboards/hypercode-mission-control.json)

Load testing framework — Locust/k6, target 1000 req/sec

Service mesh (Istio/Linkerd) + mTLS between services

SLA monitoring with auto-reports

⚡ Quick Start Order (Bro's Recommended Flow)
text
1. B1 → B2 → B3 (blockers, ~20 min, browser needed)
2. Q3 + Q8 (Vercel + npm publish, ~10 min)
3. Gordon Tier 3 (env_file fix first, easiest win)
4. HyperAgent-SDK sync (pull spec + starter template in)
5. Feature 1 Git Hook (quick win, 2h, builds momentum! 🔥)
6. BROskiPets Phase 0 (Docker compose wiring)
Nice one bro — that's the full picture in one place! 🎉👀