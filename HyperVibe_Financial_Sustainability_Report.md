# Hyper-Vibe Coding Course — Financial Sustainability Report
**Business Plan: Revenue Model, Cost Analysis & Multi-Year Projections**
*Prepared May 2026 | welshDog / Hyper-Vibe Coding Course*

---

## Executive Summary

The Hyper-Vibe Coding Course is a neurodivergent-first AI and full-stack coding education platform built by and for ADHD, dyslexic, and autistic learners. It operates on a five-tier pricing model combining one-time payments and optional monthly subscriptions. This report demonstrates the platform's financial viability across a 3-year horizon, showing that operating costs are covered from a minimal number of monthly sales, and that the recurring subscription layer provides a durable revenue floor regardless of new customer acquisition.

The platform is structurally designed to **pay for itself** — with a sustainable pricing model, low break-even threshold, and compounding subscriber base that grows in value over time.

---

## Platform Infrastructure & Running Costs

### Core Stack

The Hyper-Vibe platform runs on a modern, cloud-native stack designed for scalability without unnecessary cost bloat.

| Service | Purpose | Estimated Monthly Cost |
|---|---|---|
| Supabase Pro | Database, Auth, Edge Functions, Storage | £25/mo |
| Vercel Pro | Frontend hosting, CI/CD, Edge network | £20/mo |
| Stripe | Payment processing (2.9% + 30p per transaction) | Variable |
| IBM Quantum API | Quantum module compute access (Hyper Legend tier) | £50–£200/mo |
| Discord bots & hosting | Community automation, BROski$ economy | £10/mo |
| Domain & DNS | Platform identity | £5/mo |
| **Base fixed costs** | | **£110/mo (low) — £260/mo (high)** |

### Cost Scaling Behaviour

Infrastructure costs scale **gradually**, not linearly. Supabase and Vercel pricing tiers mean the platform can support hundreds of active users before hitting the next cost tier. The most variable cost is IBM Quantum API usage, which only activates for Hyper Legend tier students. At low Legend enrolment, quantum costs remain near the floor (~£50/mo). As Legend students increase, this cost rises — but is offset by the significantly higher revenue per Legend sale.

**Conservative annual operating cost estimate: £1,800 – £3,600/yr**

---

## Pricing Model

### Five-Tier Structure

The platform uses a five-tier pricing architecture designed around behavioural economics principles — specifically the **anchor pricing effect**, where middle tiers feel like exceptional value relative to the premium tier above them[cite:64].

| Tier | One-Time Price | Monthly Option | Modules Included | BROski$ Tokens |
|---|---|---|---|---|
| 🌱 Starter | £29 | — | M1 only | 100 |
| ⚡ Pro | £49 | — | M1–M4 | 300 |
| 🔥 Builder *(hero tier)* | £97 | £12/mo | M1–M9 | 800 |
| 🏛️ Architect | £167 | £18/mo | M1–M11 | 1,500 |
| ⚛️ Hyper Legend | £247 | £25/mo | M1–M13 + Quantum | 2,500 |

### Pricing Rationale

**One-time payments are the primary offer.** Research into online course pricing psychology shows that learners — especially neurodivergent buyers — respond strongly to ownership framing ("pay once, own forever") versus subscription models that create ongoing cognitive load and guilt[cite:64]. One-time pricing also reduces churn risk and builds trust faster.

**Monthly subscriptions serve as an accessibility option**, not the default. They allow learners who cannot afford upfront payment to access the course. Critically, the monthly pricing is structured so that sustained monthly payments cost more over 12 months than the one-time fee — this naturally nudges most buyers toward one-time purchase while keeping the door open for those with cash flow constraints.

**Charm pricing** (£29, £49, £97, £167, £247) is used throughout. Research consistently shows that prices ending in 7 or 9 outperform round numbers in conversion rates for digital products[cite:64][cite:67].

**Comparison to market:** UK coding bootcamps charge between £4,000 and £13,000 for full-time programmes[cite:65]. Self-paced online courses on platforms like Udemy range from £10–£200, but offer no community, no evolving AI features, and no neurodivergent-first design[cite:59]. The Hyper-Vibe course at £97–£247 is positioned as a premium self-paced product — significantly cheaper than bootcamps, significantly more valuable than commodity courses.

---

## Break-Even Analysis

### Monthly Break-Even (Fixed Costs Only)

At the conservative fixed cost of £110/month, the platform breaks even with remarkably few sales:

| Sales Scenario | Revenue | Covers Costs? |
|---|---|---|
| 2× Builder (£97) one-time | £194 | ✅ Yes (low month) |
| 1× Architect (£167) one-time | £167 | ✅ Yes (low month) |
| 1× Hyper Legend (£247) one-time | £247 | ✅ Yes (any month) |
| 10× monthly Builder subs (£12) | £120 | ✅ Yes (recurring floor) |

*Note: Stripe fees (2.9% + 30p) reduce net revenue slightly. On a £97 sale, net received is approximately £91.88.*

### The Subscription Floor Model

The most powerful aspect of the pricing model is the **recurring subscription layer**. Each monthly subscriber adds a permanent revenue floor that compounds over time. Once a subscriber cohort is established, operating costs are covered regardless of new sales activity.

**Target: 25 active monthly subscribers = self-sustaining platform**

| Monthly Subscribers | Blended Revenue (est. £14 avg) | vs. Running Costs |
|---|---|---|
| 10 subscribers | £140/mo | Covers low-cost months |
| 25 subscribers | £350/mo | Covers all operating scenarios |
| 50 subscribers | £700/mo | Covers costs + reinvestment fund |
| 100 subscribers | £1,400/mo | Full salary contribution possible |

---

## 3-Year Revenue Projections

The following projections use **conservative assumptions**: modest growth, realistic churn on monthly subs (15%/mo), and no viral or partnership growth events. Three scenarios are modelled.

### Assumptions

- **Average sale value:** £85 (blended across all tiers, weighted toward Builder)
- **Monthly subscriber churn:** 15% per month (industry standard for self-paced courses)
- **New monthly sub sign-ups:** gradual growth from launch
- **One-time sales:** conservative linear growth

---

### Scenario A — Slow Burn (Minimal Marketing)

| Period | New One-Time Sales | Active Monthly Subs | Est. Monthly Revenue | Est. Annual Revenue |
|---|---|---|---|---|
| Month 1–3 (Launch) | 5/mo | 8 | £537 | — |
| Month 4–6 | 8/mo | 15 | £888 | — |
| **Year 1 Total** | ~80 sales | ~20 avg subs | ~£900/mo avg | **~£10,800** |
| **Year 2 Total** | ~120 sales | ~40 avg subs | ~£1,460/mo avg | **~£17,520** |
| **Year 3 Total** | ~160 sales | ~65 avg subs | ~£1,970/mo avg | **~£23,640** |

*Year 1 operating costs: ~£2,400. Net Year 1: ~£8,400 positive.*

---

### Scenario B — Steady Growth (Light Social/Discord Marketing)

| Period | New One-Time Sales | Active Monthly Subs | Est. Monthly Revenue | Est. Annual Revenue |
|---|---|---|---|---|
| Month 1–3 (Launch) | 12/mo | 20 | £1,300 | — |
| Month 4–6 | 20/mo | 40 | £2,230 | — |
| **Year 1 Total** | ~200 sales | ~45 avg subs | ~£2,300/mo avg | **~£27,600** |
| **Year 2 Total** | ~350 sales | ~90 avg subs | ~£4,030/mo avg | **~£48,360** |
| **Year 3 Total** | ~500 sales | ~140 avg subs | ~£6,000/mo avg | **~£72,000** |

*Year 1 operating costs: ~£2,400. Net Year 1: ~£25,200 positive.*

---

### Scenario C — Growth Mode (Community + Partnerships + ND Network)

| Period | New One-Time Sales | Active Monthly Subs | Est. Monthly Revenue | Est. Annual Revenue |
|---|---|---|---|---|
| Month 1–3 (Launch) | 25/mo | 40 | £2,625 | — |
| Month 4–6 | 45/mo | 90 | £5,100 | — |
| **Year 1 Total** | ~420 sales | ~100 avg subs | ~£4,700/mo avg | **~£56,400** |
| **Year 2 Total** | ~800 sales | ~220 avg subs | ~£9,880/mo avg | **~£118,560** |
| **Year 3 Total** | ~1,200 sales | ~380 avg subs | ~£16,400/mo avg | **~£196,800** |

*Year 1 operating costs: ~£3,000 (higher due to quantum usage). Net Year 1: ~£53,400 positive.*

---

## Structural Advantages & Sustainability Factors

### Why This Platform Stays Profitable

**1. Low fixed cost ceiling.** The entire platform runs for under £260/month at full operational load. This is exceptional for an education SaaS product of this complexity and feature depth.

**2. One-time revenue is immediate.** Unlike SaaS businesses that depend entirely on subscription retention, the majority of Hyper-Vibe revenue is one-time — meaning cash flow is positive from day one of sales, with no waiting for payback periods.

**3. The subscription layer is bonus revenue.** Every monthly subscriber is pure recurring income on top of the one-time sales baseline. As the subscriber base grows, the platform becomes increasingly insulated from slow sales months.

**4. Compounding community value.** The BROski$ token economy, Discord community, and BROskiPets system create **platform stickiness** — students stay engaged longer, refer others, and are more likely to upgrade tiers. This reduces the cost of customer acquisition over time.

**5. Neurodivergent market is underserved and growing.** An estimated 15–20% of the UK population is neurodivergent[cite:51]. Dedicated ND-first coding education at this price point has virtually no direct competition. Word-of-mouth within ND communities (Reddit, Discord, TikTok, X) is particularly strong, making organic growth achievable without paid advertising.

**6. Module updates retain subscribers.** The 1-year free update promise for Hyper Legend tier, and ongoing module improvements, give monthly subscribers reason to remain subscribed beyond course completion — extending lifetime value significantly.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Slow initial sales | Medium | Medium | Break-even at just 2 Builder sales/mo — very low threshold |
| High monthly churn | Medium | Low | One-time model means churn doesn't threaten survival |
| IBM Quantum costs spike | Low | Medium | Quantum only activates for Legend tier — costs covered by £247 price point |
| Platform cost increases (Vercel/Supabase) | Low | Low | Costs modelled with headroom; platform can absorb one tier increase |
| Competition enters ND space | Low | Medium | First-mover advantage + BROski$ economy creates switching cost |

---

## Conclusion

The Hyper-Vibe Coding Course financial model is structurally sound and demonstrably self-sustaining. In the most conservative scenario (Scenario A), the platform generates approximately £8,400 net in Year 1 from minimal sales activity — covering all operating costs with room for reinvestment. In realistic growth scenarios (B and C), Year 2 and Year 3 revenue scales to five and six figures respectively.

The combination of low fixed infrastructure costs, a diversified five-tier pricing model, a recurring subscription floor, and a deeply underserved target market creates a durable business that pays for itself from launch and compounds in value over time.

**The platform does not require venture funding, advertising spend, or large student cohorts to remain operational.** It is designed to run lean, grow organically through community, and scale its revenue in direct proportion to its growing student base.

---

*Report prepared for business planning purposes | Hyper-Vibe Coding Course | welshDog 🐶♾️ | Llanelli, Wales | May 2026*
