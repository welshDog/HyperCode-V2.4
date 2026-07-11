import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ApprovalCard } from './StudioView'

describe('ApprovalCard', () => {
  const approval = {
    kind: 'approval_request' as const, approvalId: 'ap_1', toolName: 'Write',
    target: 'config/prod.env', rule: 'unknown_tool', reason: 'needs a human',
    expiresAt: '2026-07-11T09:35:00Z', seq: 1,
  }

  it('shows the tool and target', () => {
    render(<ApprovalCard approval={approval} onRespond={vi.fn()} />)
    expect(screen.getByText(/config\/prod\.env/)).toBeTruthy()
    expect(screen.getByText(/Write/)).toBeTruthy()
  })

  it('calls onRespond with approved when Approve is clicked', () => {
    const onRespond = vi.fn()
    render(<ApprovalCard approval={approval} onRespond={onRespond} />)
    fireEvent.click(screen.getByRole('button', { name: /approve/i }))
    expect(onRespond).toHaveBeenCalledWith('ap_1', 'approved')
  })

  it('calls onRespond with denied when Deny is clicked', () => {
    const onRespond = vi.fn()
    render(<ApprovalCard approval={approval} onRespond={onRespond} />)
    fireEvent.click(screen.getByRole('button', { name: /deny/i }))
    expect(onRespond).toHaveBeenCalledWith('ap_1', 'denied')
  })
})
