'use client'

/**
 * Pricing Page — BROski Plans
 * Phase 10H | HyperCode V2.4 | BROski♾
 *
 * Shows:
 *   • 3 one-time token packs
 *   • 2 course subscriptions with monthly/yearly toggle
 * Clicking any plan POSTs to /api/stripe/checkout and redirects to Stripe.
 */

import React, { useState } from 'react'
import { PricingCard } from '@/components/PricingCard'

// ── API URL ───────────────────────────────────────────────────────────────────

function getApiUrl(): string {
  // Primary: NEXT_PUBLIC_API_URL (set in .env.local)
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL
  // Fallback: reconstruct from host/port vars (matches rest of dashboard hooks)
  if (typeof window !== 'undefined') {
    const host = process.env.NEXT_PUBLIC_CORE_WS_HOST ?? window.location.hostname
    const port = process.env.NEXT_PUBLIC_CORE_WS_PORT ?? '8000'
    return `http://${host}:${port}`
  }
  return 'http://localhost:8000'
}

// ── Plan definitions (prices LOCKED April 14 2026 — do NOT change) ────────────

const TOKEN_PACKS = [
  {
    priceKey:  'starter',
    name:      'Starter Pack',
    price:     '£5',
    tokens:    200,
    ctaLabel:  'Get 200 BROski$',
    highlight: false,
    badge:     undefined as string | undefined,
    features:  [
      '200 BROski$ tokens',
      'No expiry — spend any time',
      'Access to the digital shop',
    ],
  },
  {
    priceKey:  'builder',
    name:      'Builder Pack',
    price:     '£15',
    tokens:    800,
    ctaLabel:  'Get 800 BROski$',
    highlight: true,
    badge:     'Most Popular' as string | undefined,
    features:  [
      '800 BROski$ tokens',
      'Best price per token',
      'No expiry — spend any time',
      'Access to the digital shop',
    ],
  },
  {
    priceKey:  'hyper',
    name:      'Hyper Pack',
    price:     '£35',
    tokens:    2500,
    ctaLabel:  'Go Hyper Mode ⚡',
    highlight: false,
    badge:     undefined as string | undefined,
    features:  [
      '2500 BROski$ tokens',
      'Maximum token value',
      'No expiry — spend any time',
      'Access to the digital shop',
      'Unlock everything',
    ],
  },
] as const

type SubPlan = {
  priceKey: string
  name: string
  monthlyPrice: string
  yearlyPrice: string
  yearlyNote: string
  ctaLabel: string
  highlight: boolean
  badge?: string
  features: readonly string[]
}

const SUBSCRIPTION_PLANS: SubPlan[] = [
  {
    priceKey:     'pro_monthly',   // overridden by billing toggle
    name:         'Pro Course',
    monthlyPrice: '£9/mo',
    yearlyPrice:  '£90/yr',
    yearlyNote:   '= £7.50/mo — save £18',
    ctaLabel:     'Start Learning',
    highlight:    false,
    features:     [
      'Full course access',
      'Community Discord',
      'Course updates forever',
      'Cancel any time',
    ],
  },
  {
    priceKey:     'hyper_monthly', // overridden by billing toggle
    name:         'Hyper Elite',
    monthlyPrice: '£29/mo',
    yearlyPrice:  '£290/yr',
    yearlyNote:   '= £24.17/mo — save £58',
    ctaLabel:     'Go Elite 🦅',
    highlight:    true,
    badge:        'Best Value',
    features:     [
      'Everything in Pro',
      'Live group sessions',
      'Priority support',
      'Early access to new content',
      'Direct Discord access to Lyndz',
    ],
  },
]

// ── Section heading ───────────────────────────────────────────────────────────

function SectionHeading({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <h2
      style={{
        margin:        '0 0 16px',
        fontSize:      12,
        fontWeight:    700,
        color:         'var(--text-secondary)',
        letterSpacing: '0.09em',
        textTransform: 'uppercase',
        fontFamily:    'var(--font-mono)',
      }}
    >
      {children}
    </h2>
  )
}

// ── Billing toggle ────────────────────────────────────────────────────────────

type Billing = 'monthly' | 'yearly'

function BillingToggle({
  value,
  onChange,
}: {
  value: Billing
  onChange: (v: Billing) => void
}): React.JSX.Element {
  return (
    <div
      role="group"
      aria-label="Billing period"
      style={{
        display:        'inline-flex',
        alignItems:     'center',
        gap:            0,
        background:     'rgba(255,255,255,0.05)',
        border:         '1px solid var(--pane-border)',
        borderRadius:   8,
        padding:        3,
      }}
    >
      {(['monthly', 'yearly'] as Billing[]).map((b) => (
        <button
          key={b}
          onClick={() => onChange(b)}
          aria-pressed={value === b}
          style={{
            padding:      '5px 16px',
            borderRadius: 5,
            border:       'none',
            background:   value === b ? 'var(--accent-cyan)' : 'transparent',
            color:        value === b ? '#fff' : 'var(--text-secondary)',
            fontWeight:   value === b ? 700 : 500,
            fontSize:     12,
            cursor:       'pointer',
            fontFamily:   'var(--font-mono)',
            transition:   'background 0.12s, color 0.12s',
          }}
        >
          {b === 'monthly' ? 'Monthly' : 'Yearly'}
          {b === 'yearly' && (
            <span
              style={{
                marginLeft:  5,
                fontSize:    9,
                fontWeight:  700,
                color:       value === 'yearly' ? 'rgba(255,255,255,0.8)' : 'var(--accent-green)',
                letterSpacing: '0.04em',
              }}
            >
              SAVE
            </span>
          )}
        </button>
      ))}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PricingPage(): React.JSX.Element {
  const [loadingId, setLoadingId]   = useState<string | null>(null)
  const [errorId,   setErrorId]     = useState<string | null>(null)
  const [errorMsg,  setErrorMsg]    = useState<string | null>(null)
  const [billing,   setBilling]     = useState<Billing>('monthly')

  const handleBuy = async (priceKey: string) => {
    setLoadingId(priceKey)
    setErrorId(null)
    setErrorMsg(null)

    try {
      const res = await fetch(`${getApiUrl()}/api/stripe/checkout`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ price_id: priceKey }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({})) as { detail?: string }
        throw new Error(body.detail ?? `Request failed (${res.status})`)
      }

      const data = await res.json() as { checkout_url?: string }
      if (!data.checkout_url) throw new Error('No checkout URL returned')

      window.location.href = data.checkout_url
      // no setLoadingId(null) — page is navigating away
    } catch (e) {
      setErrorId(priceKey)
      setErrorMsg(e instanceof Error ? e.message : 'Payment failed to start, try again')
      setLoadingId(null)
    }
  }

  return (
    <div
      style={{
        maxWidth:  920,
        margin:    '0 auto',
        padding:   '28px 20px 40px',
        display:   'flex',
        flexDirection: 'column',
        gap:       36,
      }}
    >
      {/* ── Header ──────────────────────────────────── */}
      <header style={{ textAlign: 'center' }}>
        <h1
          style={{
            fontSize:   26,
            fontWeight: 800,
            color:      'var(--text-primary)',
            margin:     '0 0 8px',
            fontFamily: 'var(--font-primary)',
          }}
        >
          💳 BROski Plans
        </h1>
        <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: 13, lineHeight: 1.6 }}>
          Token packs for the shop &middot; Course subscriptions &middot; Built for ADHD brains 🧠
        </p>
      </header>

      {/* ── Token packs ─────────────────────────────── */}
      <section>
        <SectionHeading>🪙 Token Packs — one-time payment</SectionHeading>
        <div
          style={{
            display:             'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap:                 16,
          }}
        >
          {TOKEN_PACKS.map((plan) => (
            <PricingCard
              key={plan.priceKey}
              name={plan.name}
              price={plan.price}
              tokens={plan.tokens}
              features={[...plan.features]}
              priceKey={plan.priceKey}
              ctaLabel={plan.ctaLabel}
              highlight={plan.highlight}
              badge={plan.badge}
              loading={loadingId === plan.priceKey}
              error={errorId === plan.priceKey ? (errorMsg ?? undefined) : undefined}
              onClick={handleBuy}
            />
          ))}
        </div>
      </section>

      {/* ── Course subscriptions ─────────────────────── */}
      <section>
        <div
          style={{
            display:        'flex',
            alignItems:     'center',
            justifyContent: 'space-between',
            flexWrap:       'wrap',
            gap:            10,
            marginBottom:   16,
          }}
        >
          <SectionHeading>🎓 Course Subscriptions — recurring</SectionHeading>
          <BillingToggle value={billing} onChange={setBilling} />
        </div>

        <div
          style={{
            display:             'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap:                 16,
          }}
        >
          {SUBSCRIPTION_PLANS.map((plan) => {
            const activeKey =
              billing === 'yearly'
                ? plan.priceKey.replace('monthly', 'yearly')
                : plan.priceKey.replace('yearly', 'monthly')

            const displayPrice  = billing === 'yearly' ? plan.yearlyPrice  : plan.monthlyPrice
            const yearlyNote    = billing === 'yearly' ? plan.yearlyNote    : undefined

            const featuresWithNote = yearlyNote
              ? [...plan.features, yearlyNote]
              : [...plan.features]

            return (
              <PricingCard
                key={plan.priceKey}
                name={plan.name}
                price={displayPrice}
                features={featuresWithNote}
                priceKey={activeKey}
                ctaLabel={plan.ctaLabel}
                highlight={plan.highlight}
                badge={plan.badge}
                loading={loadingId === activeKey}
                error={errorId === activeKey ? (errorMsg ?? undefined) : undefined}
                onClick={handleBuy}
              />
            )
          })}
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────── */}
      <p
        style={{
          fontSize:   11,
          color:      'var(--text-secondary)',
          textAlign:  'center',
          margin:     0,
          lineHeight: 1.6,
        }}
      >
        Secure checkout powered by Stripe &middot; All prices in GBP &middot; Cancel subscriptions any time
      </p>
    </div>
  )
}
