'use client'

import React from 'react'

// Per-task model choice for HyperStudio. `coder-studio` passes the id straight
// through to the Claude Code CLI (no allow-list), so any valid id works — this
// is the set worth offering in the UI.
//
// Cloud = hosted Claude, uses credits. Free / Local routes through the FCC proxy
// (`fcc-proxy:8083`, an Anthropic-compatible gateway → NVIDIA NIM / Ollama).
// The FCC backend path is not wired yet, so the Free group ships `enabled: false`
// — flip a single flag here once `coder-studio` routing lands.
export interface ModelOption {
  id: string
  label: string
  group: 'cloud' | 'free'
  badge: string
  note?: string
  enabled: boolean
}

export const MODELS: ModelOption[] = [
  { id: 'claude-sonnet-5', label: 'Sonnet 5', group: 'cloud', badge: 'Balanced', enabled: true, note: 'default — near-Opus on coding at a fraction of the cost' },
  { id: 'claude-opus-4-8', label: 'Opus 4.8', group: 'cloud', badge: 'Best', enabled: true, note: 'most capable' },
  { id: 'claude-haiku-4-5', label: 'Haiku 4.5', group: 'cloud', badge: 'Fast', enabled: true, note: 'fast & cheap' },
  { id: 'claude-fable-5', label: 'Fable 5', group: 'cloud', badge: 'Top tier', enabled: true, note: 'top tier' },
  {
    id: 'nvidia_nim/nvidia/nemotron-3-super-120b-a12b',
    label: 'Nemotron 3 Super 120B',
    group: 'free',
    badge: 'Free · Frontier',
    enabled: false,
    note: 'NVIDIA NIM · 40 req/min (best-effort) · the only free option that can run a full task',
  },
  {
    id: 'ollama/qwen3:4b',
    label: 'Qwen3 4B',
    group: 'free',
    badge: 'Free · Local',
    enabled: false,
    note: 'on-box · private · fine for smoke tests, often will not finish a full task',
  },
]

const GROUPS: { key: ModelOption['group']; label: string }[] = [
  { key: 'cloud', label: 'Cloud — Claude' },
  { key: 'free', label: 'Free / Local — needs FCC proxy (coming soon)' },
]

/** Friendly label for a model id — used in the run header. Falls back to the
 *  last path segment (FCC ids are `provider/vendor/model`), then the raw id. */
export function modelLabel(id: string | undefined | null): string {
  if (!id) return '—'
  const known = MODELS.find((m) => m.id === id)
  if (known) return known.label
  const seg = id.split('/').pop()
  return seg || id
}

export function ModelPicker({
  value,
  onChange,
  disabled = false,
}: {
  value: string
  onChange: (id: string) => void
  disabled?: boolean
}): React.JSX.Element {
  return (
    <label
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        color: 'var(--text-secondary)',
      }}
    >
      <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ letterSpacing: '0.06em', textTransform: 'uppercase', flexShrink: 0 }}>Model</span>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          style={{
            flex: 1,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid var(--pane-border)',
            borderRadius: 6,
            color: 'var(--text-primary)',
            padding: '6px 8px',
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            outline: 'none',
            cursor: disabled ? 'not-allowed' : 'pointer',
          }}
        >
          {GROUPS.map((g) => (
            <optgroup key={g.key} label={g.label}>
              {MODELS.filter((m) => m.group === g.key).map((m) => (
                <option
                  key={m.id}
                  value={m.id}
                  disabled={!m.enabled}
                  title={m.note}
                  style={{ background: 'var(--pane-bg)' }}
                >
                  {m.label} · {m.badge}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </span>
      <span style={{ fontSize: 9, opacity: 0.75, paddingLeft: 2 }}>
        Cloud = best quality, uses credits · Free / Local = slower, cheaper, private — wiring in progress
      </span>
    </label>
  )
}
