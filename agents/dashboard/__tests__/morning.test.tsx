import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MorningCard } from '@/components/crew/MorningCard'
import { loadMorning, resetMorningStore, getSnapshot } from '@/lib/morning/store'

const card = (over: Record<string, unknown> = {}) => ({
  status: 'done', tldr: ['Last 24 hours: a quiet one. That is fine.', 'Fleet: green (3.9 GB free)'],
  next_action: 'Start one small quest when you are ready', details: [], details_collapsed: true,
  plain_text: 'Last 24 hours: a quiet one. That is fine.\nNext: Start one small quest when you are ready', ...over,
})
const ok = (body: unknown) => ({ ok: true, json: async () => body })

beforeEach(() => resetMorningStore())
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('Morning Card', () => {
  it('loads once on mount and shows status, summary, one light and exactly one next action', async () => {
    const f = vi.fn().mockResolvedValue(ok({ calmCard: card(), light: 'green' }))
    vi.stubGlobal('fetch', f)
    render(<MorningCard />)
    expect(await screen.findByTestId('morning-next')).toHaveTextContent('Next: Start one small quest when you are ready')
    expect(screen.getByTestId('morning-status')).toHaveTextContent('Done')
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByTestId('morning-light')).toHaveTextContent('Green: plenty of room') // a word, not just a colour
    expect(f).toHaveBeenCalledTimes(1)
    expect(f.mock.calls[0][0]).toBe('/api/crew/morning')
  })

  it('does not poll: it fetches again only when you press Refresh', async () => {
    vi.useFakeTimers()
    const f = vi.fn().mockResolvedValue(ok({ calmCard: card(), light: 'amber' }))
    vi.stubGlobal('fetch', f)
    render(<MorningCard />)
    await vi.advanceTimersByTimeAsync(120_000)
    expect(f).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))
    await waitFor(() => expect(f).toHaveBeenCalledTimes(2))
  })

  it('shows win details only behind a collapsed "More detail"', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok({ calmCard: card({ details: ['Run aaaaaaaa: +20 XP'] }), light: 'green' })))
    render(<MorningCard />)
    const d = await screen.findByTestId('morning-details')
    expect(d).not.toHaveAttribute('open')
    expect(d).toHaveTextContent('Run aaaaaaaa: +20 XP')
  })

  it('says plainly when the crew cannot be reached, and offers Refresh', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    render(<MorningCard />)
    expect(await screen.findByText(/Can.t reach the crew right now/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeEnabled()
  })

  it('treats a malformed response as an error rather than showing a half card', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok({ calmCard: { status: 'done' }, light: 'green' })))
    await loadMorning()
    expect(getSnapshot().phase).toBe('error')
    expect(getSnapshot().card).toBeNull()
  })

  it('ignores an unknown light value instead of trusting it', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok({ calmCard: card(), light: 'purple' })))
    await loadMorning()
    expect(getSnapshot().phase).toBe('ready')
    expect(getSnapshot().light).toBeNull()
  })
})
