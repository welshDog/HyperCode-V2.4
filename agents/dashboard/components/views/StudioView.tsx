'use client'

import React, { useMemo, useState } from 'react'
import { Pane } from '@/components/shell/Pane'
import { StreamFeed } from '@/components/studio/StreamFeed'
import { DiffPanel } from '@/components/studio/DiffPanel'
import { useToast } from '@/components/ui/ToastProvider'
import { useStudioSession, pendingApprovals, type StudioStatus, type StreamItem } from '@/hooks/useStudioSession'

const STATUS_META: Record<StudioStatus, { label: string; color: string; live: boolean }> = {
  idle: { label: 'ready', color: 'var(--text-secondary)', live: false },
  pending: { label: 'starting', color: 'var(--accent-cyan)', live: true },
  running: { label: 'building', color: 'var(--accent-cyan)', live: true },
  review: { label: 'review the diff', color: 'var(--accent-amber)', live: false },
  merged: { label: 'merged', color: 'var(--accent-green)', live: false },
  discarded: { label: 'discarded', color: 'var(--text-secondary)', live: false },
  failed: { label: 'failed', color: 'var(--accent-red)', live: false },
}

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 32) || 'task'
}

// Per-task model choice. Sonnet is the default — near-Opus on coding at a
// fraction of the cost. The service accepts any valid id; these are the set
// worth offering in the UI.
const MODELS: { id: string; label: string }[] = [
  { id: 'claude-sonnet-5', label: 'Sonnet 5 · balanced (default)' },
  { id: 'claude-opus-4-8', label: 'Opus 4.8 · most capable' },
  { id: 'claude-haiku-4-5', label: 'Haiku 4.5 · fast & cheap' },
  { id: 'claude-fable-5', label: 'Fable 5 · top tier' },
]

export function StudioView(): React.JSX.Element {
  const [focus, setFocus] = useState<string | null>(null)
  const [prompt, setPrompt] = useState('')
  const [model, setModel] = useState(MODELS[0].id)
  const [merging, setMerging] = useState(false)
  const { toast } = useToast()
  const s = useStudioSession()

  const meta = STATUS_META[s.status]
  const running = s.status === 'running' || s.status === 'pending'
  const pending = useMemo(() => pendingApprovals(s.stream), [s.stream])

  const gridTemplate = focus
    ? `"${focus} ${focus} ${focus}" 1fr / 1fr 1fr 1fr`
    : `"task stream diff" 1fr / 340px 1fr 1fr`

  const submit = async () => {
    const p = prompt.trim()
    if (!p || running) return
    toast({ variant: 'info', title: 'Studio', message: 'Handing the task to the agent…' })
    await s.start(p, slugify(p), model)
  }

  const merge = async () => {
    setMerging(true)
    try {
      const result = await s.merge()
      if (result.ok) {
        toast({ variant: 'success', title: 'Merged', message: 'The change landed on the branch. Nice one!' })
      } else {
        // e.g. a merge collision — show the service's plain-language reason.
        toast({ variant: 'error', title: "Couldn't merge", message: result.detail ?? 'Merge failed.' })
      }
    } finally {
      setMerging(false)
    }
  }

  const discard = async () => {
    await s.discard()
    toast({ variant: 'info', title: 'Discarded', message: 'Worktree thrown away — nothing was written.' })
  }

  return (
    <div className="hyper-shell" style={{ gridTemplate }}>
      <Pane
        id="task"
        title="🏗️ Task"
        gridArea="task"
        focused={focus === 'task'}
        onFocusToggle={() => setFocus(focus === 'task' ? null : 'task')}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
          <StatusPill label={meta.label} color={meta.color} live={meta.live} />

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') submit()
            }}
            placeholder="Describe the change you want built — e.g. add a rate limit to the /events route and a test for it."
            rows={5}
            disabled={running}
            style={{
              resize: 'vertical',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--pane-border)',
              borderRadius: 6,
              color: 'var(--text-primary)',
              padding: '10px 12px',
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
              lineHeight: 1.6,
              outline: 'none',
            }}
          />

          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)' }}>
            <span style={{ letterSpacing: '0.06em', textTransform: 'uppercase', flexShrink: 0 }}>Model</span>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              disabled={running}
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
                cursor: running ? 'not-allowed' : 'pointer',
              }}
            >
              {MODELS.map((m) => (
                <option key={m.id} value={m.id} style={{ background: 'var(--pane-bg)' }}>{m.label}</option>
              ))}
            </select>
          </label>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              className="btn studio-build"
              type="button"
              onClick={submit}
              disabled={running || prompt.trim().length === 0}
            >
              {running ? 'Building…' : 'Build it'}
            </button>
            {(s.status !== 'idle' && !running) && (
              <button className="btn" type="button" onClick={s.reset}>New task</button>
            )}
            <span style={{ flex: 1 }} />
            <span style={{ color: 'var(--text-secondary)', fontSize: 10, opacity: 0.6 }}>⌘⏎</span>
          </div>

          {pending.map((ap) => (
            <ApprovalCard
              key={ap.approvalId}
              approval={ap}
              onRespond={(id, decision) => {
                void s.respondApproval(id, decision)
                toast({
                  variant: decision === 'approved' ? 'success' : 'info',
                  title: decision === 'approved' ? 'Approved' : 'Denied',
                  message: decision === 'approved' ? 'Letting the agent continue.' : 'Action blocked.',
                })
              }}
            />
          ))}

          {s.error && (
            <div className="studio-banner" style={{ borderColor: 'rgba(255,68,102,0.35)', background: 'rgba(255,68,102,0.08)' }}>
              <span style={{ color: 'var(--accent-red)' }}>✗ {s.error}</span>
            </div>
          )}

          <div style={{ flex: 1 }} />
          <p style={{ color: 'var(--text-secondary)', fontSize: 10, opacity: 0.55, lineHeight: 1.5, margin: 0 }}>
            The agent works in a throwaway git worktree. Nothing touches your working tree until you merge.
          </p>
        </div>
      </Pane>

      <Pane
        id="stream"
        title={s.connected ? '📡 Live · agent working' : '📡 Agent stream'}
        gridArea="stream"
        focused={focus === 'stream'}
        onFocusToggle={() => setFocus(focus === 'stream' ? null : 'stream')}
      >
        <StreamFeed items={s.stream} live={running} />
      </Pane>

      <Pane
        id="diff"
        title="🔍 Diff & Review"
        gridArea="diff"
        focused={focus === 'diff'}
        onFocusToggle={() => setFocus(focus === 'diff' ? null : 'diff')}
      >
        <DiffPanel
          diff={s.diff}
          status={s.status}
          mergeSha={s.mergeSha}
          onMerge={merge}
          onDiscard={discard}
          busy={merging}
        />
      </Pane>
    </div>
  )
}

type ApprovalItem = Extract<StreamItem, { kind: 'approval_request' }>

export function ApprovalCard({
  approval,
  onRespond,
}: {
  approval: ApprovalItem
  onRespond: (approvalId: string, decision: 'approved' | 'denied') => void
}): React.JSX.Element {
  return (
    <div
      className="studio-banner"
      role="group"
      aria-label="Action needs your approval"
      style={{ borderColor: 'rgba(255,170,0,0.35)', background: 'rgba(255,170,0,0.08)' }}
    >
      <span style={{ color: 'var(--accent-amber)' }}>⚠ Approval needed</span>
      <div style={{ color: 'var(--text-secondary)', fontSize: 10, marginTop: 4, fontFamily: 'var(--font-mono)' }}>
        <div><strong style={{ color: 'var(--text-primary)' }}>{approval.toolName}</strong> → {approval.target}</div>
        <div style={{ opacity: 0.8 }}>{approval.rule}: {approval.reason}</div>
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <button className="btn" type="button" onClick={() => onRespond(approval.approvalId, 'denied')}>
          Deny
        </button>
        <button className="btn studio-build" type="button" onClick={() => onRespond(approval.approvalId, 'approved')}>
          Approve
        </button>
      </div>
    </div>
  )
}

function StatusPill({ label, color, live }: { label: string; color: string; live: boolean }): React.JSX.Element {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, alignSelf: 'flex-start' }}>
      <span
        className={live ? 'studio-dot live' : 'studio-dot'}
        style={{ background: color }}
        aria-hidden
      />
      <span style={{ color, fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.03em' }}>
        {label}
      </span>
    </div>
  )
}
