'use client'

import React, { useState, useCallback } from 'react'
import { Pane } from './Pane'
import { ViewModeToggle } from './ViewModeToggle'
import { NDToggle } from '../ui/NDToggle'
import { AgentSwarmView } from '../views/AgentSwarmView'
import { TimelineView } from '../views/TimelineView'
import { MetricsView } from '../views/MetricsView'
import { BROskiPulseView } from '../views/BROskiPulseView'
import { TasksView } from '../views/TasksView'
import { LogsView } from '../views/LogsView'
import { PlanningView } from '../views/PlanningView'
import { useViewMode } from '@/hooks/useViewMode'
import type { ViewMode } from './ViewModeToggle'

// ── View Registry — register new views here, zero core changes needed
export const VIEW_REGISTRY: Record<string, React.ComponentType> = {
  'agent-swarm':  AgentSwarmView,
  'timeline':     TimelineView,
  'metrics':      MetricsView,
  'broski-pulse': BROskiPulseView,
  'tasks':        TasksView,
  'logs':         LogsView,
  'planning':     PlanningView,
}

export interface PaneConfig {
  id:         string
  title:      string
  viewId:     string
  gridArea:   string
}

const DEFAULT_PANES: PaneConfig[] = [
  // Row 1: agent status, event stream, metrics
  { id: 'agents',   title: '🤖 Agent Swarm',    viewId: 'agent-swarm',  gridArea: 'agents'   },
  { id: 'timeline', title: '📡 Event Timeline',  viewId: 'timeline',     gridArea: 'timeline' },
  { id: 'metrics',  title: '📊 Metrics',         viewId: 'metrics',      gridArea: 'metrics'  },
  // Row 2: tasks, logs, broski pulse
  { id: 'tasks',    title: '✅ Tasks',            viewId: 'tasks',        gridArea: 'tasks'    },
  { id: 'logs',     title: '📋 System Logs',      viewId: 'logs',         gridArea: 'logs'     },
  { id: 'pulse',    title: '🦅 BROski Pulse',     viewId: 'broski-pulse', gridArea: 'pulse'    },
  // Row 3: full-width planning
  { id: 'planning', title: '🧠 Plan Generator',   viewId: 'planning',     gridArea: 'planning' },
]

export function HyperShellLayout({
  showTopBar = true,
  viewMode: viewModeProp,
  setViewMode: setViewModeProp,
}: {
  showTopBar?: boolean
  viewMode?: ViewMode
  setViewMode?: (mode: ViewMode) => void
}): React.JSX.Element {
  const local = useViewMode()
  const viewMode = viewModeProp ?? local.viewMode
  const setViewMode = setViewModeProp ?? local.setViewMode
  const [focusedPaneId, setFocusedPaneId] = useState<string | null>(null)
  const [ndMode, setNdMode] = useState<string>('default')

  const handleNdChange = useCallback((mode: string) => {
    setNdMode(mode)
    document.documentElement.setAttribute('data-nd-mode', mode)
  }, [])

  const gridTemplate = viewMode === 'focus' && focusedPaneId
    ? `"${focusedPaneId} ${focusedPaneId} ${focusedPaneId}" 1fr / 1fr 1fr 1fr`
    : showTopBar
      ? `
          "topbar   topbar   topbar"   44px
          "agents   timeline metrics"  minmax(180px,1fr)
          "tasks    logs     pulse"    minmax(160px,1fr)
          "planning planning planning" minmax(200px,1fr)
          / 1fr     1fr      1fr
        `
      : `
          "agents   timeline metrics"  minmax(180px,1fr)
          "tasks    logs     pulse"    minmax(160px,1fr)
          "planning planning planning" minmax(200px,1fr)
          / 1fr     1fr      1fr
        `

  return (
    <div
      className="hyper-shell"
      style={{ gridTemplate }}
      data-testid="hyper-shell"
    >
      {showTopBar && (
        <div
          style={{
            gridArea:       'topbar',
            display:        'flex',
            alignItems:     'center',
            justifyContent: 'space-between',
            padding:        '0 16px',
            background:     'var(--pane-header)',
            borderBottom:   '1px solid var(--pane-border)',
          }}
        >
          <span style={{ color: 'var(--accent-cyan)', fontWeight: 700, fontSize: 14 }}>
            🦅 HyperCode Mission Control
          </span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <NDToggle value={ndMode} onChange={handleNdChange} />
            <ViewModeToggle value={viewMode} onChange={setViewMode} />
          </div>
        </div>
      )}

      {/* ── Panes ───────────────────────────────── */}
      {DEFAULT_PANES.map((pane) => {
        const ViewComponent = VIEW_REGISTRY[pane.viewId]
        const isFocused = focusedPaneId === pane.id
        return (
          <Pane
            key={pane.id}
            id={pane.id}
            title={pane.title}
            gridArea={pane.gridArea}
            focused={isFocused}
            onFocusToggle={() => setFocusedPaneId(isFocused ? null : pane.id)}
          >
            {ViewComponent && <ViewComponent />}
          </Pane>
        )
      })}
    </div>
  )
}
