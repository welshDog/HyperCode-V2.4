// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { buildDecisionExport, parsePatternReviewPacket } from '../lib/patternFoundry'

const digest = 'a'.repeat(64)
const candidateHash = 'b'.repeat(64)
const packet = {
  schema_version: 1,
  document_type: 'hypercode.pattern-review.v1',
  source: { kind: 'local-directory', name: 'fleet-controller' },
  provenance: {
    approval_id: 'approval-local-1',
    approved_by: 'human reviewer',
    approved_at: '2026-10-27T12:00:00Z',
    inventory_sha256: digest,
    inventory_schema_version: 1,
    manifest_count: 2,
    extractor: 'scripts/pattern_review.py',
  },
  review_status: 'pending_human_review',
  synthesis_authorized: false,
  execution_authorized: false,
  candidate_patterns: [{
    candidate_id: 'compose-service-topology',
    category: 'service-architecture',
    claim: 'Compose defines service relationships for review.',
    evidence: [{ path: 'docker-compose.yml', sha256: candidateHash }],
    facts: { services: ['fleet-controller', 'mission-director'] },
    limitations: ['Static configuration does not prove runtime behavior.'],
  }],
}

function validPacketText(): string { return JSON.stringify(packet) }

describe('Pattern Foundry review packet parser', () => {
  it('accepts a well-formed pending review packet', () => {
    expect(parsePatternReviewPacket(validPacketText()).candidate_patterns).toHaveLength(1)
  })

  it('rejects a packet claiming synthesis or execution authority', () => {
    expect(() => parsePatternReviewPacket(JSON.stringify({ ...packet, execution_authorized: true }))).toThrow(/must not authorize/)
  })

  it('rejects traversal evidence paths', () => {
    const bad = structuredClone(packet)
    bad.candidate_patterns[0].evidence[0].path = '../secrets/.env'
    expect(() => parsePatternReviewPacket(JSON.stringify(bad))).toThrow(/unsafe path/)
  })

  it('rejects duplicate candidate identifiers', () => {
    const bad = structuredClone(packet)
    bad.candidate_patterns.push(structuredClone(bad.candidate_patterns[0]))
    expect(() => parsePatternReviewPacket(JSON.stringify(bad))).toThrow(/duplicated/)
  })

  it('rejects packets over one megabyte', () => {
    expect(() => parsePatternReviewPacket(' '.repeat(1_000_001))).toThrow(/1 MB/)
  })

  describe('schema 2 evidence (metadata vs content hashes)', () => {
    const withEvidence = (evidence: unknown): string =>
      JSON.stringify({ ...packet, candidate_patterns: [{ ...packet.candidate_patterns[0], evidence: [evidence] }] })
    const fileHash = 'c'.repeat(64)

    it('keeps old packets exactly as before: no new keys appear', () => {
      const parsed = parsePatternReviewPacket(validPacketText())
      expect(parsed.candidate_patterns[0].evidence).toEqual([{ path: 'docker-compose.yml', sha256: candidateHash }])
    })

    it('passes metadata_sha256 and content_sha256 through', () => {
      const parsed = parsePatternReviewPacket(withEvidence({ path: 'Dockerfile', sha256: digest, metadata_sha256: digest, content_sha256: fileHash }))
      expect(parsed.candidate_patterns[0].evidence[0]).toEqual({ path: 'Dockerfile', sha256: digest, metadata_sha256: digest, content_sha256: fileHash })
    })

    it('accepts a withheld (null) content hash', () => {
      const parsed = parsePatternReviewPacket(withEvidence({ path: 'docker-compose.yml', sha256: digest, metadata_sha256: digest, content_sha256: null }))
      expect(parsed.candidate_patterns[0].evidence[0].content_sha256).toBeNull()
    })

    it.each([
      [{ path: 'a', sha256: digest, metadata_sha256: 'nothex' }, /invalid metadata digest/],
      [{ path: 'a', sha256: digest, content_sha256: 'nothex' }, /invalid content digest/],
      [{ path: 'a', sha256: digest, content_sha256: 42 }, /invalid content digest/],
    ])('rejects malformed fingerprints %#', (evidence, message) => {
      expect(() => parsePatternReviewPacket(withEvidence(evidence))).toThrow(message)
    })

    it('does not carry unknown evidence keys through', () => {
      const parsed = parsePatternReviewPacket(withEvidence({ path: 'a', sha256: digest, raw_source: 'print(1)' }))
      expect(JSON.stringify(parsed)).not.toContain('raw_source')
    })
  })
})

describe('Pattern Foundry decision export', () => {
  it('exports per-candidate decisions with hashes and keeps all downstream authority disabled', async () => {
    const parsed = parsePatternReviewPacket(validPacketText())
    const bundle = await buildDecisionExport(parsed, { 'compose-service-topology': 'accepted' }, 'Bro')
    expect(bundle.review.status).toBe('human_reviewed')
    expect(bundle.review.unsigned).toBe(true)
    expect(bundle.decisions[0].candidate_sha256).toMatch(/^[a-f0-9]{64}$/)
    expect(bundle.decisions[0].decision).toBe('accepted')
    expect(bundle.synthesis_authorized).toBe(false)
    expect(bundle.execution_authorized).toBe(false)
  })

  it('defaults unreviewed candidates to deferred', async () => {
    const bundle = await buildDecisionExport(parsePatternReviewPacket(validPacketText()), {}, 'Bro')
    expect(bundle.decisions[0].decision).toBe('deferred')
  })

  it('fingerprints the same candidate identically regardless of JSON key ordering', async () => {
    const parsed = parsePatternReviewPacket(validPacketText())
    const reordered = structuredClone(parsed)
    reordered.candidate_patterns[0] = Object.fromEntries(
      Object.entries(reordered.candidate_patterns[0]).reverse(),
    ) as typeof reordered.candidate_patterns[number]
    const first = await buildDecisionExport(parsed, {}, 'Bro')
    const second = await buildDecisionExport(reordered, {}, 'Bro')
    expect(first.decisions[0].candidate_sha256).toBe(second.decisions[0].candidate_sha256)
  })

  it('requires a reviewer label before export', async () => {
    await expect(buildDecisionExport(parsePatternReviewPacket(validPacketText()), {}, '  ')).rejects.toThrow(/Reviewer name is required/)
  })
})
