'use client'

import React, { useCallback, useMemo, useState } from 'react'
import { StatusBadge } from '../ui/StatusBadge'
import { XPBar } from '../ui/XPBar'
import { useAgentSwarm } from '@/hooks/useAgentSwarm'
import { useToast } from '@/components/ui/ToastProvider'
import { AgentDetailPopout } from '@/components/panels/AgentDetailPopout'
import type { Agent } from '@/types/agent'
import type { AgentSummary } from '@/components/panels/AgentDetailPopout'

function statusRank(status: Agent['status']): number {
  if (status === 'error') return 0
  if (status === 'warning') return 1
  if (status === 'healthy') return 2
  return 3
}

function formatCountLabel(count: number): string {
  return count === 1 ? 'agent' : 'agents'
}

/** Map Agent → AgentSummary for the popout */
function toSummary(agent: Agent): AgentSummary {
  return {
    id: agent.id,
    name: agent.name,
    status: agent.status,
    lastActivity: agent.lastAction,
    last_seen: (agent as unknown as Record<string, string>).last_seen,
    skills: (agent as unknown as Record<string, string[]>).skills,
    circuitState: (agent as unknown as Record<string, string>).circuit_state,
    circuitFailures: (agent as unknown as Record<string, number>).circuit_failures,
  };
}

export function AgentSwarmView(): React.JSX.Element {
  const { toast } = useToast()
  const [selectedAgent, setSelectedAgent] = useState<AgentSummary | null>(null);

  const onRefetchComplete = useCallback((success: boolean) => {
    if (success) {
      toast({ type: 'success', message: '✅ Agent status refreshed' })
    } else {
      toast({ type: 'error', message: '❌ Failed to refresh agents' })
    }
  }, [toast])

  const { agents, loading, error, refetch } = useAgentSwarm(onRefetchComplete)

  const stats = useMemo(() => {
    const counts = { healthy: 0, warning: 0, error: 0, idle: 0, total: 0 }
    for (const a of agents) {
      counts.total += 1
      if (a.status === 'healthy') counts.healthy += 1
      else if (a.status === 'warning') counts.warning += 1
      else if (a.status === 'error') counts.error += 1
      else counts.idle += 1
    }
    return counts
  }, [agents])

  const sortedAgents = useMemo(() => {
    return [...agents].sort((a, b) => {
      const r = statusRank(a.status) - statusRank(b.status)
      if (r !== 0) return r
      return a.name.localeCompare(b.name)
    })
  }, [agents])

  const handleManualRefetch = () => {
    toast({ type: 'info', message: '⏳ Polling agent fleet…' })
    refetch()
  }

  if (loading) {
    return (
      <div className="hc-agent-swarm" data-testid="agent-swarm" aria-busy="true">
        <div className="hc-agent-swarm-header">
          <div className="hc-agent-swarm-title">
            <span className="hc-agent-swarm-kpi">
              <span className="hc-agent-swarm-kpi-value hc-mono">--</span>
              <span className="hc-agent-swarm-kpi-label">agents</span>
            </span>
          </div>
          <div className="hc-agent-swarm-actions">
            <button type="button" className="btn" disabled aria-disabled="true">↻ Refresh</button>
          </div>
        </div>
        <div className="hc-agent-swarm-list">
          {Array.from({ length: 8 }).map((_, idx) => (
            <div key={idx} className="hc-agent-card hc-skeleton" aria-hidden="true" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="hc-agent-swarm" data-testid="agent-swarm" role="alert">
        <div className="hc-agent-swarm-header">
          <div className="hc-agent-swarm-title">
            <span className="hc-agent-swarm-kpi">
              <span className="hc-agent-swarm-kpi-value hc-mono">{stats.total}</span>
              <span className="hc-agent-swarm-kpi-label">{formatCountLabel(stats.total)}</span>
            </span>
          </div>
          <div className="hc-agent-swarm-actions">
            <button type="button" className="btn" onClick={handleManualRefetch}>↻ Refresh</button>
          </div>
        </div>
        <div className="hc-agent-swarm-empty hc-agent-swarm-error">
          <div className="hc-agent-swarm-empty-title">Agent fleet unavailable</div>
          <div className="hc-agent-swarm-empty-subtitle hc-mono">{error}</div>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* 🔍 Agent detail popout — rendered at root so it overlays everything */}
      <AgentDetailPopout agent={selectedAgent} onClose={() => setSelectedAgent(null)} />

      <div className="hc-agent-swarm" data-testid="agent-swarm">
        <div className="hc-agent-swarm-header">
          <div className="hc-agent-swarm-title">
            <span className="hc-agent-swarm-kpi">
              <span className="hc-agent-swarm-kpi-value hc-mono">{stats.total}</span>
              <span className="hc-agent-swarm-kpi-label">{formatCountLabel(stats.total)}</span>
            </span>
            <div className="hc-agent-swarm-badges" role="list" aria-label="Fleet status counts">
              <span className="hc-agent-swarm-chip" role="listitem"><span className="status-dot error" aria-hidden="true" />{stats.error}</span>
              <span className="hc-agent-swarm-chip" role="listitem"><span className="status-dot warning" aria-hidden="true" />{stats.warning}</span>
              <span className="hc-agent-swarm-chip" role="listitem"><span className="status-dot healthy" aria-hidden="true" />{stats.healthy}</span>
              <span className="hc-agent-swarm-chip" role="listitem"><span className="status-dot idle" aria-hidden="true" />{stats.idle}</span>
            </div>
          </div>
          <div className="hc-agent-swarm-actions">
            <button type="button" className="btn" onClick={handleManualRefetch} aria-label="Refresh agent fleet">↻ Refresh</button>
          </div>
        </div>

        {sortedAgents.length === 0 ? (
          <div className="hc-agent-swarm-empty">
            <div className="hc-agent-swarm-empty-title">No agents reporting</div>
            <div className="hc-agent-swarm-empty-subtitle">
              Start the agents profile and wait for heartbeats.
            </div>
          </div>
        ) : (
          <div className="hc-agent-swarm-list" role="list" aria-label="Agent fleet">
            {sortedAgents.map((agent: Agent) => (
              <div
                key={agent.id}
                className="hc-agent-card cursor-pointer hover:border-zinc-600 transition-colors"
                role="listitem"
                onClick={() => setSelectedAgent(toSummary(agent))}
                title={`Click to inspect ${agent.name}`}
              >
                <div className="hc-agent-card-top">
                  <div className="hc-agent-card-name" title={agent.name}>{agent.name}</div>
                  <StatusBadge status={agent.status} />
                </div>
                <div className="hc-agent-card-metrics">
                  <span className="hc-agent-card-metric hc-mono" aria-label={`Level ${agent.level ?? 1}`}>
                    LV {agent.level ?? 1}
                  </span>
                  <span className="hc-agent-card-metric hc-mono" aria-label={`${agent.xp ?? 0} XP`}>
                    {agent.xp ?? 0} XP
                  </span>
                  {typeof agent.coins === 'number' && (
                    <span className="hc-agent-card-metric hc-mono" aria-label={`${agent.coins} coins`}>
                      {agent.coins} ⓑ
                    </span>
                  )}
                </div>
                <XPBar xp={agent.xp ?? 0} maxXp={agent.xpToNextLevel ?? 100} level={agent.level ?? 1} />
                {agent.lastAction && (
                  <div className="hc-agent-card-last" title={agent.lastAction}>
                    <span className="hc-agent-card-last-label">Last</span>
                    <span className="hc-agent-card-last-value">{agent.lastAction}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
