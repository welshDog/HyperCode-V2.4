'use client'

import React, { useState } from 'react'
import { Pane } from '@/components/shell/Pane'
import { MetricsView } from '@/components/views/MetricsView'
import { AgentSwarmView } from '@/components/views/AgentSwarmView'
import { TasksView } from '@/components/views/TasksView'
import { BROskiPulseView } from '@/components/views/BROskiPulseView'
import { SystemHealth } from '@/components/SystemHealth'
import { LeanModeBadge } from '@/components/LeanModeBadge'
import { useDockerServices } from '@/hooks/useDockerServices'

export default function HyperStationPage(): React.JSX.Element {
  const [focus, setFocus] = useState<string | null>(null)
  // Shared services feed — SystemHealth + LeanModeBadge read from the same poll
  const { services, loading } = useDockerServices(15_000)

  const gridTemplate = focus
    ? `"${focus} ${focus}" 1fr / 1fr 1fr`
    : `
        "metrics agents"  minmax(260px, 1fr)
        "services tasks"  minmax(260px, 1fr)
        "pulse   pulse"   minmax(260px, 1fr)
        / 1fr 1fr
      `

  return (
    <div className="hyper-shell" style={{ gridTemplate }}>
      {/* 🏷️ Lean Mode badge — floated top-right of the shell */}
      <div className="fixed top-3 right-4 z-30">
        <LeanModeBadge services={services} loading={loading} />
      </div>

      <Pane
        id="metrics"
        title="📊 Metrics Home"
        gridArea="metrics"
        focused={focus === 'metrics'}
        onFocusToggle={() => setFocus(focus === 'metrics' ? null : 'metrics')}
      >
        <MetricsView />
      </Pane>

      <Pane
        id="agents"
        title="🤖 Agents"
        gridArea="agents"
        focused={focus === 'agents'}
        onFocusToggle={() => setFocus(focus === 'agents' ? null : 'agents')}
      >
        {/* Agent cards are clickable — opens AgentDetailPopout */}
        <AgentSwarmView />
      </Pane>

      <Pane
        id="tasks"
        title="✅ Tasks"
        gridArea="tasks"
        focused={focus === 'tasks'}
        onFocusToggle={() => setFocus(focus === 'tasks' ? null : 'tasks')}
      >
        <TasksView />
      </Pane>

      <Pane
        id="services"
        title="🖥️ Services"
        gridArea="services"
        focused={focus === 'services'}
        onFocusToggle={() => setFocus(focus === 'services' ? null : 'services')}
      >
        {/* SystemHealth now has sparklines + ghost agents toggle built in */}
        <SystemHealth />
      </Pane>

      <Pane
        id="pulse"
        title="🦅 BROski Pulse"
        gridArea="pulse"
        focused={focus === 'pulse'}
        onFocusToggle={() => setFocus(focus === 'pulse' ? null : 'pulse')}
      >
        <BROskiPulseView />
      </Pane>
    </div>
  )
}
