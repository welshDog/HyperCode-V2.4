import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BROskiPulseView } from '../components/views/BROskiPulseView'

const swarm = vi.hoisted(() => ({ agents: [] as Array<Record<string, unknown>> }))
vi.mock('../hooks/useAgentSwarm', () => ({ useAgentSwarm: () => ({ agents: swarm.agents, loading: false, error: null }) }))

function stubBroski(body: unknown, ok = true) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok, json: async () => body }))
}

const stat = (label: RegExp) => screen.getByText(label).parentElement as HTMLElement

describe('BROskiPulseView', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
    swarm.agents = []
  })

  it("shows the user's real XP from /api/broski (the bug: it showed the agent sum, 0, while the real value was 6705)", async () => {
    swarm.agents = [{ id: 'a', name: 'celery-worker', status: 'healthy', xp: 0 }]
    stubBroski({ coins: 25, xp: 6705, level: 7 })
    render(<BROskiPulseView />)
    await waitFor(() => expect(stat(/Total XP/)).toHaveTextContent('6705'))
    expect(stat(/BROski\$/)).toHaveTextContent('25')
  })

  it('falls back to the sum of the agents\' XP when /api/broski has no xp', async () => {
    swarm.agents = [{ id: 'a', name: 'a', status: 'healthy', xp: 30 }, { id: 'b', name: 'b', status: 'idle', xp: 12 }]
    stubBroski({ coins: 5 })
    render(<BROskiPulseView />)
    await waitFor(() => expect(stat(/BROski\$/)).toHaveTextContent('5'))
    expect(stat(/Total XP/)).toHaveTextContent('42')
  })

  it('falls back to the agent sum when the fetch fails, and still renders', async () => {
    swarm.agents = [{ id: 'a', name: 'a', status: 'healthy', xp: 7 }]
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    render(<BROskiPulseView />)
    await waitFor(() => expect(stat(/Total XP/)).toHaveTextContent('7'))
  })

  it('ignores a non-numeric xp', async () => {
    swarm.agents = [{ id: 'a', name: 'a', status: 'healthy', xp: 3 }]
    stubBroski({ coins: 1, xp: 'lots' })
    render(<BROskiPulseView />)
    await waitFor(() => expect(stat(/BROski\$/)).toHaveTextContent('1'))
    expect(stat(/Total XP/)).toHaveTextContent('3')
  })
})
