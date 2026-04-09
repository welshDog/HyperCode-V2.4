'use client'

import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import Link from 'next/link'

export type ToastVariant = 'info' | 'success' | 'error'

export type ToastAction = {
  label: string
  href: string
}

export type ToastInput = {
  variant?: ToastVariant
  type?: ToastVariant
  title?: string
  message?: string
  durationMs?: number
  action?: ToastAction
}

type ToastItem = {
  id: string
  variant: ToastVariant
  title: string
  message?: string
  action?: ToastAction
}

export type ToastHistoryItem = ToastItem & {
  createdAt: number
}

type ToastContextValue = {
  toast: (toast: ToastInput) => void
  pushToast: (toast: ToastInput) => void
  history: ToastHistoryItem[]
  dismissHistory: (id: string) => void
  clearHistory: () => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('ToastContext missing')
  return ctx
}

export function ToastProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const [history, setHistory] = useState<ToastHistoryItem[]>([])
  const timeoutsRef = useRef<Map<string, number>>(new Map())

  const removeActive = useCallback((id: string) => {
    const t = timeoutsRef.current.get(id)
    if (t) window.clearTimeout(t)
    timeoutsRef.current.delete(id)
    setToasts((prev) => prev.filter((x) => x.id !== id))
  }, [])

  const dismissHistory = useCallback((id: string) => {
    removeActive(id)
    setHistory((prev) => prev.filter((x) => x.id !== id))
  }, [removeActive])

  const clearHistory = useCallback(() => {
    setHistory([])
  }, [])

  const pushToast = useCallback((input: ToastInput) => {
    const id = `toast-${Date.now()}-${Math.random().toString(16).slice(2)}`
    const title = (input.title ?? input.message ?? '').trim()
    if (!title) return
    const actionLabel = input.action?.label?.trim() ?? ''
    const actionHref = input.action?.href?.trim() ?? ''
    const action = actionLabel && actionHref ? { label: actionLabel, href: actionHref } : undefined
    const item: ToastItem = {
      id,
      variant: input.variant ?? input.type ?? 'info',
      title,
      message: input.title ? input.message : undefined,
      action,
    }
    const historyItem: ToastHistoryItem = {
      ...item,
      createdAt: Date.now(),
    }
    setToasts((prev) => [item, ...prev].slice(0, 4))
    setHistory((prev) => [historyItem, ...prev].slice(0, 100))
    const duration = typeof input.durationMs === 'number' ? input.durationMs : 3500
    const timeoutId = window.setTimeout(() => removeActive(id), duration)
    timeoutsRef.current.set(id, timeoutId)
  }, [removeActive])

  const value = useMemo<ToastContextValue>(() => ({
    toast: pushToast,
    pushToast,
    history,
    dismissHistory,
    clearHistory,
  }), [pushToast, history, dismissHistory, clearHistory])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="hc-toasts" aria-live="polite" aria-relevant="additions">
        {toasts.map((t) => (
          <div key={t.id} className={`hc-toast ${t.variant}`} role="status">
            <div className="hc-toast-head">
              <div className="hc-toast-title">{t.title}</div>
              <div className="hc-toast-actions">
                {t.action && (
                  <Link className="hc-toast-action" href={t.action.href} onClick={() => removeActive(t.id)}>
                    {t.action.label}
                  </Link>
                )}
                <button className="hc-toast-close" onClick={() => removeActive(t.id)} aria-label="Dismiss notification">
                  ×
                </button>
              </div>
            </div>
            {t.message && <div className="hc-toast-msg">{t.message}</div>}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
