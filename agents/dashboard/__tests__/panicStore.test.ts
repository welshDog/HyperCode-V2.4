import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { dismissMessage, getSnapshot, loadHeld, panic, resetPanicStore, resume } from '@/lib/panic/store'

const ok = (body: unknown) => ({ ok: true, json: async () => body })
const run = (id: string) => ({ taskId: id, pausedAt: 't', card: { tldr: ['Plan written'], next_action: 'Read the plan' } })

function stubFetch(handler: (url: string, init?: RequestInit) => unknown) {
  const f = vi.fn(async (url: string, init?: RequestInit) => handler(url, init))
  vi.stubGlobal('fetch', f)
  return f
}

beforeEach(() => resetPanicStore())
afterEach(() => vi.unstubAllGlobals())

describe('panic store', () => {
  it('starts idle with nothing held and no message', () => {
    expect(getSnapshot()).toMatchObject({ phase: 'idle', held: [], message: null })
  })

  it('POSTs to the fixed panic path and shows the exact message core sent', async () => {
    const f = stubFetch((url, init) =>
      init?.method === 'POST' ? ok({ saved: true, ledger: true, paused: [run('a')], alreadyPaused: [], message: 'Saved. Nothing is running. Take your time.' })
        : ok({ paused: [run('a')] }))
    await panic()
    expect(f.mock.calls[0][0]).toBe('/api/crew/panic')
    expect(f.mock.calls[0][1]).toMatchObject({ method: 'POST' })
    expect(getSnapshot().message).toBe('Saved. Nothing is running. Take your time.')
    expect(getSnapshot().held.map((h) => h.taskId)).toEqual(['a'])
    expect(getSnapshot().phase).toBe('idle')
  })

  it('never claims "Saved" when core did not confirm it', async () => {
    for (const reply of [() => { throw new Error('ECONNREFUSED 10.0.0.5') }, () => ({ ok: false, json: async () => ({}) }), () => ok({ saved: false, message: 'Saved.' }), () => ok({})]) {
      resetPanicStore()
      stubFetch(reply)
      await panic()
      const s = getSnapshot()
      expect(s.phase).toBe('error')
      expect(s.message).toContain('nothing was changed')
      expect(s.message).not.toMatch(/Saved/)
      expect(s.message).not.toContain('10.0.0.5')
      expect(s.held).toEqual([])
    }
  })

  it('is disabled-friendly: phase is "working" while the request is in flight', async () => {
    let release: (v: unknown) => void = () => {}
    stubFetch(() => new Promise((r) => { release = r }))
    const p = panic()
    expect(getSnapshot().phase).toBe('working')
    release(ok({ saved: true, paused: [], alreadyPaused: [], message: 'Nothing was running. You are all clear.' }))
    await p
    expect(getSnapshot().phase).toBe('idle')
  })

  it('mentions it when the audit note could not be written, but still says saved', async () => {
    stubFetch((_u, init) => (init?.method === 'POST' ? ok({ saved: true, ledger: false, paused: [run('a')], alreadyPaused: [], message: 'Saved. Nothing is running. Take your time.' }) : ok({ paused: [run('a')] })))
    await panic()
    expect(getSnapshot().message).toContain('Saved. Nothing is running. Take your time.')
    expect(getSnapshot().message).toContain('audit note could not be written')
  })

  it('keeps what was already held when a second panic finds nothing new', async () => {
    stubFetch((_u, init) => (init?.method === 'POST' ? ok({ saved: true, ledger: true, paused: [run('a')], alreadyPaused: [], message: 'm' }) : ok({ paused: [run('a')] })))
    await panic()
    stubFetch((_u, init) => (init?.method === 'POST' ? ok({ saved: true, ledger: true, paused: [], alreadyPaused: ['a'], message: 'm2' }) : ok({ paused: [run('a')] })))
    await panic()
    expect(getSnapshot().held.map((h) => h.taskId)).toEqual(['a'])
  })

  it('loadHeld restores what is held after a refresh and ignores junk', async () => {
    stubFetch(() => ok({ paused: [run('a'), { nope: 1 }, null, 'x', run('b')] }))
    await loadHeld()
    expect(getSnapshot().held.map((h) => h.taskId)).toEqual(['a', 'b'])
    expect(getSnapshot().loaded).toBe(true)
  })

  it('loadHeld failing quietly leaves what we had', async () => {
    stubFetch((_u, init) => (init?.method === 'POST' ? ok({ saved: true, paused: [run('a')], alreadyPaused: [], message: 'm' }) : ok({ paused: [run('a')] })))
    await panic()
    stubFetch(() => { throw new Error('down') })
    await loadHeld()
    expect(getSnapshot().held.map((h) => h.taskId)).toEqual(['a'])
  })

  it('resume POSTs to the resume path and clears what was held', async () => {
    stubFetch((_u, init) => (init?.method === 'POST' ? ok({ saved: true, paused: [run('a')], alreadyPaused: [], message: 'm' }) : ok({ paused: [run('a')] })))
    await panic()
    const f = stubFetch((u) => (u.endsWith('/resume') ? ok({ resumed: ['a'] }) : ok({ paused: [] })))
    await resume()
    expect(f.mock.calls[0][0]).toBe('/api/crew/panic/resume')
    expect(f.mock.calls[0][1]).toMatchObject({ method: 'POST' })
    expect(getSnapshot().held).toEqual([])
    expect(getSnapshot().message).toContain('Resumed')
  })

  it('a failed resume keeps everything held and says nothing changed', async () => {
    stubFetch((_u, init) => (init?.method === 'POST' ? ok({ saved: true, paused: [run('a')], alreadyPaused: [], message: 'm' }) : ok({ paused: [run('a')] })))
    await panic()
    stubFetch(() => ({ ok: false, json: async () => ({}) }))
    await resume()
    expect(getSnapshot().held).toHaveLength(1)
    expect(getSnapshot().phase).toBe('error')
    expect(getSnapshot().message).toContain('Nothing was changed')
  })

  it('dismissMessage clears only the message', async () => {
    stubFetch((_u, init) => (init?.method === 'POST' ? ok({ saved: true, paused: [run('a')], alreadyPaused: [], message: 'hello' }) : ok({ paused: [run('a')] })))
    await panic()
    dismissMessage()
    expect(getSnapshot().message).toBeNull()
    expect(getSnapshot().held).toHaveLength(1)
  })
})
