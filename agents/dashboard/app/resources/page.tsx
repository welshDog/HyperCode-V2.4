'use client'

import React, { useEffect, useState } from 'react'
import {
  RAM_AMBER_MB,
  RAM_RED_MB,
  type ContainerRow,
  type RamVerdict,
  type ResourceSnapshot,
  type Severity,
} from '@/lib/resourceSnapshot'

const POLL_MS = 10_000

const VERDICT_COLOR: Record<RamVerdict, string> = {
  GREEN: 'var(--status-healthy)',
  AMBER: 'var(--status-warning)',
  RED: 'var(--status-error)',
  UNKNOWN: 'var(--status-idle)',
}
const VERDICT_TEXT: Record<RamVerdict, string> = {
  GREEN: 'GREEN · safe to build',
  AMBER: 'AMBER · no builds, start nothing big',
  RED: 'RED · stop things now',
  UNKNOWN: 'UNKNOWN · WSL not readable',
}
const SEVERITY_COLOR: Record<Severity, string> = {
  ok: 'var(--status-healthy)',
  warn: 'var(--status-warning)',
  crit: 'var(--status-error)',
  unbounded: 'var(--accent-cyan)',
}
const SEVERITY_LABEL: Record<Severity, string> = {
  ok: 'ok',
  warn: 'high',
  crit: 'critical',
  unbounded: 'no limit',
}

const fmtMb = (n: number): string => `${n.toLocaleString('en-GB', { maximumFractionDigits: 1 })} MB`

function WslGauge({ wsl }: { wsl: NonNullable<Extract<ResourceSnapshot, { available: true }>['wsl']> }) {
  const scale = Math.max(2000, wsl.availableMb)
  const pos = (mb: number): string => `${Math.min(100, (mb / scale) * 100)}%`
  const color = VERDICT_COLOR[wsl.verdict]
  return (
    <section className="pane" aria-label="WSL memory">
      <header className="pane-header">
        <h2>🧠 WSL memory · the number that decides everything</h2>
        <span className="tag" style={{ color, borderColor: color }}>{VERDICT_TEXT[wsl.verdict]}</span>
      </header>
      <div className="pane-body" style={{ display: 'grid', gap: 10 }}>
        <p style={{ fontSize: 'clamp(2rem, 6vw, 3.4rem)', fontWeight: 800, lineHeight: 1.1, color, margin: 0 }}>
          {wsl.availableMb.toLocaleString('en-GB')} MB <span style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>available of {wsl.totalMb.toLocaleString('en-GB')} MB</span>
        </p>
        <div
          role="meter"
          aria-label="WSL available memory"
          aria-valuemin={0}
          aria-valuemax={scale}
          aria-valuenow={wsl.availableMb}
          aria-valuetext={`${wsl.availableMb} megabytes available, ${wsl.verdict}`}
          style={{ position: 'relative', height: 18, borderRadius: 9, background: 'var(--pane-header)', border: '1px solid var(--pane-border)', overflow: 'hidden' }}
        >
          <div style={{ width: pos(wsl.availableMb), height: '100%', background: color, transition: 'width var(--transition-med)' }} />
          <span aria-hidden style={{ position: 'absolute', left: pos(RAM_RED_MB), top: 0, bottom: 0, width: 2, background: 'var(--status-error)' }} />
          <span aria-hidden style={{ position: 'absolute', left: pos(RAM_AMBER_MB), top: 0, bottom: 0, width: 2, background: 'var(--status-warning)' }} />
        </div>
        <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Red line {RAM_RED_MB.toLocaleString('en-GB')} MB (stop) · amber line {RAM_AMBER_MB.toLocaleString('en-GB')} MB (builds need above this) · swap used {fmtMb(wsl.swapUsedMb)}
        </p>
      </div>
    </section>
  )
}

function ContainerBar({ row, maxMb }: { row: ContainerRow; maxMb: number }) {
  const color = SEVERITY_COLOR[row.severity]
  const width = maxMb > 0 ? Math.max(1, (row.workingSetMb / maxMb) * 100) : 0
  return (
    <li style={{ display: 'grid', gridTemplateColumns: 'minmax(120px, 220px) 1fr minmax(150px, auto)', gap: 12, alignItems: 'center', padding: '4px 0' }}>
      <span style={{ fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={row.name}>{row.name}</span>
      <div aria-hidden style={{ height: 12, borderRadius: 6, background: 'var(--pane-header)' }}>
        <div style={{ width: `${width}%`, height: '100%', borderRadius: 6, background: color }} />
      </div>
      <span style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
        {fmtMb(row.workingSetMb)}
        {row.limitMb ? ` / ${fmtMb(row.limitMb)}` : ''}
        {' · '}
        <strong style={{ color }}>{row.pctOfLimit !== null ? `${row.pctOfLimit}% ` : ''}{SEVERITY_LABEL[row.severity]}</strong>
      </span>
    </li>
  )
}

export default function ResourcesPage(): React.JSX.Element {
  const [snap, setSnap] = useState<ResourceSnapshot | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let alive = true
    const load = async (): Promise<void> => {
      try {
        const res = await fetch('/api/resources', { cache: 'no-store' })
        if (!res.ok) throw new Error(String(res.status))
        const body = (await res.json()) as ResourceSnapshot
        if (alive) {
          setSnap(body)
          setFailed(false)
        }
      } catch {
        if (alive) setFailed(true)
      }
    }
    void load()
    const timer = setInterval(() => void load(), POLL_MS)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])

  const maxMb = snap && snap.available ? Math.max(...snap.containers.map((c) => c.workingSetMb), 1) : 1

  return (
    <main className="hyper-shell" aria-labelledby="resources-title">
      <div style={{ gridArea: '1 / 1 / auto / -1', maxWidth: 1120, width: '100%', margin: '24px auto', display: 'grid', gap: 18 }}>
        <header>
          <h1 id="resources-title">📊 Stack Resources · Memory Map</h1>
          <p>Live per-container memory from Prometheus. Refreshes every {POLL_MS / 1000} seconds. Read-only.</p>
        </header>

        {failed && (
          <div role="alert" className="pane" style={{ padding: 14, borderColor: 'var(--status-error)' }}>
            Could not reach the dashboard API. Showing the last data we had{snap ? '' : ' (none yet)'}.
          </div>
        )}

        {!snap && !failed && <p role="status">Loading the memory map…</p>}

        {snap && !snap.available && (
          <div role="status" className="pane" style={{ padding: 14, borderColor: 'var(--status-warning)' }}>
            <strong>No data right now.</strong> {snap.reason}
          </div>
        )}

        {snap && snap.available && (
          <>
            {snap.wsl ? (
              <WslGauge wsl={snap.wsl} />
            ) : (
              <div role="status" className="pane" style={{ padding: 14 }}>WSL memory is not being reported (node-exporter down?).</div>
            )}

            <section className="pane" aria-label="Containers">
              <header className="pane-header">
                <h2>🐳 {snap.totals.count} containers · {fmtMb(snap.totals.workingSetMb)} in use</h2>
                <span className="tag" style={snap.totals.nearLimit ? { color: 'var(--status-warning)', borderColor: 'var(--status-warning)' } : undefined}>
                  {snap.totals.nearLimit === 0 ? 'none near their limit' : `${snap.totals.nearLimit} near their limit`}
                </span>
              </header>
              <ul className="pane-body" style={{ listStyle: 'none', margin: 0 }}>
                {snap.containers.map((row) => (
                  <ContainerBar key={row.name} row={row} maxMb={maxMb} />
                ))}
              </ul>
            </section>

            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Updated {new Date(snap.collectedAt).toLocaleTimeString('en-GB')}</p>
          </>
        )}
      </div>
    </main>
  )
}
