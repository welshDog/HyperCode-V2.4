'use client'

import React from 'react'
import { useSensory } from './SensoryProvider'
import { isCalm } from '@/lib/sensory/settings'

// One switch. Literal label, state in words (not colour alone), no confirmation dialog.
export function CalmModeToggle(): React.JSX.Element {
  const { settings, toggleCalmMode } = useSensory()
  const on = isCalm(settings)
  return (
    <button
      type="button"
      className={`btn${on ? ' active' : ''}`}
      aria-pressed={on}
      onClick={toggleCalmMode}
      title="Calm mode: less motion, one thing at a time"
    >
      Calm mode: {on ? 'On' : 'Off'}
    </button>
  )
}
