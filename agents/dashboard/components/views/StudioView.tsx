'use client'

import React, { useMemo, useState } from 'react'
import { Pane } from '@/components/shell/Pane'
import { StreamFeed } from '@/components/studio/StreamFeed'
import { DiffPanel } from '@/components/studio/DiffPanel'
import { useToast } from '@/components/ui/ToastProvider'
import { useStudioSession, type StudioStatus } from '@/hooks/useStudioSession'

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

export function StudioView(): React.JSX.Element {
  const [focus, setFocus] = useState<string | null>(null)
  const [prompt, setPrompt] = useState('')
  const [merging, setMerging] = useState(false)
  const { toast } = useToast()
  const s = useStudioSession()

  const meta = STATUS_META[s.status]
  const running = s.status === 'running' || s.status === 'pending'
  const escalations = useMemo(
    () => s.stream.filter((i) => i.kind === 'decision' && i.decision === 'ESCALATE'),
    [s.stream],
  )

  const gridTemplate = focus
    ? `"${focus} ${focus} ${focus}" 1fr / 1fr 1fr 1fr`
    : `"task stream diff" 1fr / 340px 1fr 1fr`

  const submit = async () => {
    const p = prompt.trim()
    if (!p || running) return
    toast({ variant: 'info', title: 'Studio', message: 'Handing the task to the agent…' })
    await s.start(p, slugify(p))
  }

  const merge = async () => {
    setMerging(true)
    try {
      await s.merge()
      toast({ variant: 'success', title: 'Merged', message: 'The change landed on the branch. Nice one!' })
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

          {escalations.length > 0 && (
            <div className="studio-banner" style={{ borderColor: 'rgba(255,170,0,0.35)', background: 'rgba(255,170,0,0.08)' }}>
              <span style={{ color: 'var(--accent-amber)' }}>
                ⚠ {escalations.length} action{escalations.length > 1 ? 's' : ''} needed approval and {escalations.length > 1 ? 'were' : 'was'} held.
              </span>
              <div style={{ color: 'var(--text-secondary)', fontSize: 10, marginTop: 4 }}>
                Interactive approval arrives in a later phase — for now these are denied so nothing risky slips through.
              </div>
            </div>
          )}

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
