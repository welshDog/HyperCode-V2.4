'use client'

import { useState, useCallback } from 'react'
import type { ViewMode } from '@/components/shell/ViewModeToggle'

export function useViewMode() {
  const [viewMode, setViewModeState] = useState<ViewMode>('grid')

  const setViewMode = useCallback((mode: ViewMode) => {
    setViewModeState(mode)
  }, [])

  return { viewMode, setViewMode }
}
