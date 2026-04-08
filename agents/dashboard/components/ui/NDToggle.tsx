'use client'

import React from 'react'

const ND_MODES = [
  { id: 'default',       label: '\uD83E\uDDE0 Default' },
  { id: 'dyslexia',      label: '\uD83D\uDCC4 Dyslexia' },
  { id: 'high-contrast', label: '\u26AA High-C' },
  { id: 'focus',         label: '\uD83D\uDD15 Focus' },
]

export function NDToggle({
  value,
  onChange,
}: {
  value: string
  onChange: (mode: string) => void
}): React.JSX.Element {
  return (
    <div style={{ display: 'flex', gap: 4 }} role="group" aria-label="Neurodivergent mode">
      {ND_MODES.map((m) => (
        <button
          key={m.id}
          className={`btn${value === m.id ? ' active' : ''}`}
          onClick={() => onChange(m.id)}
          aria-pressed={value === m.id}
          title={m.label}
        >
          {m.label}
        </button>
      ))}
    </div>
  )
}
