'use client'

import React, { useEffect, useSyncExternalStore } from 'react'
import {
  dismissMessage, getServerSnapshot, getSnapshot, loadHeld, panic, resume, subscribe,
} from '@/lib/panic/store'

// Always visible, one click, no confirmation dialog. Literal label; the state is said in words.
export function PanicButton(): React.JSX.Element {
  const s = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
  useEffect(() => {
    void loadHeld()
  }, [])
  const held = s.held.length > 0
  return held ? (
    <button type="button" className="btn active" onClick={() => void resume()} disabled={s.phase === 'working'}
      title="Everything is paused. Resume carries on from where it stopped.">
      Paused ({s.held.length}) · Resume
    </button>
  ) : (
    <button type="button" className="btn" onClick={() => void panic()} disabled={s.phase === 'working'}
      title="Pause everything now. Nothing is lost.">
      Pause everything
    </button>
  )
}

// The calm confirmation line: says exactly what happened, and what is waiting for you.
export function PanicNotice(): React.JSX.Element | null {
  const s = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
  if (!s.message && s.held.length === 0) return null
  return (
    <div role="status" aria-live="polite" data-testid="panic-notice" className="panic-notice">
      {s.message && (
        <p>
          {s.message}{' '}
          <button type="button" className="btn" onClick={dismissMessage}>OK</button>
        </p>
      )}
      {s.held.length > 0 && (
        <ul data-testid="panic-held" style={{ paddingLeft: 18 }}>
          {s.held.map((h) => (
            <li key={h.taskId}>
              Where you were: {h.card?.tldr?.length ? h.card.tldr[h.card.tldr.length - 1] : 'a run'}
              {h.card?.next_action ? ` — next: ${h.card.next_action}` : ''}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
