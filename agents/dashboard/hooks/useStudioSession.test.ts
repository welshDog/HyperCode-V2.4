import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { pendingApprovals, useStudioSession, type StreamItem } from './useStudioSession'

const req = (approvalId: string, seq: number): StreamItem => ({
  kind: 'approval_request', approvalId, toolName: 'Write', target: 'app.py',
  rule: 'unknown_tool', reason: 'needs a human', expiresAt: '2026-07-11T09:35:00Z', seq,
})
const resolved = (approvalId: string, seq: number): StreamItem => ({
  kind: 'approval_resolved', approvalId, status: 'approved', seq,
})

describe('pendingApprovals', () => {
  it('returns an unresolved request', () => {
    expect(pendingApprovals([req('a', 1)]).map((i) => i.approvalId)).toEqual(['a'])
  })

  it('drops a request once its resolution arrives', () => {
    expect(pendingApprovals([req('a', 1), resolved('a', 2)])).toEqual([])
  })

  it('keeps only the still-pending ones', () => {
    const stream = [req('a', 1), req('b', 2), resolved('a', 3)]
    expect(pendingApprovals(stream).map((i) => i.approvalId)).toEqual(['b'])
  })
})

describe('respondApproval', () => {
  const realEventSource = global.EventSource
  const realFetch = global.fetch

  afterEach(() => {
    global.EventSource = realEventSource
    global.fetch = realFetch
    vi.restoreAllMocks()
  })

  // jsdom has no real SSE transport; a no-op stub keeps openStream() from
  // throwing so we can reach an active session without a real server.
  class NoopEventSource {
    onopen: (() => void) | null = null
    onerror: (() => void) | null = null
    addEventListener(): void {}
    close(): void {}
  }

  it('maps res.ok to the boolean it returns', async () => {
    // @ts-expect-error -- test stub, not a full EventSource implementation
    global.EventSource = NoopEventSource
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'cs_test' }),
    }) as unknown as typeof fetch

    const { result } = renderHook(() => useStudioSession())

    await act(async () => {
      await result.current.start('do a thing', 'do-a-thing')
    })
    expect(result.current.sessionId).toBe('cs_test')

    global.fetch = vi.fn().mockResolvedValue({ ok: true }) as unknown as typeof fetch
    let approved: boolean | undefined
    await act(async () => {
      approved = await result.current.respondApproval('ap_1', 'approved')
    })
    expect(approved).toBe(true)

    global.fetch = vi.fn().mockResolvedValue({ ok: false }) as unknown as typeof fetch
    let denied: boolean | undefined
    await act(async () => {
      denied = await result.current.respondApproval('ap_1', 'denied')
    })
    expect(denied).toBe(false)
  })

  it('returns false with no active session, without calling fetch', async () => {
    const fetchSpy = vi.fn()
    global.fetch = fetchSpy as unknown as typeof fetch

    const { result } = renderHook(() => useStudioSession())
    let response: boolean | undefined
    await act(async () => {
      response = await result.current.respondApproval('ap_1', 'approved')
    })
    expect(response).toBe(false)
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
