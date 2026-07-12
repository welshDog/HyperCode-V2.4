import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

const mockUseFleet = vi.fn()
vi.mock('../hooks/useFleet', () => ({
  useFleet: () => mockUseFleet(),
}))

import FleetGridPanel from '../components/panels/FleetGridPanel'

const SUMMARY = {
  total: 42,
  healthy: 20,
  running: 5,
  down: 1,
  not_deployed: 15,
  crash_looping: 1,
  auto_restart_enabled: true,
  generated_at: '2026-07-12T00:00:00Z',
}

describe('FleetGridPanel', () => {
  it('renders the live count and trouble first', () => {
    mockUseFleet.mockReturnValue({
      summary: SUMMARY,
      agents: [
        { name: 'healer-agent', role: 'Self-healing', source: 'x', status: 'healthy' },
        { name: 'broski-bot', role: 'Discord bot', source: 'x', status: 'down' },
        { name: 'ghost', role: 'Dormant', source: 'x', status: 'not_deployed' },
      ],
      error: null,
      loading: false,
    })
    render(<FleetGridPanel />)

    expect(screen.getByText('25')).toBeInTheDocument() // healthy + running
    expect(screen.getByText('AUTO-HEAL ON')).toBeInTheDocument()

    const cards = screen.getAllByRole('listitem')
    // down sorts before healthy, dormant last
    expect(cards[0]).toHaveAccessibleName('broski-bot — Down')
    expect(cards[2]).toHaveAccessibleName('ghost — Not deployed')
  })

  it('flags crash-looping agents', () => {
    mockUseFleet.mockReturnValue({
      summary: SUMMARY,
      agents: [
        { name: 'flappy', role: 'Crashy', source: 'x', status: 'running', crash_loop: true },
      ],
      error: null,
      loading: false,
    })
    render(<FleetGridPanel />)
    expect(screen.getByText('CRASH LOOP')).toBeInTheDocument()
  })

  it('shows the registry error state', () => {
    mockUseFleet.mockReturnValue({ summary: null, agents: [], error: 'boom', loading: false })
    render(<FleetGridPanel />)
    expect(screen.getByRole('alert')).toHaveTextContent('Registry unreachable: boom')
  })
})
