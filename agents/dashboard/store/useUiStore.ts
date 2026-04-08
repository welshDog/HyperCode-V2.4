'use client'

/**
 * Task 11 — UI Store
 * Zustand store for cross-component UI state.
 *
 * focusMode:
 *   When true, the dashboard hides non-essential panels so the user can
 *   concentrate on the current agent output / task feed.
 *   State is persisted to localStorage under the key 'hypercode-ui-state'.
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

interface UiState {
  focusMode: boolean
  toggleFocusMode: () => void
  setFocusMode: (value: boolean) => void
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      focusMode: false,

      toggleFocusMode: () =>
        set((state) => ({ focusMode: !state.focusMode })),

      setFocusMode: (value: boolean) =>
        set({ focusMode: value }),
    }),
    {
      name: 'hypercode-ui-state',
      storage: createJSONStorage(() => {
        // Guard for SSR — localStorage is only available in the browser
        if (typeof window === 'undefined') {
          return {
            getItem: () => null,
            setItem: () => {},
            removeItem: () => {},
          }
        }
        return window.localStorage
      }),
      partialize: (state) => ({ focusMode: state.focusMode }),
    }
  )
)
