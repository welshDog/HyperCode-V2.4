import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

const mockUseSafetyFeed = vi.fn()
vi.mock('../hooks/useSafetyFeed', () => ({
  useSafetyFeed: () => mockUseSafetyFeed(),
}))

import SafetyFeedPanel from '../components/panels/SafetyFeedPanel'

describe('SafetyFeedPanel', () => {
  it('renders verdicts with decision badges', () => {
    mockUseSafetyFeed.mockReturnValue({
      events: [
        {
          id: 'e1',
          ts: '2026-07-12T10:00:00Z',
          agent: 'coder_studio',
          category: 'file_write',
          tool: 'edit',
          decision: 'ALLOW',
        },
        {
          id: 'e2',
          ts: '2026-07-12T10:01:00Z',
          agent: 'qa-engineer',
          category: 'docker',
          decision: 'BLOCK',
          reason: 'docker writes denied',
        },
        {
          id: 'e3',
          ts: '2026-07-12T10:02:00Z',
          agent: 'coder',
          category: 'http_external',
          decision: 'ESCALATE',
          approval_id: 'ap-1',
        },
      ],
      error: null,
      loading: false,
    })
    render(<SafetyFeedPanel />)

    expect(screen.getByText('ALLOW')).toBeInTheDocument()
    expect(screen.getByText('BLOCK')).toBeInTheDocument()
    expect(screen.getByText('docker writes denied')).toBeInTheDocument()
    expect(screen.getByText('awaiting human')).toBeInTheDocument()
  })

  it('shows the human empty state', () => {
    mockUseSafetyFeed.mockReturnValue({ events: [], error: null, loading: false })
    render(<SafetyFeedPanel />)
    expect(
      screen.getByText('No verdicts yet — the Shepherd is watching.')
    ).toBeInTheDocument()
  })

  it('shows the shepherd error state', () => {
    mockUseSafetyFeed.mockReturnValue({ events: [], error: 'down', loading: false })
    render(<SafetyFeedPanel />)
    expect(screen.getByRole('alert')).toHaveTextContent('Shepherd unreachable: down')
  })
})
