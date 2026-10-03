import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { PanicButton, PanicNotice } from '@/components/crew/PanicControl'
import { resetPanicStore } from '@/lib/panic/store'

const ok = (body: unknown) => ({ ok: true, json: async () => body })
const run = (id: string) => ({ taskId: id, card: { tldr: ['Plan written', 'You approved the plan'], next_action: 'Read the plan' } })

function stub(held: unknown[] = []) {
  // Models the server as the source of truth: once a panic is saved, GET reports the held run.
  let current = held
  const f = vi.fn(async (_u: string, init?: RequestInit) => {
    if (init?.method === 'POST') {
      current = held.length ? held : [run('a')]
      return ok({ saved: true, ledger: true, paused: current, alreadyPaused: [], message: 'Saved. Nothing is running. Take your time.' })
    }
    return ok({ paused: current })
  })
  vi.stubGlobal('fetch', f)
  return f
}

beforeEach(() => resetPanicStore())
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('Panic control', () => {
  it('is one literally-labelled button', () => {
    stub()
    render(<PanicButton />)
    expect(screen.getByRole('button', { name: 'Pause everything' })).toBeInTheDocument()
  })

  it('one click pauses, with no confirmation dialog', async () => {
    const f = stub()
    const confirm = vi.spyOn(window, 'confirm')
    render(<><PanicButton /><PanicNotice /></>)
    fireEvent.click(screen.getByRole('button', { name: 'Pause everything' }))
    expect(await screen.findByText(/Saved\. Nothing is running\. Take your time\./)).toBeInTheDocument()
    expect(confirm).not.toHaveBeenCalled()
    expect(f.mock.calls.some(([u, i]) => u === '/api/crew/panic' && i?.method === 'POST')).toBe(true)
  })

  it('then offers Resume, with the count, and shows where you were', async () => {
    stub()
    render(<><PanicButton /><PanicNotice /></>)
    fireEvent.click(screen.getByRole('button', { name: 'Pause everything' }))
    const resumeBtn = await screen.findByRole('button', { name: /Paused \(1\) · Resume/ })
    expect(resumeBtn).toBeInTheDocument()
    expect(screen.getByTestId('panic-held')).toHaveTextContent('Where you were: You approved the plan — next: Read the plan')
  })

  it('shows what is held after a refresh (loaded from the server)', async () => {
    stub([run('x'), run('y')])
    render(<><PanicButton /><PanicNotice /></>)
    expect(await screen.findByRole('button', { name: /Paused \(2\) · Resume/ })).toBeInTheDocument()
  })

  it('resume clears the hold and says what happens next', async () => {
    const f = vi.fn(async (u: string, init?: RequestInit) => {
      if (u.endsWith('/resume')) return ok({ resumed: ['x'] })
      if (init?.method === 'POST') return ok({})
      return ok({ paused: u && f.mock.calls.length < 3 ? [run('x')] : [] })
    })
    vi.stubGlobal('fetch', f)
    render(<><PanicButton /><PanicNotice /></>)
    fireEvent.click(await screen.findByRole('button', { name: /Resume/ }))
    expect(await screen.findByText(/Resumed\. The crew carries on from where it stopped\./)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Pause everything' })).toBeInTheDocument())
  })

  it('when core cannot be reached it says nothing was changed, and does not say Saved', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('down') }))
    render(<><PanicButton /><PanicNotice /></>)
    fireEvent.click(screen.getByRole('button', { name: 'Pause everything' }))
    expect(await screen.findByText(/nothing was changed/)).toBeInTheDocument()
    expect(screen.queryByText(/Saved/)).toBeNull()
    expect(screen.getByRole('button', { name: 'Pause everything' })).toBeEnabled() // can simply try again
  })

  it('the notice can be dismissed and is a polite live region', async () => {
    stub()
    render(<><PanicButton /><PanicNotice /></>)
    fireEvent.click(screen.getByRole('button', { name: 'Pause everything' }))
    const notice = await screen.findByTestId('panic-notice')
    expect(notice).toHaveAttribute('role', 'status')
    expect(notice).toHaveAttribute('aria-live', 'polite')
    fireEvent.click(screen.getByRole('button', { name: 'OK' }))
    expect(screen.queryByText(/Saved\./)).toBeNull()
    expect(screen.getByTestId('panic-held')).toBeInTheDocument() // the hold itself stays visible
  })

  it('renders nothing when nothing happened', () => {
    stub()
    const { container } = render(<PanicNotice />)
    expect(container).toBeEmptyDOMElement()
  })
})
