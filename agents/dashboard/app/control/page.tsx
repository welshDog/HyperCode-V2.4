'use client'

// Mission Control — one glance = state of the whole fleet + every safety verdict.
// Fleet grid is the focal point (registry :8077); the Shepherd feed rides the
// right rail (:8096). ApprovalModal overlays for pending ESCALATE decisions.

import React from 'react'
import FleetGridPanel from '@/components/panels/FleetGridPanel'
import SafetyFeedPanel from '@/components/panels/SafetyFeedPanel'
import { ApprovalModal } from '@/components/ApprovalModal'

export default function MissionControlPage(): React.JSX.Element {
  return (
    <main className="min-h-screen bg-[#0a0a0a] p-4 lg:p-6">
      <ApprovalModal />

      <header className="mb-5 flex items-baseline gap-2">
        <h1 className="text-xl font-bold tracking-tight">
          <span className="font-mono text-cyan-400">HyperCode</span>{' '}
          <span className="text-white">Mission Control</span>
        </h1>
        <span className="text-xs text-gray-600">fleet · safety · live</span>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
        <div className="lg:col-span-2">
          <FleetGridPanel />
        </div>
        <SafetyFeedPanel />
      </div>
    </main>
  )
}
