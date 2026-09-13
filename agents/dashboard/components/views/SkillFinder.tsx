'use client'

import React, { useState } from 'react'

interface SkillMatch {
  name: string
  rationale: string
}

interface SkillSearchResponse {
  matches: SkillMatch[]
  usedFallback: boolean
  error: string | null
}

export function SkillFinder(): React.JSX.Element {
  const [goal, setGoal] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SkillSearchResponse | null>(null)
  const [copiedName, setCopiedName] = useState<string | null>(null)

  async function submit() {
    const trimmed = goal.trim()
    if (!trimmed || loading) return
    setLoading(true)
    try {
      const res = await fetch('/api/skills', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: trimmed }),
      })
      const data = (await res.json()) as SkillSearchResponse
      setResult(data)
    } catch {
      setResult({ matches: [], usedFallback: true, error: 'request failed' })
    } finally {
      setLoading(false)
    }
  }

  async function copyInvocation(name: string) {
    try {
      await navigator.clipboard.writeText(`/${name}`)
      setCopiedName(name)
      setTimeout(() => setCopiedName((c) => (c === name ? null : c)), 1500)
    } catch {
      // clipboard access denied — silently ignore, the text is still shown
    }
  }

  return (
    <div className="pane skill-finder">
      <div className="pane-header">
        <span className="pane-title">Find a skill</span>
      </div>
      <div className="pane-body">
        <div className="skill-finder-row">
          <input
            className="skill-finder-input"
            type="text"
            value={goal}
            placeholder="What are you trying to do? e.g. deploy a discord bot with moderation"
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') submit()
            }}
          />
          <button className="btn" onClick={submit} disabled={loading || !goal.trim()}>
            {loading ? 'Searching…' : 'Find a skill'}
          </button>
        </div>

        {result && (
          <div className="skill-finder-results">
            {result.usedFallback && (
              <div className="skill-finder-notice">
                {result.error ?? 'Showing substring matches (LLM ranking unavailable).'}
              </div>
            )}
            {result.matches.length === 0 ? (
              <div className="skill-finder-notice">No matching skills found.</div>
            ) : (
              result.matches.map((m) => (
                <div className="skill-card" key={m.name}>
                  <div className="skill-card-name hc-mono">{m.name}</div>
                  <div className="skill-card-rationale">{m.rationale}</div>
                  <button className="btn skill-card-copy" onClick={() => copyInvocation(m.name)}>
                    {copiedName === m.name ? 'Copied!' : `/${m.name}`}
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
