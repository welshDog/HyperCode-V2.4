'use client'

/**
 * PricingCard — reusable plan card for the Pricing page.
 * Handles click → POST /api/stripe/checkout → redirect.
 * Phase 10H | HyperCode V2.4 | BROski♾
 */

import React from 'react'

export type PricingCardProps = {
  /** Friendly plan name, e.g. "Builder Pack" */
  name: string
  /** Display price string, e.g. "£15" or "£9/mo" */
  price: string
  /** BROski$ token amount (token packs only) */
  tokens?: number
  /** Bullet-point feature list */
  features: string[]
  /** Price key sent to /api/stripe/checkout as price_id */
  priceKey: string
  /** CTA button label */
  ctaLabel: string
  /** Highlight with accent border + gradient button */
  highlight?: boolean
  /** Badge text rendered above the card, e.g. "Most Popular" */
  badge?: string
  /** True while this card's fetch is in flight */
  loading?: boolean
  /** Error message scoped to this card (optional — page can also show global error) */
  error?: string
  /** Called when the CTA is clicked */
  onClick: (priceKey: string) => void
}

export function PricingCard({
  name,
  price,
  tokens,
  features,
  priceKey,
  ctaLabel,
  highlight = false,
  badge,
  loading = false,
  error,
  onClick,
}: PricingCardProps): React.JSX.Element {
  return (
    <div
      style={{
        position:        'relative',
        background:      highlight ? 'rgba(99,102,241,0.10)' : 'rgba(255,255,255,0.03)',
        border:          `1px solid ${highlight ? 'var(--accent-cyan)' : 'var(--pane-border)'}`,
        borderRadius:    10,
        padding:         '22px 18px 18px',
        display:         'flex',
        flexDirection:   'column',
        gap:             10,
        transition:      'border-color 0.15s, box-shadow 0.15s',
        boxShadow:       highlight ? '0 0 18px rgba(99,102,241,0.15)' : 'none',
      }}
    >
      {/* ── Badge ─────────────────────────────────────── */}
      {badge && (
        <span
          aria-label={badge}
          style={{
            position:    'absolute',
            top:         -12,
            left:        '50%',
            transform:   'translateX(-50%)',
            background:  'linear-gradient(90deg, var(--accent-cyan), var(--accent-purple))',
            color:       '#fff',
            fontSize:    10,
            fontWeight:  700,
            padding:     '3px 12px',
            borderRadius: 20,
            whiteSpace:  'nowrap',
            letterSpacing: '0.06em',
            fontFamily:  'var(--font-mono)',
          }}
        >
          {badge}
        </span>
      )}

      {/* ── Name ──────────────────────────────────────── */}
      <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)', fontFamily: 'var(--font-primary)' }}>
        {name}
      </div>

      {/* ── Price ─────────────────────────────────────── */}
      <div style={{ lineHeight: 1 }}>
        <span
          style={{
            fontSize:   30,
            fontWeight: 800,
            color:      highlight ? 'var(--accent-cyan)' : 'var(--text-primary)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {price}
        </span>
        {tokens != null && (
          <span
            style={{
              marginLeft:  8,
              fontSize:    12,
              fontWeight:  600,
              color:       'var(--accent-amber)',
              fontFamily:  'var(--font-mono)',
            }}
          >
            {tokens.toLocaleString()} BROski$
          </span>
        )}
      </div>

      {/* ── Features ──────────────────────────────────── */}
      <ul
        style={{
          margin:     '2px 0 0',
          padding:    0,
          listStyle:  'none',
          display:    'flex',
          flexDirection: 'column',
          gap:        5,
          flexGrow:   1,
        }}
      >
        {features.map((f) => (
          <li
            key={f}
            style={{
              display:    'flex',
              alignItems: 'flex-start',
              gap:        6,
              fontSize:   12,
              color:      'var(--text-secondary)',
              lineHeight: 1.4,
            }}
          >
            <span style={{ color: 'var(--accent-green)', flexShrink: 0, marginTop: 1 }}>✓</span>
            {f}
          </li>
        ))}
      </ul>

      {/* ── CTA button ────────────────────────────────── */}
      <button
        onClick={() => onClick(priceKey)}
        disabled={loading}
        aria-label={loading ? `Loading ${name}…` : ctaLabel}
        aria-busy={loading}
        style={{
          marginTop:    6,
          padding:      '10px 0',
          borderRadius: 6,
          border:       'none',
          background:   highlight
            ? 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))'
            : 'rgba(99,102,241,0.28)',
          color:        '#fff',
          fontWeight:   700,
          fontSize:     13,
          cursor:       loading ? 'not-allowed' : 'pointer',
          fontFamily:   'var(--font-mono)',
          opacity:      loading ? 0.65 : 1,
          transition:   'opacity 0.15s',
          width:        '100%',
        }}
      >
        {loading ? 'Loading…' : ctaLabel}
      </button>

      {/* ── Card-scoped error ─────────────────────────── */}
      {error && (
        <p
          role="alert"
          style={{
            margin:     0,
            fontSize:   11,
            color:      'var(--accent-red)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          ⚠️ {error}
        </p>
      )}
    </div>
  )
}
