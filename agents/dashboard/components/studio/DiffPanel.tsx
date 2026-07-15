'use client'

import React, { useMemo } from 'react'
import type { StudioStatus } from '@/hooks/useStudioSession'

function lineColor(line: string): string {
  if (line.startsWith('+') && !line.startsWith('+++')) return 'var(--accent-green)'
  if (line.startsWith('-') && !line.startsWith('---')) return 'var(--accent-red)'
  if (line.startsWith('@@')) return 'var(--accent-cyan)'
  if (line.startsWith('diff ') || line.startsWith('index ') || line.startsWith('+++') || line.startsWith('---')) {
    return 'var(--text-secondary)'
  }
  return 'var(--text-primary)'
}

interface DiffPanelProps {
  diff: string
  status: StudioStatus
  mergeSha: string | null
  onMerge: () => void
  onDiscard: () => void
  busy: boolean
}

export function DiffPanel({ diff, status, mergeSha, onMerge, onDiscard, busy }: DiffPanelProps): React.JSX.Element {
  // preview→confirm: a change can only land while it's sitting in review.
  const canDecide = status === 'review' && diff.trim().length > 0
  const lines = useMemo(() => diff.split('\n'), [diff])
  const stat = useMemo(() => {
    let added = 0
    let removed = 0
    for (const l of lines) {
      if (l.startsWith('+') && !l.startsWith('+++')) added++
      else if (l.startsWith('-') && !l.startsWith('---')) removed++
    }
    return { added, removed }
  }, [lines])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 8 }}>
      {status === 'merged' && (
        <div className="studio-banner" style={{ borderColor: 'rgba(0,255,136,0.35)', background: 'rgba(0,255,136,0.08)' }}>
          <span style={{ color: 'var(--accent-green)' }}>✓ Merged</span>
          {mergeSha && <code style={{ color: 'var(--text-secondary)', marginLeft: 8 }}>{mergeSha.slice(0, 10)}</code>}
        </div>
      )}
      {status === 'discarded' && (
        <div className="studio-banner" style={{ borderColor: 'rgba(136,153,170,0.3)', background: 'rgba(255,255,255,0.03)' }}>
          <span style={{ color: 'var(--text-secondary)' }}>Discarded — nothing was written.</span>
        </div>
      )}

      <div
        style={{
          flex: 1,
          overflow: 'auto',
          background: 'rgba(0,0,0,0.35)',
          border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: 6,
          padding: '10px 12px',
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
          lineHeight: 1.6,
        }}
      >
        {diff.trim().length === 0 ? (
          <div style={{ color: 'var(--text-secondary)', opacity: 0.6 }}>
            No diff yet. It appears when the agent finishes and the run is ready to review.
          </div>
        ) : (
          <pre style={{ margin: 0, whiteSpace: 'pre' }}>
            {lines.map((line, i) => (
              <div key={i} style={{ color: lineColor(line) }}>{line || ' '}</div>
            ))}
          </pre>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {(stat.added > 0 || stat.removed > 0) && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>
            <span style={{ color: 'var(--accent-green)' }}>+{stat.added}</span>{' '}
            <span style={{ color: 'var(--accent-red)' }}>−{stat.removed}</span>
          </span>
        )}
        <div style={{ flex: 1 }} />
        <button
          className="btn"
          type="button"
          onClick={onDiscard}
          disabled={busy || status === 'merged' || status === 'discarded'}
          title="Throw the worktree away — nothing lands"
        >
          Discard
        </button>
        <button
          className="btn studio-merge"
          type="button"
          onClick={onMerge}
          disabled={!canDecide || busy}
          title={canDecide ? 'Land this change on the branch' : 'Merge unlocks once the agent is done'}
        >
          {busy ? 'Merging…' : 'Merge'}
        </button>
      </div>
    </div>
  )
}
