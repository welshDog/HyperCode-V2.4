'use client'

/**
 * Task 11 — FocusToggle component
 * A button that toggles focusMode in the Zustand UI store.
 * When focusMode is active, the button glows and the label changes.
 * Consumers can check `useUiStore((s) => s.focusMode)` to conditionally
 * hide non-essential panels.
 */

import { useUiStore } from '@/store/useUiStore'

export function FocusToggle() {
  const focusMode     = useUiStore((s) => s.focusMode)
  const toggleFocus   = useUiStore((s) => s.toggleFocusMode)

  return (
    <button
      onClick={toggleFocus}
      title={focusMode ? 'Exit focus mode' : 'Enter focus mode — hide non-essential panels'}
      aria-pressed={focusMode}
      style={{
        display:         'inline-flex',
        alignItems:      'center',
        gap:             '0.4rem',
        padding:         '0.35rem 0.75rem',
        borderRadius:    '9999px',
        border:          `1px solid ${focusMode ? 'var(--accent-cyan, #06b6d4)' : 'var(--border-subtle, #334155)'}`,
        background:      focusMode ? 'rgba(6,182,212,0.12)' : 'transparent',
        color:           focusMode ? 'var(--accent-cyan, #06b6d4)' : 'var(--text-secondary, #94a3b8)',
        fontSize:        '0.75rem',
        fontWeight:      500,
        cursor:          'pointer',
        transition:      'all 0.2s ease',
        boxShadow:       focusMode ? '0 0 8px rgba(6,182,212,0.35)' : 'none',
        letterSpacing:   '0.03em',
        whiteSpace:      'nowrap',
      }}
    >
      <span aria-hidden style={{ fontSize: '0.85rem' }}>
        {focusMode ? '⚡' : '◎'}
      </span>
      {focusMode ? 'Focus: ON' : 'Focus mode'}
    </button>
  )
}
