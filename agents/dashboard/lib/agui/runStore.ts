// Pure run store for AG-UI-shaped crew events. One reducer, no I/O, so it is trivial to test.
//
// Replay safety: events carry a sequence number and are only applied once, in order. Feeding the
// same payload twice, or a payload that overlaps what we already have (after a refresh or a
// dropped connection), changes nothing. The latest Calm Card / status snapshot always wins.

import type { CalmCardData, EventsPayload, SequencedEvent, TaskStatus } from './types'

export type StepState = 'running' | 'finished' | 'failed'

export interface ToolCall {
  id: string
  name: string
  status: 'running' | 'done'
  stage?: string
  summary?: string
}

export interface PendingApproval {
  id: string
  node: string
  title: string
  planHash: string
}

export interface GuardVerdict {
  verdict: string
  failedChecks: string[]
  bundleHash: string
}

export interface RunState {
  taskId: string | null
  lastSeq: number
  status: TaskStatus | 'idle'
  done: boolean
  paused: boolean
  now: string | null
  pollInterval: number | null
  calmCard: CalmCardData | null
  steps: Record<string, StepState>
  toolCalls: ToolCall[]
  approval: PendingApproval | null
  planHash: string | null
  sealed: boolean
  verdict: GuardVerdict | null
  safety: { node: string; decision: string; reason: string }[]
  error: { message: string; code: string } | null
}

const MAX_SAFETY = 20

export function initialRun(taskId: string | null = null): RunState {
  return {
    taskId, lastSeq: -1, status: 'idle', done: false, paused: false, now: null, pollInterval: null,
    calmCard: null, steps: {}, toolCalls: [], approval: null, planHash: null, sealed: false,
    verdict: null, safety: [], error: null,
  }
}

const str = (v: unknown): string => (typeof v === 'string' ? v : '')

function parseJson(text: string): Record<string, unknown> {
  try {
    const v: unknown = JSON.parse(text)
    return v && typeof v === 'object' ? (v as Record<string, unknown>) : {}
  } catch {
    return {}
  }
}

function applyEvent(state: RunState, { event }: SequencedEvent): RunState {
  switch (event.type) {
    case 'STEP_STARTED':
      return { ...state, steps: { ...state.steps, [event.stepName]: 'running' } }
    case 'STEP_FINISHED':
      return { ...state, steps: { ...state.steps, [event.stepName]: 'finished' } }
    case 'TOOL_CALL_START':
      return { ...state, toolCalls: [...state.toolCalls, { id: event.toolCallId, name: event.toolCallName, status: 'running' }] }
    case 'TOOL_CALL_RESULT': {
      const body = parseJson(event.content)
      return {
        ...state,
        toolCalls: state.toolCalls.map((c) =>
          c.id === event.toolCallId ? { ...c, status: 'done', stage: str(body.stage), summary: str(body.summary) } : c,
        ),
      }
    }
    case 'RUN_ERROR':
      return { ...state, error: { message: event.message, code: event.code } }
    case 'CUSTOM': {
      const v = event.value
      switch (event.name) {
        case 'hypercode.approval.required':
          return { ...state, approval: { id: str(v.approvalId), node: str(v.node), title: str(v.title), planHash: str(v.planHash) } }
        case 'hypercode.approval.resolved':
          return { ...state, approval: null }
        case 'hypercode.plan.created':
          return { ...state, planHash: str(v.planHash) || null }
        case 'hypercode.plan.sealed':
          return { ...state, sealed: true }
        case 'hypercode.guard.verdict':
          return {
            ...state,
            verdict: {
              verdict: str(v.verdict),
              failedChecks: Array.isArray(v.failedChecks) ? v.failedChecks.map(String) : [],
              bundleHash: str(v.bundleHash),
            },
          }
        case 'hypercode.step.failed':
          return { ...state, steps: { ...state.steps, [str(v.node)]: 'failed' } }
        case 'hypercode.safety.decision':
          return {
            ...state,
            safety: [...state.safety, { node: str(v.node), decision: str(v.decision), reason: str(v.reason) }].slice(-MAX_SAFETY),
          }
        default:
          return state // unknown custom events are ignored, never fatal
      }
    }
    default:
      return state // RUN_STARTED / RUN_FINISHED / TOOL_CALL_END carry nothing we need to store
  }
}

export function applyPayload(prev: RunState, payload: EventsPayload): RunState {
  // A different task starts clean: never mix two runs.
  let state = prev.taskId === payload.taskId ? prev : initialRun(payload.taskId)
  const fresh = payload.events.filter((e) => e.seq > state.lastSeq).sort((a, b) => a.seq - b.seq)
  for (const ev of fresh) {
    state = applyEvent(state, ev)
    state = { ...state, lastSeq: ev.seq }
  }
  return {
    ...state,
    status: payload.status,
    done: payload.done,
    paused: Boolean(payload.paused),
    now: payload.now,
    pollInterval: payload.pollInterval,
    calmCard: payload.calmCard,
  }
}

export function runReducer(state: RunState, action: { type: 'payload'; payload: EventsPayload } | { type: 'reset'; taskId: string | null }): RunState {
  return action.type === 'reset' ? initialRun(action.taskId) : applyPayload(state, action.payload)
}
