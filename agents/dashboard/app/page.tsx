'use client'

import React, { useState } from 'react'
import { Pane } from '@/components/shell/Pane'
import { MetricsView } from '@/components/views/MetricsView'
import { AgentSwarmView } from '@/components/views/AgentSwarmView'
import { TasksView } from '@/components/views/TasksView'
import { BROskiPulseView } from '@/components/views/BROskiPulseView'
import { SystemHealth } from '@/components/SystemHealth'

export default function HyperStationPage(): React.JSX.Element {
  const [focus, setFocus] = useState<string | null>(null)
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
