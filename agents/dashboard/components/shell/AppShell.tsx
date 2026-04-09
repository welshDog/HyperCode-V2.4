'use client'

import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { NDToggle } from '@/components/ui/NDToggle'
import { ViewModeToggle, type ViewMode } from '@/components/shell/ViewModeToggle'
import { ToastProvider } from '@/components/ui/ToastProvider'

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

  const isMission = pathname === '/mission'

  return (
    <ShellContext.Provider value={ctx}>
      <ToastProvider>
        <div className="hc-app">
          <header className="hc-topbar">
            <div className="hc-topbar-left">
              <span className="hc-brand">
                <span className="hc-brand-mark">🦅</span>
                <span className="hc-brand-text">WelshDog HyperCode IDE</span>
              </span>
            </div>
            <div className="hc-topbar-right">
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
      </ToastProvider>
    </ShellContext.Provider>
  )
}

