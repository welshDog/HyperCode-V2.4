export type PatternDecision = 'accepted' | 'rejected' | 'deferred'

export type PatternEvidence = {
  path: string
  /** Schema 1: metadata fingerprint. Schema 2: alias of metadata_sha256. Never a file hash. */
  sha256: string
  metadata_sha256?: string
  /** Hash of the file with CRLF normalised to LF; null when withheld (secret-like or non-UTF-8 content). */
  content_sha256?: string | null
}
export type PatternCandidate = {
  candidate_id: string
  category: string
  claim: string
  evidence: PatternEvidence[]
  facts: Record<string, unknown>
  limitations: string[]
}

export type PatternReviewPacket = {
  schema_version: number
  document_type: string
  source: { kind: string; name: string }
  provenance: {
    approval_id: string
    approved_by: string
    approved_at: string
    inventory_sha256: string
    inventory_schema_version: number
    manifest_count: number
    extractor: string
  }
  review_status: string
  synthesis_authorized: boolean
  execution_authorized: boolean
  candidate_patterns: PatternCandidate[]
  review_instructions?: string[]
}

export type PatternDecisionRecord = {
  schema_version: 1
  document_type: 'hypercode.pattern-decisions.v1'
  source: PatternReviewPacket['source']
  provenance: PatternReviewPacket['provenance']
  review: {
    status: 'human_reviewed'
    reviewer: string
    reviewed_at: string
    unsigned: true
  }
  decisions: Array<{
    candidate_id: string
    candidate_sha256: string
    decision: PatternDecision
  }>
  synthesis_authorized: false
  execution_authorized: false
}

const SHA256 = /^[a-f0-9]{64}$/
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$/
const MAX_PACKET_BYTES = 1_000_000
const MAX_CANDIDATES = 250
const MAX_EVIDENCE = 80
const MAX_TEXT = 4_000

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function boundedText(value: unknown, label: string): string {
  if (typeof value !== 'string' || value.length === 0 || value.length > MAX_TEXT) {
    throw new Error(`${label} must be a non-empty string of at most ${MAX_TEXT} characters`)
  }
  return value
}

export function parsePatternReviewPacket(text: string): PatternReviewPacket {
  if (typeof text !== 'string' || text.length === 0 || new TextEncoder().encode(text).byteLength > MAX_PACKET_BYTES) {
    throw new Error('Review packet is empty or exceeds the 1 MB limit')
  }

  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    throw new Error('Review packet is not valid JSON')
  }
  if (!isRecord(raw)) throw new Error('Review packet must be a JSON object')
  if (raw.schema_version !== 1 || raw.document_type !== 'hypercode.pattern-review.v1') {
    throw new Error('Unsupported Pattern Foundry review packet format')
  }
  if (raw.review_status !== 'pending_human_review') throw new Error('Packet is not pending human review')
  if (raw.synthesis_authorized !== false || raw.execution_authorized !== false) {
    throw new Error('Packet must not authorize synthesis or execution')
  }

  const source = raw.source
  if (!isRecord(source) || source.kind !== 'local-directory') throw new Error('Packet source must be a local-directory')
  boundedText(source.name, 'source.name')

  const provenance = raw.provenance
  if (!isRecord(provenance)) throw new Error('Packet provenance is missing')
  for (const field of ['approval_id', 'approved_by', 'approved_at', 'extractor']) {
    boundedText(provenance[field], `provenance.${field}`)
  }
  if (typeof provenance.inventory_sha256 !== 'string' || !SHA256.test(provenance.inventory_sha256)) {
    throw new Error('provenance.inventory_sha256 must be a SHA-256 hex digest')
  }
  if (!Number.isInteger(provenance.inventory_schema_version) || !Number.isInteger(provenance.manifest_count) || Number(provenance.manifest_count) < 0) {
    throw new Error('Packet provenance counts or schema version are invalid')
  }

  if (!Array.isArray(raw.candidate_patterns) || raw.candidate_patterns.length > MAX_CANDIDATES) {
    throw new Error(`candidate_patterns must contain at most ${MAX_CANDIDATES} items`)
  }
  const seen = new Set<string>()
  const candidates = raw.candidate_patterns.map((item, index): PatternCandidate => {
    if (!isRecord(item)) throw new Error(`candidate_patterns[${index}] must be an object`)
    const candidateId = boundedText(item.candidate_id, `candidate_patterns[${index}].candidate_id`)
    if (!SAFE_ID.test(candidateId) || seen.has(candidateId)) throw new Error(`candidate id is unsafe or duplicated: ${candidateId}`)
    seen.add(candidateId)
    const evidence = item.evidence
    if (!Array.isArray(evidence) || evidence.length === 0 || evidence.length > MAX_EVIDENCE) {
      throw new Error(`candidate ${candidateId} must cite between 1 and ${MAX_EVIDENCE} evidence entries`)
    }
    const safeEvidence = evidence.map((ref, evidenceIndex) => {
      if (!isRecord(ref) || typeof ref.path !== 'string' || ref.path.startsWith('/') || ref.path.startsWith('\\\\') || ref.path.split(/[\\/]/).includes('..')) {
        throw new Error(`candidate ${candidateId} evidence[${evidenceIndex}] has an unsafe path`)
      }
      if (typeof ref.sha256 !== 'string' || !SHA256.test(ref.sha256)) throw new Error(`candidate ${candidateId} evidence[${evidenceIndex}] has an invalid digest`)
      // Schema 2 evidence: `sha256` is only an alias of metadata_sha256 (a hash of extracted facts, not the file).
      // content_sha256 is the file hash (CRLF normalised), or null when withheld. Old packets have neither.
      const extra: Partial<PatternEvidence> = {}
      if (ref.metadata_sha256 !== undefined) {
        if (typeof ref.metadata_sha256 !== 'string' || !SHA256.test(ref.metadata_sha256)) throw new Error(`candidate ${candidateId} evidence[${evidenceIndex}] has an invalid metadata digest`)
        extra.metadata_sha256 = ref.metadata_sha256
      }
      if (ref.content_sha256 !== undefined) {
        if (ref.content_sha256 !== null && (typeof ref.content_sha256 !== 'string' || !SHA256.test(ref.content_sha256))) throw new Error(`candidate ${candidateId} evidence[${evidenceIndex}] has an invalid content digest`)
        extra.content_sha256 = ref.content_sha256
      }
      return { path: ref.path, sha256: ref.sha256, ...extra }
    })
    const facts = item.facts
    const limitations = item.limitations
    if (!isRecord(facts) || !Array.isArray(limitations) || !limitations.every((entry) => typeof entry === 'string' && entry.length <= MAX_TEXT)) {
      throw new Error(`candidate ${candidateId} facts/limitations are invalid`)
    }
    return {
      candidate_id: candidateId,
      category: boundedText(item.category, `candidate ${candidateId}.category`),
      claim: boundedText(item.claim, `candidate ${candidateId}.claim`),
      evidence: safeEvidence,
      facts,
      limitations,
    }
  })

  return {
    schema_version: 1,
    document_type: 'hypercode.pattern-review.v1',
    source: { kind: 'local-directory', name: String(source.name) },
    provenance: {
      approval_id: String(provenance.approval_id),
      approved_by: String(provenance.approved_by),
      approved_at: String(provenance.approved_at),
      inventory_sha256: provenance.inventory_sha256,
      inventory_schema_version: Number(provenance.inventory_schema_version),
      manifest_count: Number(provenance.manifest_count),
      extractor: String(provenance.extractor),
    },
    review_status: 'pending_human_review',
    synthesis_authorized: false,
    execution_authorized: false,
    candidate_patterns: candidates,
    review_instructions: Array.isArray(raw.review_instructions) ? raw.review_instructions.filter((entry): entry is string => typeof entry === 'string').slice(0, 20) : [],
  }
}

function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalize)
  if (!isRecord(value)) return value
  return Object.fromEntries(
    Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]),
  )
}

export async function buildDecisionExport(
  packet: PatternReviewPacket,
  decisions: Record<string, PatternDecision>,
  reviewer: string,
  reviewedAt = new Date().toISOString(),
): Promise<PatternDecisionRecord> {
  const normalizedReviewer = reviewer.trim()
  if (!normalizedReviewer || normalizedReviewer.length > 120) throw new Error('Reviewer name is required (maximum 120 characters)')
  const digest = async (candidate: PatternCandidate): Promise<string> => {
    const bytes = new TextEncoder().encode(JSON.stringify(canonicalize(candidate)))
    const hash = await crypto.subtle.digest('SHA-256', bytes)
    return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, '0')).join('')
  }
  const entries = await Promise.all(packet.candidate_patterns.map(async (candidate) => ({
    candidate_id: candidate.candidate_id,
    candidate_sha256: await digest(candidate),
    decision: decisions[candidate.candidate_id] ?? 'deferred',
  })))
  return {
    schema_version: 1,
    document_type: 'hypercode.pattern-decisions.v1',
    source: packet.source,
    provenance: packet.provenance,
    review: { status: 'human_reviewed', reviewer: normalizedReviewer, reviewed_at: reviewedAt, unsigned: true },
    decisions: entries,
    synthesis_authorized: false,
    execution_authorized: false,
  }
}
