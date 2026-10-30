// @vitest-environment jsdom
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ResourcesPage from '../app/resources/page'

const snapshot = {
  available: true,
  collectedAt: '2026-10-30T18:00:00Z',
  wsl: { availableMb: 1232, totalMb: 3917, swapUsedMb: 1100, verdict: 'AMBER' },
  containers: [
    { name: 'prometheus', workingSetMb: 450, limitMb: 512, pctOfLimit: 87.9, cpuCores: 0.06, severity: 'warn' },
    { name: 'hypercode-core', workingSetMb: 150, limitMb: null, pctOfLimit: null, cpuCores: 0.1, severity: 'unbounded' },
  ],
  totals: { count: 2, workingSetMb: 600, nearLimit: 1 },
}
const respond = (body: unknown, ok = true) =>
  vi.fn().mockResolvedValue({ ok, status: ok ? 200 : 500, json: async () => body })

describe('Resources page', () => {
  beforeEach(() => vi.unstubAllGlobals())
  afterEach(() => vi.unstubAllGlobals())

  it('shows the WSL verdict, the gauge and every container', async () => {
    vi.stubGlobal('fetch', respond(snapshot))
    render(<ResourcesPage />)
    expect(await screen.findByText(/AMBER · no builds/)).toBeTruthy()
    const meter = screen.getByRole('meter', { name: 'WSL available memory' })
    expect(meter.getAttribute('aria-valuenow')).toBe('1232')
    expect(meter.getAttribute('aria-valuetext')).toContain('AMBER')
    expect(screen.getByText('prometheus')).toBeTruthy()
    expect(screen.getByText('hypercode-core')).toBeTruthy()
    expect(screen.getByText(/1 near their limit/)).toBeTruthy()
    expect(screen.getByText(/87\.9% high/)).toBeTruthy()
    expect(screen.getByText(/no limit/)).toBeTruthy()
  })

  it('explains an empty result instead of drawing an empty chart', async () => {
    vi.stubGlobal('fetch', respond({ available: false, reason: 'Prometheus is unreachable', collectedAt: 'x' }))
    render(<ResourcesPage />)
    expect(await screen.findByText(/Prometheus is unreachable/)).toBeTruthy()
    expect(screen.queryByRole('meter')).toBeNull()
  })

  it('shows an alert when the dashboard API itself fails', async () => {
    vi.stubGlobal('fetch', respond({}, false))
    render(<ResourcesPage />)
    await waitFor(() => expect(screen.getByRole('alert').textContent).toMatch(/Could not reach the dashboard API/))
  })
})
