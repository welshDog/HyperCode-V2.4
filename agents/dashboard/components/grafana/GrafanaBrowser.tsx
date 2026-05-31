'use client'

import React, { useMemo, useState } from 'react'

type GrafanaView = 'launchpad' | 'dashboards' | 'explore' | 'alerting' | 'custom'

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
            Pop out
          </a>
        </div>
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

