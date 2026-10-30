// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PatternReviewPage from '../app/pattern-review/page'

const validPacket = {
  schema_version: 1,
  document_type: 'hypercode.pattern-review.v1',
  source: { kind: 'local-directory', name: 'demo-repo' },
  provenance: {
    approval_id: 'approval-local-1',
    approved_by: 'local human',
    approved_at: '2026-10-27T12:00:00Z',
    inventory_sha256: 'a'.repeat(64),
    inventory_schema_version: 1,
    manifest_count: 1,
    extractor: 'scripts/pattern_review.py',
  },
  review_status: 'pending_human_review',
  synthesis_authorized: false,
  execution_authorized: false,
  candidate_patterns: [{
    candidate_id: 'compose-service-topology',
    category: 'service-architecture',
    claim: 'Compose declares a service relationship.',
    evidence: [{ path: 'docker-compose.yml', sha256: 'b'.repeat(64) }],
    facts: { service_names: ['api', 'redis'] },
    limitations: ['Static only.'],
  }],
}

describe('Pattern Foundry Dashboard review', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubGlobal('fetch', vi.fn())
  })

  it('loads a packet locally and records a candidate decision without network calls', async () => {
    render(<PatternReviewPage />)
    const file = new File([JSON.stringify(validPacket)], 'review.json', { type: 'application/json' })
    fireEvent.change(screen.getByLabelText('Open review packet JSON'), { target: { files: [file] } })

    expect(await screen.findByText('compose-service-topology')).toBeInTheDocument()
    expect(screen.getByText(/local human/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Decision for compose-service-topology'), { target: { value: 'accepted' } })
    expect(screen.getByLabelText('Decision for compose-service-topology')).toHaveValue('accepted')
    expect(fetch).not.toHaveBeenCalled()
    expect(screen.getByText(/No upload, model call, source checkout, build, deployment/)).toBeInTheDocument()
  })

  it('refuses invalid packet JSON and does not render candidate controls', async () => {
    render(<PatternReviewPage />)
    const bad = new File(['not json'], 'bad.json', { type: 'application/json' })
    fireEvent.change(screen.getByLabelText('Open review packet JSON'), { target: { files: [bad] } })
    expect(await screen.findByRole('alert')).toHaveTextContent('not valid JSON')
    expect(screen.queryByLabelText(/Decision for/)).not.toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })
})
