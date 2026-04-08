'use client'

import React from 'react'
import { HyperShellLayout } from '@/components/shell/HyperShellLayout'
import { useShellContext } from '@/components/shell/AppShell'

export default function MissionPage(): React.JSX.Element {
  const { viewMode, setViewMode } = useShellContext()
  return <HyperShellLayout showTopBar={false} viewMode={viewMode} setViewMode={setViewMode} />
}

