'use client'

import React, { ChangeEvent, useMemo, useState } from 'react'
import {
  buildDecisionExport,
  parsePatternReviewPacket,
  type PatternDecision,
  type PatternReviewPacket,
} from '@/lib/patternFoundry'

const DECISIONS: Array<{ value: PatternDecision; label: string }> = [
  { value: 'accepted', label: 'Accept for later synthesis' },
  { value: 'rejected', label: 'Reject this pattern' },
  { value: 'deferred', label: 'Defer review' },
]

export default function PatternReviewPage(): React.JSX.Element {
  const [packet, setPacket] = useState<PatternReviewPacket | null>(null)
  const [decisions, setDecisions] = useState<Record<string, PatternDecision>>({})
  const [reviewer, setReviewer] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loadedName, setLoadedName] = useState('')
  const [exporting, setExporting] = useState(false)

  const decisionCounts = useMemo(() => {
    const values = packet?.candidate_patterns.map((candidate) => decisions[candidate.candidate_id] ?? 'deferred') ?? []
    return {
      accepted: values.filter((value) => value === 'accepted').length,
      rejected: values.filter((value) => value === 'rejected').length,
      deferred: values.filter((value) => value === 'deferred').length,
    }
  }, [packet, decisions])

  async function loadPacket(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    setError(null)
    setPacket(null)
    setDecisions({})
    setLoadedName('')
    const file = event.currentTarget.files?.[0]
    event.currentTarget.value = ''
    if (!file) return
    if (file.size > 1_000_000) {
      setError('Packet exceeds the 1 MB import limit.')
      return
    }
    try {
      const parsed = parsePatternReviewPacket(await file.text())
      setPacket(parsed)
      setLoadedName(file.name)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not read this review packet.')
    }
  }

  async function exportDecisions(): Promise<void> {
    if (!packet) return
    setExporting(true)
    setError(null)
    try {
      const bundle = await buildDecisionExport(packet, decisions, reviewer)
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `${packet.source.name}-pattern-decisions.json`
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not export review decisions.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <main className="hyper-shell" aria-labelledby="pattern-review-title">
      <section className="pane" style={{ gridArea: '1 / 1 / auto / -1', maxWidth: 1120, width: '100%', margin: '24px auto' }}>
        <header className="pane-header">
          <div>
            <h1 id="pattern-review-title">🧪 Pattern Foundry · Review Desk</h1>
            <p>Inspect approved, evidence-linked architecture candidates before any future synthesis work.</p>
          </div>
        </header>
        <div className="pane-body" style={{ display: 'grid', gap: 18 }}>
          <div role="note" aria-label="Safety boundary" className="pane" style={{ padding: 14, borderColor: 'var(--pane-border)' }}>
            <strong>Review only. Nothing runs from this page.</strong>
            <p>Packets stay in this browser. No upload, model call, source checkout, build, deployment, or approval signature occurs here.</p>
          </div>

          <label className="btn" htmlFor="pattern-packet-file" style={{ width: 'fit-content', cursor: 'pointer' }}>
            Open Pattern Foundry review packet (JSON)
          </label>
          <input id="pattern-packet-file" aria-label="Open review packet JSON" type="file" accept="application/json,.json" onChange={loadPacket} />

          {error && <p role="alert" className="tag error">{error}</p>}

          {packet && (
            <>
              <section aria-label="Packet provenance" className="pane" style={{ padding: 16 }}>
                <h2>Source and provenance</h2>
                <dl>
                  <dt>Source</dt><dd>{packet.source.name}</dd>
                  <dt>Source approval</dt><dd>{packet.provenance.approved_by} · {packet.provenance.approval_id}</dd>
                  <dt>Inventory digest</dt><dd><code>{packet.provenance.inventory_sha256}</code></dd>
                  <dt>Manifests reviewed</dt><dd>{packet.provenance.manifest_count}</dd>
                  <dt>Packet</dt><dd>{loadedName} · {packet.review_status}</dd>
                </dl>
                <p><strong>Candidate decisions:</strong> {decisionCounts.accepted} accepted · {decisionCounts.rejected} rejected · {decisionCounts.deferred} deferred</p>
              </section>

              <section aria-label="Pattern candidates" style={{ display: 'grid', gap: 12 }}>
                <h2>Evidence-linked candidates ({packet.candidate_patterns.length})</h2>
                {packet.candidate_patterns.map((candidate) => (
                  <article key={candidate.candidate_id} className="pane" style={{ padding: 16 }}>
                    <header style={{ display: 'flex', gap: 12, justifyContent: 'space-between', flexWrap: 'wrap' }}>
                      <div>
                        <span className="tag idle">{candidate.category}</span>
                        <h3>{candidate.candidate_id}</h3>
                      </div>
                      <label>
                        Decision for this candidate
                        <select
                          aria-label={`Decision for ${candidate.candidate_id}`}
                          value={decisions[candidate.candidate_id] ?? 'deferred'}
                          onChange={(event) => setDecisions((previous) => ({ ...previous, [candidate.candidate_id]: event.target.value as PatternDecision }))}
                        >
                          {DECISIONS.map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
                        </select>
                      </label>
                    </header>
                    <p>{candidate.claim}</p>
                    <h4>Evidence</h4>
                    <ul>{candidate.evidence.map((item) => <li key={`${item.path}:${item.sha256}`}><code>{item.path}</code> · <code>{item.sha256}</code></li>)}</ul>
                    <h4>Extracted facts</h4>
                    <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(candidate.facts, null, 2)}</pre>
                    <h4>Limitations</h4>
                    <ul>{candidate.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
                  </article>
                ))}
              </section>

              <section className="pane" style={{ padding: 16 }} aria-label="Export decisions">
                <label htmlFor="pattern-reviewer">Reviewer name (local record only)</label>
                <input id="pattern-reviewer" value={reviewer} maxLength={120} onChange={(event) => setReviewer(event.target.value)} />
                <p>Export records choices and candidate hashes. It is unsigned and does not authorize synthesis or execution.</p>
                <button className="btn" type="button" disabled={!reviewer.trim() || exporting} onClick={exportDecisions}>
                  {exporting ? 'Preparing…' : 'Export unsigned decision record'}
                </button>
              </section>
            </>
          )}
        </div>
      </section>
    </main>
  )
}
