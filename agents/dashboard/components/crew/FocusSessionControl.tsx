'use client'

import React, { useEffect, useState, useSyncExternalStore } from 'react'
import { useToast } from '@/components/ui/ToastProvider'
import {
  CHUNK_OPTIONS, endFocus, getServerSnapshot, getSnapshot, remainingSeconds, setMinutes, startFocus, subscribe,
  type ChunkMinutes,
} from '@/lib/focus/store'

function mmss(total: number): string {
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// A suggestion, not a rule: the time running out changes one line of text. It never ends the session,
// plays a sound or opens anything.
export function FocusSessionControl(): React.JSX.Element {
  const focus = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
  const [now, setNow] = useState<number>(() => Date.now())
  const { history } = useToast()

  useEffect(() => {
    if (!focus.active) return
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [focus.active])

  if (!focus.active) {
    return (
      <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
        <select
          aria-label="Focus chunk length"
          className="skill-finder-input"
          style={{ flex: 'none', width: 'auto' }}
          value={focus.minutes}
          onChange={(e) => setMinutes(Number(e.target.value) as ChunkMinutes)}
        >
          {CHUNK_OPTIONS.map((m) => (
            <option key={m} value={m}>{m} min</option>
          ))}
        </select>
        <button type="button" className="btn" onClick={() => startFocus()} title="Start one quiet chunk of work">
          Start focus
        </button>
      </span>
    )
  }

  // `now` can predate a session that has just started; never count down from before its start.
  const left = remainingSeconds(focus, Math.max(now, focus.startedAt ?? 0))
  const waiting = history.filter((h) => focus.startedAt !== null && h.createdAt >= focus.startedAt).length
  return (
    <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }} data-testid="focus-active">
      <span role="timer" aria-label="Focus time left">
        {left > 0 ? `Focus: ${mmss(left)} left` : 'Chunk done. Break when you are ready.'}
      </span>
      {waiting > 0 && <span data-testid="focus-waiting">{waiting} waiting in the bell</span>}
      <button type="button" className="btn active" onClick={endFocus}>End focus</button>
    </span>
  )
}
