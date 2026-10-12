'use client'

import React, { useState } from 'react'
import { useCrewRun } from '@/hooks/useCrewRun'
import type { CardStatus } from '@/lib/agui/types'

// Calm Card: at most five summary lines, exactly ONE next action, details collapsed.
// Status is always icon + word (never colour alone). No motion, no popups.
export const STATUS: Record<CardStatus, { glyph: string; word: string; color: string }> = {
  running: { glyph: '…', word: 'Running', color: 'var(--accent-cyan)' },
  waiting_on_you: { glyph: '!', word: 'Waiting on you', color: 'var(--accent-amber)' },
  paused: { glyph: '‖', word: 'Paused', color: 'var(--text-secondary)' },
  blocked: { glyph: '✕', word: 'Blocked', color: 'var(--accent-red)' },
  done: { glyph: '✓', word: 'Done', color: 'var(--accent-green)' },
}

function readAloud(text: string): void {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(text))
}

export function CalmCardPanel(): React.JSX.Element {
  const [draft, setDraft] = useState('')
  const [taskId, setTaskId] = useState<string | null>(null)
  const { run, connection } = useCrewRun(taskId)
  const card = run.calmCard
  const chip = card ? STATUS[card.status] : null

  return (
    <div className="pane crew-calm-card">
      <div className="pane-header">
        <span className="pane-title">Crew run</span>
      </div>
      <div className="pane-body">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            setTaskId(draft.trim() || null)
          }}
          style={{ display: 'flex', gap: 8, marginBottom: 12 }}
        >
          <input
            aria-label="Crew task id"
            className="skill-finder-input"
            type="text"
            placeholder="Paste a crew task id"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <button type="submit" className="btn">Show</button>
        </form>

        {taskId && !card && (
          <p role="status" style={{ color: 'var(--text-secondary)' }}>
            {connection === 'retrying' ? "Can't reach the crew right now. Trying again…" : 'Loading…'}
          </p>
        )}

        {card && chip && (
          <div role="region" aria-label="Crew run summary" aria-live="polite">
            <p data-testid="calm-status" style={{ color: chip.color, fontWeight: 600, margin: '0 0 8px' }}>
              <span aria-hidden>{chip.glyph}</span> {chip.word}
            </p>
            <ul data-testid="calm-tldr" style={{ margin: '0 0 12px', paddingLeft: 18 }}>
              {card.tldr.map((line, i) => (
                <li key={`${i}-${line}`}>{line}</li>
              ))}
            </ul>
            <p
              data-testid="calm-next"
              style={{ border: '1px solid var(--accent-purple)', borderRadius: 8, padding: '10px 12px', margin: '0 0 12px', fontWeight: 600 }}
            >
              Next: {card.next_action}
            </p>
            {card.details.length > 0 && (
              <details data-testid="calm-details">
                <summary>More detail</summary>
                <ul style={{ paddingLeft: 18 }}>
                  {card.details.map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
              </details>
            )}
            <button type="button" className="btn" onClick={() => readAloud(card.plain_text)}>
              Read it to me
            </button>
            {connection === 'retrying' && (
              <p role="status" style={{ color: 'var(--text-secondary)', marginTop: 8 }}>
                Connection lost. Showing the last update. Trying again…
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
