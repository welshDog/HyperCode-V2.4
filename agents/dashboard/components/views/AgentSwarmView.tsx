'use client'

import React, { useCallback } from 'react'
import { StatusBadge } from '../ui/StatusBadge'
import { XPBar } from '../ui/XPBar'
import { useAgentSwarm } from '@/hooks/useAgentSwarm'
import { useToast } from '@/components/ui/ToastProvider'
import type { Agent } from '@/types/agent'

export function AgentSwarmView(): React.JSX.Element {
  const { toast } = useToast()

  const onRefetchComplete = useCallback((success: boolean) => {
    if (success) {
      toast({ type: 'success', message: '✅ Agent status refreshed' })
    } else {
      toast({ type: 'error', message: '❌ Failed to refresh agents' })
    }
  }, [toast])

  const { agents, loading, error, refetch } = useAgentSwarm(onRefetchComplete)

  const handleManualRefetch = () => {
    toast({ type: 'info', message: '⏳ Polling agent fleet…' })
    refetch()
  }

  if (loading) return <div style={{ color: 'var(--text-secondary)', padding: 16 }}>⏳ Loading agents...</div>
  if (error)   return <div style={{ color: 'var(--status-error)',   padding: 16 }}>⚠️ {error}</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }} data-testid="agent-swarm">
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
        <button className="btn" onClick={handleManualRefetch} style={{ fontSize: 10, padding: '2px 8px' }}>↻ Refresh</button>
      </div>
      {agents.map((agent: Agent) => (
        <div
          key={agent.id}
          style={{
            background:   'rgba(255,255,255,0.03)',
            border:       '1px solid var(--pane-border)',
            borderRadius: 6,
            padding:      '8px 10px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontWeight: 600, fontSize: 13 }}>{agent.name}</span>
            <StatusBadge status={agent.status} />
          </div>
          <XPBar xp={agent.xp ?? 0} maxXp={agent.xpToNextLevel ?? 100} level={agent.level ?? 1} />
          {agent.lastAction && (
            <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 4 }}>
              Last: {agent.lastAction}
            </div>
          )}
        </div>
      ))}
      {agents.length === 0 && (
        <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: 24 }}>No agents online</div>
      )}
    </div>
  )
}
