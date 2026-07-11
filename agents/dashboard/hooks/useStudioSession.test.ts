import { describe, it, expect } from 'vitest'
import { pendingApprovals, type StreamItem } from './useStudioSession'

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
