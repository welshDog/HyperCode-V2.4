'use client';

import React, { useState, useRef, useId } from 'react';
import {
  chunkBrainDump,
  MicroTask,
  EFFORT_LABELS,
  CATEGORY_EMOJI,
  type ChunkResult,
} from '../lib/brainDump';

export default function BrainDumpChunker() {
  const [raw, setRaw] = useState('');
  const [result, setResult] = useState<ChunkResult | null>(null);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const announcerRef = useRef<HTMLDivElement>(null);
  const inputId = useId();
  const labelId = useId();

  function handleChunk() {
    const res = chunkBrainDump(raw);
    setResult(res);
    setDismissed(new Set());
    // Announce result count to screen readers
    if (announcerRef.current) {
      announcerRef.current.textContent = '';
      setTimeout(() => {
        if (announcerRef.current) {
          announcerRef.current.textContent =
            res.tasks.length === 0
              ? 'No tasks found. Try adding more detail to your brain dump.'
              : `${res.tasks.length} task${res.tasks.length > 1 ? 's' : ''} found.${
                  res.overloadWarning ? ' Warning: high cognitive load detected.' : ''
                }${res.suggestedFocus ? ` Suggested start: ${res.suggestedFocus.text}` : ''}`;
        }
      }, 50);
    }
  }

  function dismissTask(id: string) {
    setDismissed((prev) => new Set([...prev, id]));
  }

  const visibleTasks = result?.tasks.filter((t) => !dismissed.has(t.id)) ?? [];

  return (
    <section
      aria-labelledby={labelId}
      className="hc-card brain-dump-chunker"
      style={{
        background: 'var(--hc-color-surface)',
        border: '1px solid var(--hc-color-border)',
        borderRadius: '12px',
        padding: '1.25rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
      }}
    >
      {/* Screen reader live region */}
      <div
        ref={announcerRef}
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      />

      <h2
        id={labelId}
        style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--hc-color-text)' }}
      >
        🧠 Brain Dump
      </h2>

      <label
        htmlFor={inputId}
        style={{ fontSize: '0.8rem', color: 'var(--hc-color-text-muted)' }}
      >
        Dump everything on your mind — tasks, worries, ideas. One line, bullet points, or total
        chaos. We’ll sort it.
      </label>

      <textarea
        id={inputId}
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        rows={5}
        placeholder={`fix auth bug, email client about invoice, research aria patterns, refactor the chunker URGENT, blocked on design review...`}
        aria-describedby={`${inputId}-hint`}
        style={{
          width: '100%',
          resize: 'vertical',
          background: 'var(--hc-color-bg)',
          color: 'var(--hc-color-text)',
          border: '1px solid var(--hc-color-border)',
          borderRadius: '8px',
          padding: '0.6rem',
          fontSize: '0.9rem',
          fontFamily: 'inherit',
          boxSizing: 'border-box',
        }}
      />
      <span id={`${inputId}-hint`} className="sr-only">
        Enter your brain dump text. Separate tasks with commas, new lines, or just write freely.
      </span>

      <button
        onClick={handleChunk}
        disabled={!raw.trim()}
        style={{
          alignSelf: 'flex-start',
          background: raw.trim() ? 'var(--hc-color-accent)' : 'var(--hc-color-border)',
          color: raw.trim() ? '#fff' : 'var(--hc-color-text-muted)',
          border: 'none',
          borderRadius: '8px',
          padding: '0.5rem 1.25rem',
          fontWeight: 700,
          cursor: raw.trim() ? 'pointer' : 'not-allowed',
          fontSize: '0.9rem',
          transition: 'background 0.2s',
        }}
        aria-label="Chunk my brain dump into tasks"
      >
        ⚡ Chunk It
      </button>

      {/* Results */}
      {result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {/* Overload warning */}
          {result.overloadWarning && (
            <div
              role="alert"
              style={{
                background: 'var(--hc-color-error-bg, #fff3cd)',
                color: 'var(--hc-color-error, #856404)',
                borderRadius: '8px',
                padding: '0.5rem 0.75rem',
                fontSize: '0.85rem',
                fontWeight: 600,
              }}
            >
              ⚠️ {result.tasks.length} tasks detected — high cognitive load risk. Consider tackling
              the suggested task first, then come back.
            </div>
          )}

          {/* Suggested focus */}
          {result.suggestedFocus && !dismissed.has(result.suggestedFocus.id) && (
            <div
              style={{
                background: 'var(--hc-color-accent-soft, #e8f4ff)',
                border: '1px solid var(--hc-color-accent)',
                borderRadius: '8px',
                padding: '0.5rem 0.75rem',
                fontSize: '0.85rem',
              }}
            >
              <span style={{ fontWeight: 700 }}>🎯 Start here:</span>{' '}
              {CATEGORY_EMOJI[result.suggestedFocus.category]} {result.suggestedFocus.text}{' '}
              <span style={{ color: 'var(--hc-color-text-muted)' }}>
                ({EFFORT_LABELS[result.suggestedFocus.effort]})
              </span>
            </div>
          )}

          {/* Task list */}
          {visibleTasks.length > 0 ? (
            <ul
              aria-label={`${visibleTasks.length} chunked task${visibleTasks.length > 1 ? 's' : ''}`}
              style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.4rem' }}
            >
              {visibleTasks.map((task) => (
                <TaskChip key={task.id} task={task} onDismiss={dismissTask} />
              ))}
            </ul>
          ) : (
            result.tasks.length > 0 && (
              <p style={{ color: 'var(--hc-color-text-muted)', fontSize: '0.85rem', margin: 0 }}>
                All tasks dismissed. Nice work! 🔥
              </p>
            )
          )}

          {result.tasks.length === 0 && (
            <p style={{ color: 'var(--hc-color-text-muted)', fontSize: '0.85rem', margin: 0 }}>
              No tasks found. Try adding more detail!
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function TaskChip({
  task,
  onDismiss,
}: {
  task: MicroTask;
  onDismiss: (id: string) => void;
}) {
  return (
    <li
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        background: 'var(--hc-color-bg)',
        border: '1px solid var(--hc-color-border)',
        borderRadius: '8px',
        padding: '0.4rem 0.6rem',
        fontSize: '0.85rem',
      }}
    >
      <span aria-hidden="true">{CATEGORY_EMOJI[task.category]}</span>
      <span style={{ flex: 1, color: 'var(--hc-color-text)' }}>
        {task.urgent && (
          <span
            aria-label="urgent"
            style={{ color: 'var(--hc-color-error, #dc3545)', fontWeight: 700, marginRight: '0.25rem' }}
          >
            !
          </span>
        )}
        {task.text}
      </span>
      <span
        style={{
          fontSize: '0.75rem',
          color: 'var(--hc-color-text-muted)',
          whiteSpace: 'nowrap',
        }}
        aria-label={`Effort: ${EFFORT_LABELS[task.effort]}`}
      >
        {EFFORT_LABELS[task.effort]}
      </span>
      <button
        onClick={() => onDismiss(task.id)}
        aria-label={`Dismiss task: ${task.text}`}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--hc-color-text-muted)',
          fontSize: '1rem',
          padding: '0 0.2rem',
          lineHeight: 1,
        }}
      >
        ✕
      </button>
    </li>
  );
}
