import '@testing-library/jest-dom'
import React from 'react'
import { vi } from 'vitest'

vi.mock('@/components/ui/ToastProvider', () => {
  const pushToast = vi.fn()
  return {
    ToastProvider: ({ children }: { children: React.ReactNode }) => children,
    useToast: () => ({
      toast: pushToast,
      pushToast,
      history: [],
      dismissHistory: vi.fn(),
      clearHistory: vi.fn(),
    }),
  }
})
