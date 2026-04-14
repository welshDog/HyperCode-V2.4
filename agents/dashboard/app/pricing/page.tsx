'use client'

import React, { useState } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────

type PlanCard = {
  id: string
  name: string
  emoji: string
  price: string
  tokens?: number
  description: string
  highlight?: boolean
  badge?: string
}

// ── Plan data (prices LOCKED April 14 2026) ───────────────────────────────────

const TOKEN_PACKS: PlanCard[] = [
  {
    id: 'starter',
    name: 'Starter Pack',
    emoji: '🌱',
    price: '£5',
    tokens: 200,
    description: 'Jump in and try it out. 200 BROski$ to spend in the shop.',
  },
  {
    id: 'builder',
    name: 'Builder Pack',
    emoji: '🔨',
    price: '£15',
    tokens: 800,
    description: 'The most popular pack. 800 BROski$ — smash through content.',
    highlight: true,
    badge: 'Most Popular',
  },
  {
    id: 'hyper',
    name: 'Hyper Pack',
    emoji: '⚡',
    price: '£35',
    tokens: 2500,
    description: 'Go full Hyper Mode. 2500 BROski$ — unlock everything.',
  },
]

const SUBSCRIPTIONS: PlanCard[] = [
  {
    id: 'pro_monthly',
    name: 'Pro Course',
    emoji: '🎓',
    price: '£9/mo',
    description: 'Full course access, updates, community. Cancel any time.',
  },
  {
    id: 'hyper_monthly',
    name: 'Hyper Elite',
    emoji: '🦅',
    price: '£29/mo',
    description: 'Everything in Pro + live sessions, priority support, early access.',
    highlight: true,
    badge: 'Best Value',
  },
]

// ── API helper ────────────────────────────────────────────────────────────────

function getApiBase(): string {
  if (typeof window === 'undefined') return 'http://localhost:8000'
  const host = process.env.NEXT_PUBLIC_CORE_WS_HOST ?? window.location.hostname
  const port = process.env.NEXT_PUBLIC_CORE_WS_PORT ?? '8000'
  return `http://${host}:${port}`
}

// ── Card component ────────────────────────────────────────────────────────────

function PriceCard({
  plan,
  loading,
  onBuy,
}: {
  plan: PlanCard
  loading: boolean
  onBuy: (id: string) => void
}): React.JSX.Element {
  return (
    <div
      style={{
        position: 'relative',
        background: plan.highlight ? 'rgba(99,102,241,0.12)' : 'rgba(255,255,255,0.03)',
        border: `1px solid ${plan.highlight ? 'var(--accent-cyan)' : 'var(--pane-border)'}`,
        borderRadius: 10,
        padding: '20px 18px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        transition: 'border-color 0.15s',
      }}
    >
      {plan.badge && (
        <span
          style={{
            position: 'absolute',
            top: -11,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'var(--accent-cyan)',
            color: '#fff',
            fontSize: 10,
            fontWeight: 700,
            padding: '2px 10px',
            borderRadius: 20,
            whiteSpace: 'nowrap',
            letterSpacing: '0.05em',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {plan.badge}
        </span>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 22 }}>{plan.emoji}</span>
        <span
          style={{
            fontSize: 14,
            fontWeight: 700,
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-primary)',
          }}
        >
          {plan.name}
        </span>
      </div>

      <div
        style={{
          fontSize: 26,
          fontWeight: 800,
          color: plan.highlight ? 'var(--accent-cyan)' : 'var(--text-primary)',
          fontFamily: 'var(--font-mono)',
          lineHeight: 1,
        }}
      >
        {plan.price}
        {plan.tokens && (
          <span
            style={{
              fontSize: 11,
              fontWeight: 500,
              color: 'var(--accent-amber)',
              marginLeft: 8,
              fontFamily: 'var(--font-mono)',
            }}
          >
            {plan.tokens} BROski$
          </span>
        )}
      </div>

      <p
        style={{
          fontSize: 12,
          color: 'var(--text-secondary)',
          margin: 0,
          lineHeight: 1.5,
          flexGrow: 1,
        }}
      >
        {plan.description}
      </p>

      <button
        onClick={() => onBuy(plan.id)}
        disabled={loading}
        style={{
          marginTop: 4,
          padding: '9px 0',
          borderRadius: 6,
          border: 'none',
          background: plan.highlight
            ? 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))'
            : 'rgba(99,102,241,0.25)',
          color: '#fff',
          fontWeight: 700,
          fontSize: 13,
          cursor: loading ? 'not-allowed' : 'pointer',
          fontFamily: 'var(--font-mono)',
          opacity: loading ? 0.6 : 1,
          transition: 'opacity 0.15s',
        }}
        aria-label={`Buy ${plan.name}`}
      >
        {loading ? 'Loading…' : plan.tokens ? `Get ${plan.tokens} BROski$` : 'Subscribe'}
      </button>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PricingPage(): React.JSX.Element {
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleBuy = async (priceId: string) => {
    setLoadingId(priceId)
    setError(null)
    try {
      const res = await fetch(`${getApiBase()}/api/stripe/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ price_id: priceId }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? `Request failed (${res.status})`)
      }
      const { checkout_url } = await res.json()
      window.location.href = checkout_url
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Checkout failed — try again.')
      setLoadingId(null)
    }
  }

  return (
    <div
      style={{
        maxWidth: 900,
        margin: '0 auto',
        padding: '28px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: 32,
      }}
    >
      {/* Header */}
      <div style={{ textAlign: 'center' }}>
        <h1
          style={{
            fontSize: 28,
            fontWeight: 800,
            color: 'var(--text-primary)',
            margin: '0 0 8px',
            fontFamily: 'var(--font-primary)',
          }}
        >
          💳 BROski Plans
        </h1>
        <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: 14 }}>
          Token packs for the shop · Course subscriptions · Built for ADHD brains 🧠
        </p>
      </div>

      {/* Token Packs */}
      <section>
        <h2
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: 'var(--text-secondary)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            margin: '0 0 14px',
            fontFamily: 'var(--font-mono)',
          }}
        >
          🪙 Token Packs — one-time
        </h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 16,
          }}
        >
          {TOKEN_PACKS.map((plan) => (
            <PriceCard
              key={plan.id}
              plan={plan}
              loading={loadingId === plan.id}
              onBuy={handleBuy}
            />
          ))}
        </div>
      </section>

      {/* Subscriptions */}
      <section>
        <h2
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: 'var(--text-secondary)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            margin: '0 0 14px',
            fontFamily: 'var(--font-mono)',
          }}
        >
          🎓 Course Subscriptions — recurring
        </h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: 16,
          }}
        >
          {SUBSCRIPTIONS.map((plan) => (
            <PriceCard
              key={plan.id}
              plan={plan}
              loading={loadingId === plan.id}
              onBuy={handleBuy}
            />
          ))}
        </div>
      </section>

      {/* Error */}
      {error && (
        <div
          role="alert"
          style={{
            background: 'rgba(255,68,102,0.08)',
            border: '1px solid rgba(255,68,102,0.4)',
            borderRadius: 6,
            padding: '10px 14px',
            fontSize: 13,
            color: 'var(--accent-red)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          ⚠️ {error}
        </div>
      )}

      {/* Footer note */}
      <p
        style={{
          fontSize: 11,
          color: 'var(--text-secondary)',
          textAlign: 'center',
          margin: 0,
        }}
      >
        Secure checkout powered by Stripe · Prices in GBP · Cancel subscriptions any time
      </p>
    </div>
  )
}
