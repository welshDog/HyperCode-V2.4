/**
 * Unit Tests — HyperShellLayout
 * Validates: render, pane presence, focus toggle, ND modes, view modes
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { HyperShellLayout } from '../components/shell/HyperShellLayout'

vi.mock('../hooks/useAgentSwarm', () => ({
  useAgentSwarm: () => ({
    agents: [
      { id: '1', name: 'Healer Agent', status: 'healthy', xp: 150, xpToNextLevel: 500, level: 2, coins: 75 },
      { id: '2', name: 'Agent X',      status: 'warning', xp:  50, xpToNextLevel: 500, level: 1, coins: 20 },
    ],
    loading: false,
    error: null,
  })
}))

vi.mock('../hooks/useEventStream', () => ({
  useEventStream: () => ({ events: [], connected: true })
}))

vi.mock('../hooks/useMetrics', () => ({
  useMetrics: () => ({ metrics: null, loading: false })
}))

vi.mock('../hooks/useTasks', () => ({
  useTasks: () => ({ tasks: [], loading: false, error: null, refetch: vi.fn() })
}))

vi.mock('../hooks/useLogs', () => ({
  useLogs: () => ({ logs: [], loading: false, liveWs: false }),
  levelColour: () => 'var(--accent-cyan)',
}))

describe('HyperShellLayout', () => {
  it('renders without crashing', () => {
    render(<HyperShellLayout />)
    expect(screen.getByTestId('hyper-shell')).toBeInTheDocument()
  })

  it('renders all 7 panes', () => {
    render(<HyperShellLayout />)
    expect(screen.getByTestId('pane-agents')).toBeInTheDocument()
    expect(screen.getByTestId('pane-timeline')).toBeInTheDocument()
    expect(screen.getByTestId('pane-metrics')).toBeInTheDocument()
    expect(screen.getByTestId('pane-pulse')).toBeInTheDocument()
    expect(screen.getByTestId('pane-tasks')).toBeInTheDocument()
    expect(screen.getByTestId('pane-logs')).toBeInTheDocument()
    expect(screen.getByTestId('pane-planning')).toBeInTheDocument()
  })

  it('shows Mission Control header', () => {
    render(<HyperShellLayout />)
    expect(screen.getByText(/Mission Control/i)).toBeInTheDocument()
  })

  it('focuses a pane on click', () => {
    render(<HyperShellLayout />)
    const focusBtn = screen.getAllByRole('button', { name: /Focus this pane/i })[0]
    fireEvent.click(focusBtn)
    expect(screen.getAllByText(/Exit Focus/i).length).toBeGreaterThan(0)
  })

  it('renders view mode toggles', () => {
    render(<HyperShellLayout />)
    expect(screen.getAllByText(/Grid/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Focus/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Present/i).length).toBeGreaterThan(0)
  })

  it('renders ND mode toggles', () => {
    render(<HyperShellLayout />)
    expect(screen.getByText(/Default/i)).toBeInTheDocument()
    expect(screen.getByText(/Dyslexia/i)).toBeInTheDocument()
    expect(screen.getByText(/High-C/i)).toBeInTheDocument()
  })
})
