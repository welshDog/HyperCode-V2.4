'use client'

import React, { useMemo, useState } from 'react'

type GrafanaView = 'launchpad' | 'dashboards' | 'explore' | 'alerting' | 'custom'

// Pinned boards — the ones worth one click, each with a "reach for this when…"
// line. UIDs match monitoring/grafana/provisioning/dashboards/*.json.
const PINNED: { uid: string; name: string; when: string }[] = [
  { uid: 'hypercode-ecosystem-launchpad', name: 'Ecosystem Launchpad', when: 'first look — is the whole stack alive?' },
  { uid: 'hypercode-mission-control', name: 'Mission Control v2.4', when: 'a mission is running and you want the at-a-glance' },
  { uid: 'safety-shepherd', name: 'Safety Shepherd', when: 'an allow/escalate/block decision needs explaining' },
  { uid: 'hyperswarm-hud', name: 'HyperSwarm HUD', when: 'watching the agent swarm work in real time' },
  { uid: 'broski-agents', name: 'BROski Agent Intelligence', when: 'chasing a slow or hungry agent (CPU / mem / restarts)' },
  { uid: 'smoke-metrics', name: 'Crew Orchestrator', when: 'the orchestrator target looks down or flaky' },
]

function getGrafanaBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_GRAFANA_URL) return process.env.NEXT_PUBLIC_GRAFANA_URL
  if (typeof window !== 'undefined') {
    const host = window.location.hostname
    if (host === 'localhost' || host === '127.0.0.1') return `http://${host}:3001`
  }
  return 'http://127.0.0.1:3001'
}

function viewToPath(view: GrafanaView, customPath: string): string {
  if (view === 'launchpad') return '/d/hypercode-ecosystem-launchpad'
  if (view === 'dashboards') return '/dashboards'
  if (view === 'explore') return '/explore'
  if (view === 'alerting') return '/alerting/list'

  const trimmed = customPath.trim()
  if (!trimmed) return '/dashboards'
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) return trimmed
  if (!trimmed.startsWith('/')) return `/${trimmed}`
  return trimmed
}

export function GrafanaBrowser(): React.JSX.Element {
  const grafanaBaseUrl = useMemo(() => getGrafanaBaseUrl(), [])
  const [view, setView] = useState<GrafanaView>('launchpad')
  const [customPath, setCustomPath] = useState<string>('')

  const src = useMemo(() => {
    const pathOrUrl = viewToPath(view, customPath)
    if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) return pathOrUrl
    return `${grafanaBaseUrl}${pathOrUrl}`
  }, [grafanaBaseUrl, view, customPath])

  const goTo = (path: string) => {
    setCustomPath(path)
    setView('custom')
  }
  const activePath = viewToPath(view, customPath)

  return (
    <div className="pane" style={{ height: '100%' }}>
      <div className="pane-header" style={{ gap: 10, alignItems: 'center' }}>
        <div className="pane-title">📈 Grafana</div>
        <div style={{ display: 'inline-flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn" onClick={() => setView('launchpad')} aria-pressed={view === 'launchpad'}>
            Launchpad
          </button>
          <button className="btn" onClick={() => setView('dashboards')} aria-pressed={view === 'dashboards'}>
            Dashboards
          </button>
          <button className="btn" onClick={() => setView('explore')} aria-pressed={view === 'explore'}>
            Explore
          </button>
          <button className="btn" onClick={() => setView('alerting')} aria-pressed={view === 'alerting'}>
            Alerting
          </button>
        </div>
        <div style={{ marginLeft: 'auto', display: 'inline-flex', gap: 8, alignItems: 'center' }}>
          <label className="hc-mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
            Path
          </label>
          <input
            value={customPath}
            onChange={(e) => setCustomPath(e.target.value)}
            onFocus={() => setView('custom')}
            placeholder="/d/hypercode-mission-control"
            aria-label="Grafana path"
            style={{
              width: 280,
              maxWidth: '42vw',
              padding: '6px 10px',
              borderRadius: 8,
              border: '1px solid var(--pane-border)',
              background: 'rgba(255,255,255,0.03)',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
            }}
          />
          <a className="btn" href={src} target="_blank" rel="noreferrer">
            Pop out to :3001
          </a>
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          gap: 6,
          flexWrap: 'wrap',
          padding: '8px 12px',
          borderBottom: '1px solid var(--pane-border)',
        }}
      >
        {PINNED.map((b) => {
          const path = `/d/${b.uid}`
          const active = activePath === path
          return (
            <button
              key={b.uid}
              className="btn"
              onClick={() => goTo(path)}
              aria-pressed={active}
              title={`Use this when: ${b.when}`}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: 2,
                textAlign: 'left',
                maxWidth: 230,
                borderColor: active ? 'var(--accent-cyan)' : undefined,
              }}
            >
              <span style={{ fontSize: 11, fontWeight: 700 }}>{b.name}</span>
              <span style={{ fontSize: 9, opacity: 0.65, whiteSpace: 'normal', lineHeight: 1.3 }}>{b.when}</span>
            </button>
          )
        })}
      </div>

      <div style={{ height: '100%', overflow: 'hidden' }}>
        <iframe
          data-testid="grafana-iframe"
          title="Grafana"
          src={src}
          style={{ width: '100%', height: '100%', border: 0, display: 'block' }}
          allow="fullscreen"
        />
      </div>
    </div>
  )
}

