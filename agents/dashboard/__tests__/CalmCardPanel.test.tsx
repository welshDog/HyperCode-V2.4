import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { CalmCardPanel } from '@/components/crew/CalmCardPanel'
import type { CalmCardData, EventsPayload } from '@/lib/agui/types'

const card = (over: Partial<CalmCardData> = {}): CalmCardData => ({
  status: 'waiting_on_you', tldr: ['Plan written'], next_action: 'Read the plan, then approve or reject it',
  details: ['Run: t1'], details_collapsed: true, plain_text: 'Plan written\nNext: Read the plan, then approve or reject it', ...over,
})
const payload = (over: Partial<EventsPayload> = {}): EventsPayload => ({
  taskId: 't1', events: [], nextAfter: -1, done: true, status: 'input_required', now: null, calmCard: card(), pollInterval: null, ...over,
})
const okFetch = (p: EventsPayload) => vi.fn().mockResolvedValue({ ok: true, json: async () => p })

async function show(id = 't1') {
  fireEvent.change(screen.getByLabelText('Crew task id'), { target: { value: id } })
  fireEvent.click(screen.getByText('Show'))
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('CalmCardPanel', () => {
  it('shows nothing but the input until a task id is given', () => {
    vi.stubGlobal('fetch', vi.fn())
    render(<CalmCardPanel />)
    expect(screen.queryByTestId('calm-next')).toBeNull()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('renders status as icon + word, the summary lines and exactly one next action', async () => {
    vi.stubGlobal('fetch', okFetch(payload()))
    render(<CalmCardPanel />)
    await show()
    expect(await screen.findByTestId('calm-status')).toHaveTextContent('! Waiting on you')
    expect(screen.getByTestId('calm-tldr').querySelectorAll('li')).toHaveLength(1)
    expect(screen.getAllByTestId('calm-next')).toHaveLength(1)
    expect(screen.getByTestId('calm-next')).toHaveTextContent('Next: Read the plan, then approve or reject it')
  })

  it('keeps details collapsed by default', async () => {
    vi.stubGlobal('fetch', okFetch(payload()))
    render(<CalmCardPanel />)
    await show()
    const details = (await screen.findByTestId('calm-details')) as HTMLDetailsElement
    expect(details.open).toBe(false)
  })

  it.each([
    ['running', '… Running'],
    ['paused', '‖ Paused'],
    ['blocked', '✕ Blocked'],
    ['done', '✓ Done'],
  ] as const)('status %s reads as "%s"', async (status, text) => {
    vi.stubGlobal('fetch', okFetch(payload({ calmCard: card({ status, details: [] }) })))
    render(<CalmCardPanel />)
    await show()
    expect(await screen.findByTestId('calm-status')).toHaveTextContent(text)
  })

  it('asks the proxy for the typed task id', async () => {
    const f = okFetch(payload())
    vi.stubGlobal('fetch', f)
    render(<CalmCardPanel />)
    await show('run-42')
    await waitFor(() => expect(f).toHaveBeenCalled())
    expect(f.mock.calls[0][0]).toBe('/api/crew/run-42/events?after=-1')
  })

  it('stops polling once the run is done', async () => {
    const f = okFetch(payload({ done: true }))
    vi.stubGlobal('fetch', f)
    render(<CalmCardPanel />)
    await show()
    await screen.findByTestId('calm-next')
    await new Promise((r) => setTimeout(r, 50))
    expect(f).toHaveBeenCalledTimes(1)
  })

  it('shows a calm message, not an error dump, when the crew cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED 10.0.0.5')))
    render(<CalmCardPanel />)
    await show()
    expect(await screen.findByText(/Can't reach the crew right now/)).toBeInTheDocument()
    expect(screen.queryByText(/10\.0\.0\.5/)).toBeNull()
  })

  it('reads the plain text aloud, and does not crash without speech support', async () => {
    vi.stubGlobal('fetch', okFetch(payload()))
    const speak = vi.fn()
    const cancel = vi.fn()
    vi.stubGlobal('speechSynthesis', { speak, cancel })
    vi.stubGlobal('SpeechSynthesisUtterance', class { constructor(public text: string) {} })
    render(<CalmCardPanel />)
    await show()
    fireEvent.click(await screen.findByText('Read it to me'))
    expect(speak).toHaveBeenCalledTimes(1)
    expect(speak.mock.calls[0][0].text).toContain('Next: Read the plan')
  })
})
