'use client'

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Pane } from '@/components/shell/Pane'
import { MetricsView } from '@/components/views/MetricsView'
import { BROskiPulseView } from '@/components/views/BROskiPulseView'
import { useToast } from '@/components/ui/ToastProvider'

type FileEntry = { name: string; path: string; type: 'file' | 'directory' }

function asRecord(v: unknown): Record<string, unknown> | null {
  return v && typeof v === 'object' ? (v as Record<string, unknown>) : null
}

function normalizeEntries(payload: unknown): FileEntry[] {
  const obj = asRecord(payload)
  const result = asRecord(obj?.result)
  const raw = (result?.entries ?? obj?.entries ?? obj?.result ?? []) as unknown
  if (!Array.isArray(raw)) return []
  return raw
    .filter((e) => e && typeof e === 'object')
    .map((e) => {
      const entry = e as Record<string, unknown>
      const name = typeof entry.name === 'string'
        ? entry.name
        : typeof entry.path === 'string'
          ? entry.path
          : 'unknown'
      const path = typeof entry.path === 'string' ? entry.path : ''
      const type: FileEntry['type'] = entry.type === 'directory' ? 'directory' : 'file'
      return { name, path, type }
    })
    .filter((e) => e.path)
}

export function IDEView(): React.JSX.Element {
  const [focusedPaneId, setFocusedPaneId] = useState<string | null>(null)
  const [cwd, setCwd] = useState('/workspace')
  const [entries, setEntries] = useState<FileEntry[]>([])
  const [fileTreeError, setFileTreeError] = useState<string | null>(null)
  const [selected, setSelected] = useState<FileEntry | null>(null)
  const [editorText, setEditorText] = useState<string>('Select a file to view details.')
  const [terminalInput, setTerminalInput] = useState('')
  const [terminalLog, setTerminalLog] = useState<string[]>([])
  const { toast } = useToast()

  const gridTemplate = focusedPaneId
    ? `"${focusedPaneId} ${focusedPaneId} ${focusedPaneId}" 1fr / 1fr 1fr 1fr`
    : `
        "files editor side"    1fr
        "terminal terminal side" 260px
        / 300px 1fr 380px
      `

  const fetchDir = useCallback(async (path: string) => {
    setFileTreeError(null)
    toast({ variant: 'info', title: 'Loading directory', message: path })
    const controller = new AbortController()
    const t = setTimeout(() => controller.abort(), 5_000)
    try {
      const res = await fetch('/api/mcp/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: 'filesystem:list_directory', params: { path } }),
        signal: controller.signal,
      })
      const data: unknown = await res.json().catch(() => ({}))
      const items = normalizeEntries(data)
      setEntries(items)
      if (!res.ok) {
        setFileTreeError('Filesystem tools unavailable (MCP adapter offline).')
        toast({ variant: 'error', title: 'Directory load failed', message: 'Filesystem tools unavailable (MCP adapter offline).' })
      } else if (items.length === 0) {
        setFileTreeError('No files returned. /workspace may not be mounted in the container.')
        toast({ variant: 'error', title: 'No files returned', message: '/workspace may not be mounted in the container.' })
      } else {
        toast({ variant: 'success', title: 'Directory loaded', message: `${items.length} entries` })
      }
    } catch (err) {
      if (controller.signal.aborted) return
      setEntries([])
      const msg = err instanceof Error ? err.message : String(err)
      setFileTreeError(msg)
      toast({ variant: 'error', title: 'Directory load failed', message: msg })
    } finally {
      clearTimeout(t)
      controller.abort()
    }
  }, [toast])

  useEffect(() => {
    fetchDir(cwd).catch(() => setEntries([]))
  }, [cwd, fetchDir])

  const sortedEntries = useMemo(() => {
    return [...entries].sort((a, b) => {
      if (a.type !== b.type) return a.type === 'directory' ? -1 : 1
      return a.name.localeCompare(b.name)
    })
  }, [entries])

  const openEntry = useCallback(async (e: FileEntry) => {
    setSelected(e)
    if (e.type === 'directory') {
      setCwd(e.path)
      setEditorText(`Directory: ${e.path}`)
      toast({ variant: 'info', title: 'Changed directory', message: e.path })
      return
    }

    setEditorText(`Loading: ${e.path}`)
    try {
      toast({ variant: 'info', title: 'Opening file', message: e.path })
      const res = await fetch('/api/mcp/tools/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: 'filesystem:read_file', params: { path: e.path } }),
      })
      const data: unknown = await res.json().catch(() => ({}))
      if (!res.ok) {
        toast({ variant: 'error', title: 'File open failed', message: `${res.status} ${res.statusText}`.trim() })
      } else {
        toast({ variant: 'success', title: 'File opened', message: e.path })
      }
      const obj = asRecord(data)
      const result = asRecord(obj?.result)
      const content = (result?.content ?? obj?.content ?? obj?.result) as unknown
      if (typeof content === 'string') {
        setEditorText(content)
      } else {
        setEditorText(JSON.stringify(data, null, 2))
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setEditorText(msg)
      toast({ variant: 'error', title: 'File open failed', message: msg })
    }
  }, [toast])

  const runTerminal = useCallback(async () => {
    const line = terminalInput.trim()
    if (!line) return
    setTerminalLog((prev) => [...prev, `> ${line}`])
    setTerminalInput('')

    try {
      toast({ variant: 'info', title: 'Sending task', message: line })
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
      const res = await fetch('/api/orchestrator', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ description: line, type: 'terminal', agent: 'coder-agent', requires_approval: false }),
      })
      const data: unknown = await res.json().catch(() => ({}))
      setTerminalLog((prev) => [...prev, JSON.stringify(data, null, 2)])
      if (!res.ok) {
        toast({ variant: 'error', title: 'Task failed', message: `${res.status} ${res.statusText}`.trim() })
      } else {
        toast({ variant: 'success', title: 'Task sent', message: line })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setTerminalLog((prev) => [...prev, msg])
      toast({ variant: 'error', title: 'Task failed', message: msg })
    }
  }, [toast, terminalInput])

  return (
    <div className="hyper-shell" style={{ gridTemplate }}>
      <Pane
        id="files"
        title={`📁 Files (${cwd})`}
        gridArea="files"
        focused={focusedPaneId === 'files'}
        onFocusToggle={() => setFocusedPaneId(focusedPaneId === 'files' ? null : 'files')}
      >
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 8 }}>
          <button className="btn" onClick={() => setCwd('/workspace')}>/workspace</button>
          <button className="btn" onClick={() => setCwd('/')}>/</button>
        </div>
        {fileTreeError && (
          <div style={{
            background: 'rgba(255,170,0,0.08)',
            border: '1px solid rgba(255,170,0,0.35)',
            borderRadius: 6,
            padding: '8px 10px',
            fontSize: 10,
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-mono)',
            marginBottom: 8,
          }}>
            ⚠️ {fileTreeError}
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {sortedEntries.map((e) => (
            <button
              key={e.path}
              onClick={() => openEntry(e)}
              style={{
                textAlign: 'left',
                border: '1px solid rgba(255,255,255,0.06)',
                background: selected?.path === e.path ? 'rgba(192,38,211,0.10)' : 'rgba(255,255,255,0.02)',
                color: 'var(--text-primary)',
                borderRadius: 6,
                padding: '8px 10px',
                cursor: 'pointer',
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
              }}
            >
              <span style={{ color: e.type === 'directory' ? 'var(--accent-cyan)' : 'var(--text-secondary)' }}>
                {e.type === 'directory' ? 'dir' : 'file'}
              </span>{' '}
              {e.name}
            </button>
          ))}
          {sortedEntries.length === 0 && (
            <div style={{ color: 'var(--text-secondary)', padding: 12 }}>No entries</div>
          )}
        </div>
      </Pane>

      <Pane
        id="editor"
        title={`🧠 Editor${selected?.path ? ` — ${selected.path}` : ''}`}
        gridArea="editor"
        focused={focusedPaneId === 'editor'}
        onFocusToggle={() => setFocusedPaneId(focusedPaneId === 'editor' ? null : 'editor')}
      >
        <pre style={{
          margin: 0,
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
          color: 'var(--text-primary)',
          whiteSpace: 'pre',
        }}>
          {editorText}
        </pre>
      </Pane>

      <Pane
        id="terminal"
        title="💻 Terminal (Orchestrator Task Runner)"
        gridArea="terminal"
        focused={focusedPaneId === 'terminal'}
        onFocusToggle={() => setFocusedPaneId(focusedPaneId === 'terminal' ? null : 'terminal')}
      >
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <input
            value={terminalInput}
            onChange={(e) => setTerminalInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') runTerminal() }}
            placeholder="Describe what you want an agent to do…"
            style={{
              flex: 1,
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--pane-border)',
              borderRadius: 6,
              color: 'var(--text-primary)',
              padding: '8px 10px',
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
              outline: 'none',
            }}
          />
          <button className="btn" onClick={runTerminal}>Run</button>
        </div>
        <pre style={{
          margin: 0,
          padding: '10px 12px',
          borderRadius: 6,
          background: 'rgba(0,0,0,0.35)',
          border: '1px solid rgba(255,255,255,0.06)',
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
          overflow: 'auto',
          height: '100%',
          whiteSpace: 'pre-wrap',
        }}>
          {terminalLog.join('\n')}
        </pre>
      </Pane>

      <Pane
        id="side"
        title="🦅 BROski + Metrics"
        gridArea="side"
        focused={focusedPaneId === 'side'}
        onFocusToggle={() => setFocusedPaneId(focusedPaneId === 'side' ? null : 'side')}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ border: '1px solid rgba(255,255,255,0.06)', borderRadius: 6, padding: 10, background: 'rgba(255,255,255,0.02)' }}>
            <MetricsView />
          </div>
          <div style={{ border: '1px solid rgba(255,255,255,0.06)', borderRadius: 6, padding: 10, background: 'rgba(255,255,255,0.02)' }}>
            <BROskiPulseView />
          </div>
        </div>
      </Pane>
    </div>
  )
}
