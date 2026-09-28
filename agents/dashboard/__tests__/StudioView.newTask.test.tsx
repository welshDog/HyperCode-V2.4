import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeAll } from 'vitest'

// jsdom doesn't implement scrollIntoView; StreamFeed calls it unconditionally
// on mount to follow the tail of the stream.
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

const mockReset = vi.fn()
const mockUseStudioSession = vi.fn()

vi.mock('@/hooks/useStudioSession', () => ({
  useStudioSession: () => mockUseStudioSession(),
  pendingApprovals: () => [],
}))

import { StudioView } from '../components/views/StudioView'

function baseSession() {
  return {
    sessionId: 'cs_1',
    status: 'review',
    connected: false,
    stream: [],
    diff: 'diff --git a/x b/x\n+hi',
    mergeSha: null,
    error: null,
    start: vi.fn(),
    merge: vi.fn(),
    discard: vi.fn(),
    reset: mockReset,
    respondApproval: vi.fn(),
  }
}

describe('StudioView "New task"', () => {
  it('clears the stale prompt text and resets the session', () => {
    mockUseStudioSession.mockReturnValue(baseSession())
    render(<StudioView />)

    const textarea = screen.getByLabelText('Task description')
    fireEvent.change(textarea, { target: { value: 'Add a rate limit to /events' } })

    const newTaskBtn = screen.getByRole('button', { name: /new task/i })
    fireEvent.click(newTaskBtn)

    expect(mockReset).toHaveBeenCalledTimes(1)
    expect(textarea).toHaveValue('')
  })
})
