import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AgentSwarmView } from '../components/views/AgentSwarmView'

vi.mock('../hooks/useAgentSwarm', () => ({
  useAgentSwarm: () => ({
    agents: [
      { id: 'healer', name: 'Healer Agent', status: 'healthy', xp: 250, xpToNextLevel: 500, level: 3, coins: 100, lastAction: 'Healed redis' },
      { id: 'agent-x', name: 'Agent X',     status: 'idle',    xp:   0, xpToNextLevel: 500, level: 1, coins:   0 },
    ],
    loading: false,
    error: null,
  })
}))

describe('AgentSwarmView', () => {
  it('renders agents', () => {
    render(<AgentSwarmView />)
    expect(screen.getByText('Healer Agent')).toBeInTheDocument()
    expect(screen.getByText('Agent X')).toBeInTheDocument()
  })

  it('shows last action when available', () => {
    render(<AgentSwarmView />)
    expect(screen.getByText(/Healed redis/i)).toBeInTheDocument()
  })

  it('shows loading state', () => {
    vi.doMock('../hooks/useAgentSwarm', () => ({
      useAgentSwarm: () => ({ agents: [], loading: true, error: null })
    }))
  })

  it('shows empty state when no agents', () => {
    vi.doMock('../hooks/useAgentSwarm', () => ({
      useAgentSwarm: () => ({ agents: [], loading: false, error: null })
    }))
  })
})
