'use client'

import React, { useEffect, useSyncExternalStore } from 'react'
import { STATUS } from '@/components/crew/CalmCardPanel'
import { getServerSnapshot, getSnapshot, loadMorning, subscribe, type Light } from '@/lib/morning/store'

// "Where was I?": one Calm Card from what the crew already knows. Quiet days read as fine.
// The traffic light is a word and a symbol, never colour alone.
const LIGHT: Record<Light, { glyph: string; word: string }> = {
  green: { glyph: '●', word: 'Green: plenty of room' },
  amber: { glyph: '◐', word: 'Amber: getting tight' },
  red: { glyph: '○', word: 'Red: low on memory' },
}

export function MorningCard(): React.JSX.Element {
  const s = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
  useEffect(() => {
    void loadMorning()
  }, [])
  const chip = s.card ? STATUS[s.card.status] : null
  return (
    <div className="pane crew-morning-card" data-testid="morning-card">
      <div className="pane-header">
        <span className="pane-title">Where was I?</span>
      </div>
      <div className="pane-body">
        {s.phase === 'error' && (
          <p role="status">Can&apos;t reach the crew right now, so there is nothing to show yet.</p>
        )}
        {(s.phase === 'idle' || (s.phase === 'loading' && !s.card)) && <p role="status">Loading…</p>}
        {s.card && chip && (
          <div role="region" aria-label="Morning summary">
            <p data-testid="morning-status" style={{ color: chip.color, fontWeight: 600, margin: '0 0 8px' }}>
              <span aria-hidden>{chip.glyph}</span> {chip.word}
            </p>
            <ul data-testid="morning-tldr" style={{ margin: '0 0 12px', paddingLeft: 18 }}>
              {s.card.tldr.map((line, i) => (
                <li key={`${i}-${line}`}>{line}</li>
              ))}
            </ul>
            {s.light && (
              <p data-testid="morning-light" style={{ margin: '0 0 12px' }}>
                <span aria-hidden>{LIGHT[s.light].glyph}</span> {LIGHT[s.light].word}
              </p>
            )}
            <p
              data-testid="morning-next"
              style={{ border: '1px solid var(--accent-purple)', borderRadius: 8, padding: '10px 12px', margin: '0 0 12px', fontWeight: 600 }}
            >
              Next: {s.card.next_action}
            </p>
            {s.card.details.length > 0 && (
              <details data-testid="morning-details">
                <summary>More detail</summary>
                <ul style={{ paddingLeft: 18 }}>
                  {s.card.details.map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
        <button type="button" className="btn" onClick={() => void loadMorning()} disabled={s.phase === 'loading'}>
          Refresh
        </button>
      </div>
    </div>
  )
}
