'use client'

import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { NDToggle } from '@/components/ui/NDToggle'
import { ViewModeToggle, type ViewMode } from '@/components/shell/ViewModeToggle'
import { ToastProvider, useToast } from '@/components/ui/ToastProvider'

type ShellContextValue = {
  ndMode: string
  setNdMode: (mode: string) => void
  viewMode: ViewMode
  setViewMode: (mode: ViewMode) => void
}

const ShellContext = createContext<ShellContextValue | null>(null)

export function useShellContext(): ShellContextValue {
  const ctx = useContext(ShellContext)
  if (!ctx) throw new Error('ShellContext missing')
  return ctx
}

const NAV_ITEMS: { href: string; label: string }[] = [
  { href: '/',        label: 'Hyper Station' },
  { href: '/ide',     label: 'IDE' },
  { href: '/agents',  label: 'Agents' },
  { href: '/mission', label: 'Mission' },
  { href: '/mcp',     label: 'MCP' },
  { href: '/docker-zone', label: 'Docker Zone' },
  { href: '/health',  label: 'Health' },
]

export function AppShell({ children }: { children: React.ReactNode }): React.JSX.Element {
  const pathname = usePathname()
  const [ndMode, setNdMode] = useState<string>('default')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')

  useEffect(() => {
    document.documentElement.setAttribute('data-nd-mode', ndMode)
  }, [ndMode])

  const ctx = useMemo(() => ({ ndMode, setNdMode, viewMode, setViewMode }), [ndMode, viewMode])

  return (
    <ShellContext.Provider value={ctx}>
      <ToastProvider>
        <AppShellInner
          pathname={pathname}
          ndMode={ndMode}
          setNdMode={setNdMode}
          viewMode={viewMode}
          setViewMode={setViewMode}
        >
          {children}
        </AppShellInner>
      </ToastProvider>
    </ShellContext.Provider>
  )
}

function BellIcon(): React.JSX.Element {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 1 0-14 0v5l-2 2v1h18v-1l-2-2Zm-2 1H7V11a5 5 0 1 1 10 0v6Z"
      />
    </svg>
  )
}

function formatWhen(ts: number): string {
  try {
    return new Date(ts).toLocaleString([], { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function AppShellInner({
  children,
  pathname,
  ndMode,
  setNdMode,
  viewMode,
  setViewMode,
}: {
  children: React.ReactNode
  pathname: string
  ndMode: string
  setNdMode: (mode: string) => void
  viewMode: ViewMode
  setViewMode: (mode: ViewMode) => void
}): React.JSX.Element {
  const { history, dismissHistory, clearHistory } = useToast()
  const [open, setOpen] = useState(false)
  const btnRef = useRef<HTMLButtonElement | null>(null)
  const panelRef = useRef<HTMLDivElement | null>(null)
  const closeRef = useRef<HTMLButtonElement | null>(null)

  const isMission = pathname === '/mission'
  
  // Track the most recent timestamp we have "seen"
  const [lastSeenTimestamp, setLastSeenTimestamp] = useState<number>(Date.now())
  
  // Unread = items added after our lastSeenTimestamp
  const unreadCount = history.filter(t => t.createdAt > lastSeenTimestamp).length

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    // When panel opens, we mark everything up to "now" as seen
    setLastSeenTimestamp(Date.now())
  }, [open])

  useEffect(() => {
    if (!open) return
    const onPointerDown = (e: PointerEvent) => {
      const target = e.target as Node | null
      if (!target) return
      if (panelRef.current?.contains(target)) return
      if (btnRef.current?.contains(target)) return
      setOpen(false)
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      e.preventDefault()
      setOpen(false)
      btnRef.current?.focus()
    }
    window.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div className="hc-app">
      <header className="hc-topbar">
        <div className="hc-topbar-left">
          <span className="hc-brand">
            <span className="hc-brand-mark">🦅</span>
            <span className="hc-brand-text">WelshDog HyperCode IDE</span>
          </span>
        </div>
        <div className="hc-topbar-right">
          <div className="hc-notify">
            <button
              ref={btnRef}
              className={`btn hc-notify-btn ${unreadCount > 0 ? 'has-unread' : ''}`}
              onClick={() => setOpen((v) => !v)}
              aria-label="Notification history"
              aria-haspopup="dialog"
              aria-expanded={open}
              title="Notifications"
            >
              <BellIcon />
              {unreadCount > 0 && <span className="hc-notify-badge" aria-label={`${unreadCount} unread notifications`}>{unreadCount > 9 ? '9+' : unreadCount}</span>}
            </button>
            {open && (
              <div ref={panelRef} className="pane hc-notify-panel" role="dialog" aria-label="Notification history">
                <div className="pane-header">
                  <span>Notifications</span>
                  <div style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                    <button
                      className="btn"
                      onClick={() => clearHistory()}
                      disabled={history.length === 0}
                      aria-disabled={history.length === 0}
                    >
                      Clear
                    </button>
                    <button
                      ref={closeRef}
                      className="hc-toast-close"
                      onClick={() => setOpen(false)}
                      aria-label="Close notification history"
                    >
                      ×
                    </button>
                  </div>
                </div>
                <div className="pane-body hc-notify-body">
                  {history.length === 0 ? (
                    <div className="hc-notify-empty">No notifications yet</div>
                  ) : (
                    <ul className="hc-notify-list" role="list">
                      {history.map((t) => {
                        const tagClass = t.variant === 'success' ? 'healthy' : t.variant === 'error' ? 'error' : 'idle'
                        return (
                          <li key={t.id} className="hc-notify-item">
                            <div className="hc-notify-meta">
                              <span className={`tag ${tagClass}`}>{t.variant}</span>
                              <span className="hc-notify-time">{formatWhen(t.createdAt)}</span>
                            </div>
                            <div className="hc-notify-main">
                              <div className="hc-notify-title">{t.title}</div>
                              {t.message && <div className="hc-notify-msg">{t.message}</div>}
                              <div className="hc-notify-actions">
                                {t.action && (
                                  <Link className="hc-toast-action" href={t.action.href} onClick={() => setOpen(false)}>
                                    {t.action.label}
                                  </Link>
                                )}
                                <button className="hc-toast-close" onClick={() => dismissHistory(t.id)} aria-label="Dismiss notification">
                                  ×
                                </button>
                              </div>
                            </div>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </div>
          <NDToggle value={ndMode} onChange={setNdMode} />
          {isMission && <ViewModeToggle value={viewMode} onChange={setViewMode} />}
        </div>
      </header>

      <aside className="hc-sidebar" aria-label="Primary navigation">
        <nav className="hc-nav">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`hc-nav-item${active ? ' active' : ''}`}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>
      </aside>

      <main className="hc-main" role="main">
        {children}
      </main>
    </div>
  )
}

