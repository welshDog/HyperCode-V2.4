'use client'

import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'

export type ToastVariant = 'info' | 'success' | 'error'

export type ToastInput = {
  variant?: ToastVariant
  title: string
  message?: string
  durationMs?: number
}

type ToastItem = {
  id: string
  variant: ToastVariant
  title: string
  message?: string
}

type ToastContextValue = {
  pushToast: (toast: ToastInput) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('ToastContext missing')
  return ctx
}

export function ToastProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const timeoutsRef = useRef<Map<string, number>>(new Map())

  const remove = useCallback((id: string) => {
    const t = timeoutsRef.current.get(id)
    if (t) window.clearTimeout(t)
    timeoutsRef.current.delete(id)
    setToasts((prev) => prev.filter((x) => x.id !== id))
  }, [])

  const pushToast = useCallback((input: ToastInput) => {
    const id = `toast-${Date.now()}-${Math.random().toString(16).slice(2)}`
    const item: ToastItem = {
      id,
      variant: input.variant ?? 'info',
      title: input.title,
      message: input.message,
    }
    setToasts((prev) => [item, ...prev].slice(0, 4))
    const duration = typeof input.durationMs === 'number' ? input.durationMs : 3500
    const timeoutId = window.setTimeout(() => remove(id), duration)
    timeoutsRef.current.set(id, timeoutId)
  }, [remove])

  const value = useMemo<ToastContextValue>(() => ({ pushToast }), [pushToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="hc-toasts" aria-live="polite" aria-relevant="additions">
        {toasts.map((t) => (
          <div key={t.id} className={`hc-toast ${t.variant}`} role="status">
            <div className="hc-toast-head">
              <div className="hc-toast-title">{t.title}</div>
              <button className="hc-toast-close" onClick={() => remove(t.id)} aria-label="Dismiss notification">
                ×
              </button>
            </div>
            {t.message && <div className="hc-toast-msg">{t.message}</div>}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

