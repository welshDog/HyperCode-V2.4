'use client'

import React, { useEffect, useMemo, useState } from 'react'
import { Pane } from '@/components/shell/Pane'
import { StreamFeed } from '@/components/studio/StreamFeed'
import { DiffPanel } from '@/components/studio/DiffPanel'
import { useToast } from '@/components/ui/ToastProvider'
import { useStudioSession, pendingApprovals, type StudioStatus, type StreamItem, type SessionMeta } from '@/hooks/useStudioSession'

// Golden-path examples so a first-time user isn't staring at a blank box. Each
// is a small, well-scoped, test-backed change — the shape Studio does best.
const SAMPLE_TASKS: string[] = [
  'Add a /healthz route that returns { ok: true } and a test that hits it.',
  'Rate-limit the /events route to 60 req/min per IP, with a test for the 429.',
  'Extract the retry/backoff logic in the worker into a helper + unit tests.',
]

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

  // Elapsed clock — ticks only while a run is in flight, freezes on settle.
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!s.startedAt || !running) return
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [s.startedAt, running])
  const elapsedMs = s.startedAt ? (running ? now : Math.max(now, s.startedAt)) - s.startedAt : 0

  const verdicts = useMemo(() => {
    const c = { ALLOW: 0, ESCALATE: 0, BLOCK: 0 }
    for (const it of s.stream) if (it.kind === 'decision') c[it.decision] = (c[it.decision] ?? 0) + 1
    return c
  }, [s.stream])

  const runCost = useMemo(() => {
    let total = 0
    for (const it of s.stream) if (it.kind === 'message' && typeof it.cost_usd === 'number') total += it.cost_usd
    return total
  }, [s.stream])

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

          {s.sessionId && (
            <RunHeader
              sessionId={s.sessionId}
              metaInfo={s.meta}
              elapsedMs={elapsedMs}
              verdicts={verdicts}
              costUsd={runCost}
            />
          )}

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
            {s.status === 'idle' && prompt.trim().length === 0 && (
              <button
                className="btn"
                type="button"
                onClick={() => setPrompt(SAMPLE_TASKS[Math.floor(Math.random() * SAMPLE_TASKS.length)])}
              >
                Try a sample
              </button>
            )}
            <span style={{ flex: 1 }} />
            <span style={{ color: 'var(--text-secondary)', fontSize: 10, opacity: 0.6 }}>⌘⏎</span>
          </div>

          {pending.map((ap) => (
            <ApprovalCard
              key={ap.approvalId}
              approval={ap}
              onRespond={async (id, decision) => {
                const ok = await s.respondApproval(id, decision)
                if (ok) {
                  toast({
                    variant: decision === 'approved' ? 'success' : 'info',
                    title: decision === 'approved' ? 'Approved' : 'Denied',
                    message: decision === 'approved' ? 'Letting the agent continue.' : 'Action blocked.',
                  })
                } else {
                  toast({
                    variant: 'error',
                    title: "Couldn't send",
                    message: "Your response didn't reach the studio — the request is still waiting. Try again.",
                  })
                }
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
  onRespond: (approvalId: string, decision: 'approved' | 'denied') => void | Promise<void>
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

function fmtElapsed(ms: number): string {
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`
}

function RunHeader({
  sessionId,
  metaInfo,
  elapsedMs,
  verdicts,
  costUsd,
}: {
  sessionId: string
  metaInfo: SessionMeta
  elapsedMs: number
  verdicts: { ALLOW: number; ESCALATE: number; BLOCK: number }
  costUsd: number
}): React.JSX.Element {
  const model = (metaInfo.model ?? '').replace(/^claude-/, '') || '—'
  const cell = { color: 'var(--text-secondary)' as const }
  const val = { color: 'var(--text-primary)' as const }
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '4px 12px',
        alignItems: 'center',
        padding: '6px 8px',
        borderRadius: 6,
        border: '1px solid var(--pane-border)',
        background: 'rgba(255,255,255,0.02)',
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
      }}
    >
      <span style={cell}>run <span style={val}>{sessionId.slice(0, 8)}</span></span>
      <span style={cell}>model <span style={val}>{model}</span></span>
      <span style={cell}>elapsed <span style={val}>{fmtElapsed(elapsedMs)}</span></span>
      <span style={cell}>
        shepherd{' '}
        <span style={{ color: 'var(--accent-green)' }}>✓{verdicts.ALLOW}</span>{' '}
        <span style={{ color: 'var(--accent-amber)' }}>⚠{verdicts.ESCALATE}</span>{' '}
        <span style={{ color: 'var(--accent-red)' }}>✗{verdicts.BLOCK}</span>
      </span>
      {costUsd > 0 && <span style={cell}>cost <span style={val}>${costUsd.toFixed(costUsd < 1 ? 3 : 2)}</span></span>}
      {(metaInfo.repo || metaInfo.branch || metaInfo.worktree) && (
        <span style={{ ...cell, flexBasis: '100%', opacity: 0.8 }}>
          {[metaInfo.repo, metaInfo.branch && `@ ${metaInfo.branch}`, metaInfo.worktree && `· ${metaInfo.worktree}`]
            .filter(Boolean)
            .join(' ')}
        </span>
      )}
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
