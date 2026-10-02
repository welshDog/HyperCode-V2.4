import { describe, it, expect } from 'vitest'
import { applyPayload, initialRun, runReducer } from '@/lib/agui/runStore'
import type { AguiEvent, CalmCardData, EventsPayload } from '@/lib/agui/types'

const card = (over: Partial<CalmCardData> = {}): CalmCardData => ({
  status: 'running', tldr: ['Starting up'], next_action: 'Nothing needed.', details: [], details_collapsed: true,
  plain_text: 'Starting up\nNext: Nothing needed.', ...over,
})

const custom = (name: string, value: Record<string, unknown>): AguiEvent => ({ type: 'CUSTOM', name: `hypercode.${name}`, value })

const payload = (events: AguiEvent[], from = 0, over: Partial<EventsPayload> = {}): EventsPayload => ({
  taskId: 't1',
  events: events.map((event, i) => ({ seq: from + i, event })),
  nextAfter: from + events.length - 1,
  done: false, status: 'working', now: 'Writing the plan', calmCard: card(), pollInterval: 2000, ...over,
})

describe('runStore', () => {
  it('carries the paused flag from the server, defaulting to not paused', () => {
    expect(initialRun('t1').paused).toBe(false)
    expect(applyPayload(initialRun('t1'), payload([], 0, { paused: true })).paused).toBe(true)
    expect(applyPayload(initialRun('t1'), payload([], 0)).paused).toBe(false)
  })

  it('starts idle with nothing applied', () => {
    const s = initialRun()
    expect(s.status).toBe('idle')
    expect(s.lastSeq).toBe(-1)
    expect(s.calmCard).toBeNull()
  })

  it('tracks step progress', () => {
    const s = applyPayload(initialRun('t1'), payload([
      { type: 'STEP_STARTED', stepName: 'plan' }, { type: 'STEP_FINISHED', stepName: 'plan' }, { type: 'STEP_STARTED', stepName: 'build' },
    ]))
    expect(s.steps).toEqual({ plan: 'finished', build: 'running' })
    expect(s.lastSeq).toBe(2)
  })

  it('applies the same payload only once (replay safe)', () => {
    const p = payload([{ type: 'TOOL_CALL_START', toolCallId: 'a', toolCallName: 'coder-agent' }])
    const once = applyPayload(initialRun('t1'), p)
    const twice = applyPayload(once, p)
    expect(twice.toolCalls).toHaveLength(1)
    expect(twice).toEqual(once)
  })

  it('ignores overlapping events after a reconnect and applies only the new ones', () => {
    const first = applyPayload(initialRun('t1'), payload([
      { type: 'STEP_STARTED', stepName: 'plan' }, { type: 'STEP_FINISHED', stepName: 'plan' },
    ]))
    const overlap = payload([
      { type: 'STEP_FINISHED', stepName: 'plan' }, { type: 'STEP_STARTED', stepName: 'build' },
    ], 1)
    const s = applyPayload(first, overlap)
    expect(s.steps).toEqual({ plan: 'finished', build: 'running' })
    expect(s.lastSeq).toBe(2)
  })

  it('applies out-of-order events in sequence order', () => {
    const p = payload([{ type: 'STEP_STARTED', stepName: 'plan' }, { type: 'STEP_FINISHED', stepName: 'plan' }])
    p.events.reverse()
    expect(applyPayload(initialRun('t1'), p).steps.plan).toBe('finished')
  })

  it('parses a tool call result and tolerates garbage content', () => {
    let s = applyPayload(initialRun('t1'), payload([
      { type: 'TOOL_CALL_START', toolCallId: 'a', toolCallName: 'coder-agent' },
      { type: 'TOOL_CALL_END', toolCallId: 'a' },
      { type: 'TOOL_CALL_RESULT', toolCallId: 'a', content: JSON.stringify({ stage: 'build', summary: 'a diff' }) },
      { type: 'TOOL_CALL_START', toolCallId: 'b', toolCallName: 'qa-engineer' },
      { type: 'TOOL_CALL_RESULT', toolCallId: 'b', content: 'not json' },
    ]))
    expect(s.toolCalls[0]).toMatchObject({ id: 'a', status: 'done', stage: 'build', summary: 'a diff' })
    expect(s.toolCalls[1]).toMatchObject({ id: 'b', status: 'done', summary: '' })
    s = applyPayload(s, payload([{ type: 'TOOL_CALL_RESULT', toolCallId: 'zzz', content: '{}' }], 5))
    expect(s.toolCalls).toHaveLength(2)
  })

  it('shows the approval card, then clears it when resolved', () => {
    const asked = applyPayload(initialRun('t1'), payload([
      custom('approval.required', { approvalId: 't1:approve', node: 'approve', title: 'Approve?', planHash: 'sha256:aa' }),
    ], 0, { status: 'input_required' }))
    expect(asked.approval).toEqual({ id: 't1:approve', node: 'approve', title: 'Approve?', planHash: 'sha256:aa' })
    const done = applyPayload(asked, payload([custom('approval.resolved', { node: 'approve', approved: true })], 1))
    expect(done.approval).toBeNull()
  })

  it('records plan, seal, guard verdict, failures and safety decisions', () => {
    const s = applyPayload(initialRun('t1'), payload([
      custom('plan.created', { planHash: 'sha256:bb', steps: ['build'] }),
      custom('plan.sealed', { planHash: 'sha256:bb', performed: false }),
      custom('guard.verdict', { verdict: 'BLOCK', failedChecks: ['verifier_verdict'], bundleHash: 'sha256:cc' }),
      custom('step.failed', { node: 'build', reason: 'x' }),
      custom('safety.decision', { node: 'build', decision: 'ALLOW', reason: 'ok' }),
    ]))
    expect(s.planHash).toBe('sha256:bb')
    expect(s.sealed).toBe(true)
    expect(s.verdict).toEqual({ verdict: 'BLOCK', failedChecks: ['verifier_verdict'], bundleHash: 'sha256:cc' })
    expect(s.steps.build).toBe('failed')
    expect(s.safety).toEqual([{ node: 'build', decision: 'ALLOW', reason: 'ok' }])
  })

  it('caps the safety history', () => {
    const many = Array.from({ length: 30 }, (_, i) => custom('safety.decision', { node: `n${i}`, decision: 'ALLOW', reason: '' }))
    expect(applyPayload(initialRun('t1'), payload(many)).safety).toHaveLength(20)
  })

  it('stores a run error', () => {
    const s = applyPayload(initialRun('t1'), payload([{ type: 'RUN_ERROR', message: 'boom', code: 'RUN_FAILED' }], 0, { status: 'failed', done: true }))
    expect(s.error).toEqual({ message: 'boom', code: 'RUN_FAILED' })
    expect(s.done).toBe(true)
  })

  it('ignores unknown custom events and unknown event types', () => {
    const p = payload([custom('mystery', { a: 1 }), { type: 'FUTURE_EVENT' } as unknown as AguiEvent])
    const s = applyPayload(initialRun('t1'), p)
    expect(s.lastSeq).toBe(1)
    expect(s.steps).toEqual({})
  })

  it('always takes the latest snapshot (status, now, card, poll interval)', () => {
    const a = applyPayload(initialRun('t1'), payload([], 0, { now: 'A', calmCard: card({ status: 'running' }) }))
    const b = applyPayload(a, payload([], 0, { now: null, status: 'completed', done: true, pollInterval: null, calmCard: card({ status: 'done' }) }))
    expect(b).toMatchObject({ status: 'completed', done: true, now: null, pollInterval: null })
    expect(b.calmCard?.status).toBe('done')
  })

  it('switching to a different task starts clean', () => {
    const a = applyPayload(initialRun('t1'), payload([{ type: 'STEP_STARTED', stepName: 'plan' }]))
    const b = applyPayload(a, { ...payload([{ type: 'STEP_STARTED', stepName: 'build' }]), taskId: 't2' })
    expect(b.taskId).toBe('t2')
    expect(b.steps).toEqual({ build: 'running' })
  })

  it('reducer: reset clears everything, payload applies', () => {
    const a = runReducer(initialRun('t1'), { type: 'payload', payload: payload([{ type: 'STEP_STARTED', stepName: 'plan' }]) })
    expect(a.steps.plan).toBe('running')
    expect(runReducer(a, { type: 'reset', taskId: 't9' })).toEqual(initialRun('t9'))
  })
})
