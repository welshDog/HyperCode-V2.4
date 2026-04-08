'use client'

import React from 'react'

export type ViewMode = 'grid' | 'focus' | 'presentation'

const MODES: { id: ViewMode; label: string }[] = [
  { id: 'grid',         label: '\uD83D\uDD33 Grid' },
  { id: 'focus',        label: '\uD83C\uDFAF Focus' },
  { id: 'presentation', label: '\uD83D\uDCFA Present' },
]

export function ViewModeToggle({
  value,
  onChange,
}: {
  value: ViewMode
  onChange: (mode: ViewMode) => void
}): React.JSX.Element {
  return (
    <div style={{ display: 'flex', gap: 4 }} role="group" aria-label="View mode">
      {MODES.map((m) => (
        <button
          key={m.id}
          className={`btn${value === m.id ? ' active' : ''}`}
          onClick={() => onChange(m.id)}
          aria-pressed={value === m.id}
        >
          {m.label}
        </button>
      ))}
    </div>
  )
}
