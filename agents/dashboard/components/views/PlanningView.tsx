'use client'

import React, { useState } from 'react'

interface PlanPhase {
  phase_number: number
  title: string
  description: string
  workflow_steps: string[]
}

interface FileChange {
  file_path: string
  change_type: 'create' | 'modify' | 'delete'
  description: string
}

interface GeneratedPlan {
  summary: string
  phases: PlanPhase[]
  file_changes_summary: FileChange[]
  follow_up_instructions?: string
}

const CHANGE_COLOUR = {
  create: 'var(--status-healthy)',
  modify: 'var(--accent-amber)',
  delete: 'var(--status-error)',
}

export function PlanningView(): React.JSX.Element {
  const [input, setInput]     = useState('')
  const [docType, setDocType] = useState<'prd' | 'issue' | 'design' | 'generic'>('generic')
  const [loading, setLoading] = useState(false)
  const [plan, setPlan]       = useState<GeneratedPlan | null>(null)
  const [error, setError]     = useState<string | null>(null)

  const handleGenerate = async () => {
    if (!input.trim()) return
    setLoading(true)
    setError(null)
    setPlan(null)

    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
      const res = await fetch('/api/planning', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          document: { content: input.trim(), document_type: docType },
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? `HTTP ${res.status}`)
      }

      const data = await res.json()
      // Response may be { plan: ... } or the plan directly
      setPlan(data.plan ?? data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Plan generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, height: '100%', overflow: 'hidden' }}
         data-testid="planning-view">

      {/* Input area */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'flex-start' }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Paste your PRD, issue, or design doc here…"
          rows={4}
          style={{
            flex: 1,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid var(--pane-border)',
            borderRadius: 4,
            color: 'var(--text-primary)',
            padding: '6px 8px',
            fontSize: 11,
            fontFamily: 'var(--font-mono)',
            resize: 'vertical',
            outline: 'none',
          }}
        />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value as typeof docType)}
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--pane-border)',
              borderRadius: 4,
              color: 'var(--text-primary)',
              padding: '4px 6px',
              fontSize: 10,
            }}
          >
            <option value="generic">Generic</option>
            <option value="prd">PRD</option>
            <option value="issue">Issue</option>
            <option value="design">Design</option>
          </select>
          <button
            onClick={handleGenerate}
            disabled={loading || !input.trim()}
            style={{
              background: loading ? 'rgba(255,255,255,0.1)' : 'var(--accent-cyan)',
              color: loading ? 'var(--text-secondary)' : '#000',
              border: 'none',
              borderRadius: 4,
              padding: '5px 10px',
              fontSize: 11,
              fontWeight: 700,
              cursor: loading || !input.trim() ? 'wait' : 'pointer',
              opacity: !input.trim() ? 0.4 : 1,
            }}
          >
            {loading ? '⚙️ Generating…' : '🧠 Generate Plan'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          background: 'rgba(239,68,68,0.1)',
          border: '1px solid var(--status-error)',
          borderRadius: 4,
          padding: '6px 10px',
          fontSize: 11,
          color: 'var(--status-error)',
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Plan output */}
      {plan && (
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* Summary */}
          <div style={{
            background: 'rgba(6,182,212,0.08)',
            border: '1px solid var(--accent-cyan)',
            borderRadius: 5,
            padding: '8px 10px',
            fontSize: 11,
            color: 'var(--text-primary)',
          }}>
            <div style={{ fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: 4 }}>📋 Summary</div>
            {plan.summary}
          </div>

          {/* Phases */}
          {plan.phases?.length > 0 && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 4, textTransform: 'uppercase' }}>
                Phases ({plan.phases.length})
              </div>
              {plan.phases.map((phase) => (
                <div key={phase.phase_number} style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid var(--pane-border)',
                  borderRadius: 5,
                  padding: '6px 8px',
                  marginBottom: 4,
                }}>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 3 }}>
                    <span style={{
                      background: 'var(--accent-purple)',
                      color: '#fff',
                      borderRadius: 3,
                      padding: '1px 5px',
                      fontSize: 9,
                      fontWeight: 700,
                    }}>
                      {phase.phase_number}
                    </span>
                    <span style={{ fontWeight: 600, fontSize: 11 }}>{phase.title}</span>
                  </div>
                  <p style={{ fontSize: 10, color: 'var(--text-secondary)', margin: '0 0 4px 0' }}>
                    {phase.description}
                  </p>
                  {phase.workflow_steps?.length > 0 && (
                    <ul style={{ margin: 0, paddingLeft: 16, fontSize: 10, color: 'var(--text-secondary)' }}>
                      {phase.workflow_steps.map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* File changes */}
          {plan.file_changes_summary?.length > 0 && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 4, textTransform: 'uppercase' }}>
                File Changes ({plan.file_changes_summary.length})
              </div>
              {plan.file_changes_summary.map((fc, i) => (
                <div key={i} style={{
                  display: 'flex',
                  gap: 6,
                  alignItems: 'flex-start',
                  padding: '3px 0',
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                  fontSize: 10,
                }}>
                  <span style={{
                    color: CHANGE_COLOUR[fc.change_type] ?? 'var(--text-secondary)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    flexShrink: 0,
                    width: 44,
                  }}>
                    {fc.change_type}
                  </span>
                  <span style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)', flex: 1 }}>
                    {fc.file_path}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Follow-up */}
          {plan.follow_up_instructions && (
            <div style={{
              background: 'rgba(168,85,247,0.08)',
              border: '1px solid rgba(168,85,247,0.3)',
              borderRadius: 5,
              padding: '6px 8px',
              fontSize: 10,
              color: 'var(--text-secondary)',
              whiteSpace: 'pre-wrap',
            }}>
              <div style={{ fontWeight: 700, color: 'var(--accent-purple)', marginBottom: 4 }}>🔮 Follow-up Instructions</div>
              {plan.follow_up_instructions}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
