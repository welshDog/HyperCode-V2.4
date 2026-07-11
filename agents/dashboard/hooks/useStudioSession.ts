'use client'

import { useCallback, useReducer, useRef } from 'react'

// The write-path lifecycle, mirroring coder-studio's session states.
export type StudioStatus =
  | 'idle'
  | 'pending'
  | 'running'
  | 'review'
  | 'merged'
  | 'discarded'
  | 'failed'

export type Decision = 'ALLOW' | 'BLOCK' | 'ESCALATE'

export type StreamItem =
  | { kind: 'message'; role: string; text?: string; tool?: string; input?: unknown; cost_usd?: number | null; seq: number }
  | { kind: 'decision'; tool: string; decision: Decision; reason: string; rule: string; seq: number }
  | { kind: 'status'; status: string; seq: number }
  | { kind: 'error'; error: string; seq: number }
  | { kind: 'approval_request'; approvalId: string; toolName: string; target: string; rule: string; reason: string; expiresAt: string; seq: number }
  | { kind: 'approval_resolved'; approvalId: string; status: string; seq: number }

interface State {
  sessionId: string | null
  status: StudioStatus
  connected: boolean
  stream: StreamItem[]
  diff: string
  mergeSha: string | null
  error: string | null
}

const initial: State = {
  sessionId: null,
  status: 'idle',
  connected: false,
  stream: [],
  diff: '',
  mergeSha: null,
  error: null,
}

type Action =
  | { type: 'start'; id: string }
  | { type: 'connected'; value: boolean }
  | { type: 'item'; item: StreamItem }
  | { type: 'status'; status: StudioStatus }
  | { type: 'diff'; diff: string }
  | { type: 'merged'; sha: string | null }
  | { type: 'discarded' }
  | { type: 'error'; error: string }
  | { type: 'reset' }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'start':
      return { ...initial, sessionId: action.id, status: 'pending' }
    case 'connected':
      return { ...state, connected: action.value }
    case 'item':
      return { ...state, stream: [...state.stream, action.item] }
    case 'status':
      return { ...state, status: action.status }
    case 'diff':
      return { ...state, diff: action.diff }
    case 'merged':
      return { ...state, status: 'merged', mergeSha: action.sha }
    case 'discarded':
      return { ...state, status: 'discarded' }
    case 'error':
      return { ...state, status: 'failed', error: action.error }
    case 'reset':
      return initial
    default:
      return state
  }
}

export function pendingApprovals(
  stream: StreamItem[],
): Extract<StreamItem, { kind: 'approval_request' }>[] {
  const resolved = new Set(
    stream.filter((i) => i.kind === 'approval_resolved').map((i) => (i as Extract<StreamItem, { kind: 'approval_resolved' }>).approvalId),
  )
  return stream.filter(
    (i): i is Extract<StreamItem, { kind: 'approval_request' }> =>
      i.kind === 'approval_request' && !resolved.has(i.approvalId),
  )
}

const TERMINAL: StudioStatus[] = ['review', 'merged', 'discarded', 'failed']
const KINDS = ['message', 'decision', 'status', 'error', 'approval_request', 'approval_resolved', 'end'] as const

/**
 * Drives one coder-studio session: POST to start, stream events over SSE,
 * fetch the diff when the run settles, then merge or discard.
 *
 * The SSE frames are NAMED events (event: decision, event: message, …), so
 * EventSource.onmessage never fires — each kind is wired with addEventListener.
 */
export function useStudioSession() {
  const [state, dispatch] = useReducer(reducer, initial)
  const esRef = useRef<EventSource | null>(null)
  const seqRef = useRef(0)
  const idemRef = useRef<string>('')

  const closeStream = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
  }, [])

  const openStream = useCallback((id: string) => {
    closeStream()
    const es = new EventSource(`/api/studio/sessions/${id}/events`)
    esRef.current = es
    es.onopen = () => dispatch({ type: 'connected', value: true })
    es.onerror = () => dispatch({ type: 'connected', value: false })

    const settle = async () => {
      try {
        const res = await fetch(`/api/studio/sessions/${id}/diff`)
        const data = await res.json()
        dispatch({ type: 'diff', diff: typeof data.diff === 'string' ? data.diff : '' })
        if (typeof data.status === 'string') dispatch({ type: 'status', status: data.status as StudioStatus })
      } catch {
        /* diff fetch is best-effort; the stream already carried the failure */
      }
    }

    for (const kind of KINDS) {
      es.addEventListener(kind, (evt) => {
        if (kind === 'end') {
          closeStream()
          dispatch({ type: 'connected', value: false })
          void settle()
          return
        }
        let data: Record<string, unknown> = {}
        try {
          data = JSON.parse((evt as MessageEvent).data)
        } catch {
          return
        }
        const seq = ++seqRef.current
        if (kind === 'status') {
          const s = String(data.status ?? '')
          dispatch({ type: 'item', item: { kind: 'status', status: s, seq } })
          if (TERMINAL.includes(s as StudioStatus)) dispatch({ type: 'status', status: s as StudioStatus })
        } else if (kind === 'decision') {
          dispatch({
            type: 'item',
            item: {
              kind: 'decision',
              tool: String(data.tool ?? ''),
              decision: (data.decision as Decision) ?? 'BLOCK',
              reason: String(data.reason ?? ''),
              rule: String(data.rule ?? ''),
              seq,
            },
          })
        } else if (kind === 'error') {
          dispatch({ type: 'item', item: { kind: 'error', error: String(data.error ?? 'unknown error'), seq } })
        } else if (kind === 'approval_request') {
          dispatch({
            type: 'item',
            item: {
              kind: 'approval_request',
              approvalId: String(data.approval_id ?? ''),
              toolName: String(data.tool_name ?? ''),
              target: String(data.target ?? ''),
              rule: String(data.rule ?? ''),
              reason: String(data.reason ?? ''),
              expiresAt: String(data.expires_at ?? ''),
              seq,
            },
          })
        } else if (kind === 'approval_resolved') {
          dispatch({
            type: 'item',
            item: { kind: 'approval_resolved', approvalId: String(data.approval_id ?? ''), status: String(data.status ?? ''), seq },
          })
        } else {
          dispatch({
            type: 'item',
            item: {
              kind: 'message',
              role: String(data.role ?? 'assistant'),
              text: typeof data.text === 'string' ? data.text : undefined,
              tool: typeof data.tool === 'string' ? data.tool : undefined,
              input: data.input,
              cost_usd: typeof data.cost_usd === 'number' ? data.cost_usd : null,
              seq,
            },
          })
        }
      })
    }
  }, [closeStream])

  const start = useCallback(async (prompt: string, slug: string, model?: string) => {
    seqRef.current = 0
    idemRef.current = crypto.randomUUID()
    const res = await fetch('/api/studio/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // model omitted → the service default (Sonnet); set → per-session override.
      body: JSON.stringify(model ? { prompt, slug, model } : { prompt, slug }),
    })
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}))
      dispatch({ type: 'error', error: detail.detail ?? detail.error ?? `start failed (${res.status})` })
      return
    }
    const data = await res.json()
    dispatch({ type: 'start', id: data.id })
    dispatch({ type: 'status', status: 'running' })
    openStream(data.id)
  }, [openStream])

  const merge = useCallback(async (): Promise<{ ok: boolean; detail?: string }> => {
    if (!state.sessionId) return { ok: false, detail: 'no active session' }
    const res = await fetch(`/api/studio/sessions/${state.sessionId}/merge`, {
      method: 'POST',
      headers: { 'Idempotency-Key': idemRef.current },
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok) {
      dispatch({ type: 'merged', sha: data.merge_sha ?? null })
      return { ok: true }
    }
    // Surface the service's human-readable reason (e.g. a merge collision).
    return { ok: false, detail: data.detail ?? data.error ?? `merge failed (${res.status})` }
  }, [state.sessionId])

  const discard = useCallback(async () => {
    if (!state.sessionId) return
    await fetch(`/api/studio/sessions/${state.sessionId}/discard`, { method: 'POST' })
    dispatch({ type: 'discarded' })
  }, [state.sessionId])

  const reset = useCallback(() => {
    closeStream()
    seqRef.current = 0
    dispatch({ type: 'reset' })
  }, [closeStream])

  const respondApproval = useCallback(
    async (approvalId: string, decision: 'approved' | 'denied') => {
      if (!state.sessionId) return
      await fetch(`/api/studio/sessions/${state.sessionId}/approvals/${approvalId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      })
    },
    [state.sessionId],
  )

  return { ...state, start, merge, discard, reset, respondApproval }
}
