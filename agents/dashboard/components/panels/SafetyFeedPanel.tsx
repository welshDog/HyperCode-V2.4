// Mission Control — Safety Shepherd verdict feed.
// Terminal-style live stream of ALLOW / BLOCK / ESCALATE decisions. Pending
// escalations surface in the dashboard's ApprovalModal for approve/deny.

'use client'

import { useSafetyFeed, type SafetyEvent } from '../../hooks/useSafetyFeed'

const DECISION_CONFIG: Record<string, { badge: string; row: string }> = {
  ALLOW:    { badge: 'bg-emerald-950/70 text-emerald-400', row: 'border-l-emerald-500/30' },
  BLOCK:    { badge: 'bg-red-950/70 text-red-400',         row: 'border-l-red-500/60' },
  ESCALATE: { badge: 'bg-amber-950/70 text-amber-400',     row: 'border-l-amber-500/60' },
}

function eventTime(ts: string): string {
  const d = new Date(ts)
  return isNaN(d.getTime()) ? '—' : d.toLocaleTimeString([], { hour12: false })
}

function FeedRow({ event }: { event: SafetyEvent }): React.JSX.Element {
  const cfg = DECISION_CONFIG[event.decision] ?? DECISION_CONFIG.ALLOW
  const detail = [event.category, event.tool, event.target ?? event.domain]
    .filter(Boolean)
    .join(' · ')
  return (
    <li
      className={`border-l-2 pl-2 py-1.5 ${cfg.row}`}
      aria-label={`${event.decision} — ${event.agent}`}
    >
      <div className="flex items-center gap-2 text-[11px]">
        <span className="text-gray-600 tabular-nums shrink-0">{eventTime(event.ts)}</span>
        <span className={`rounded px-1.5 py-px font-semibold ${cfg.badge}`}>{event.decision}</span>
        <span className="text-gray-300 truncate">{event.agent}</span>
        {event.decision === 'ESCALATE' && event.approval_id && (
          <span className="ml-auto shrink-0 text-amber-400/70">awaiting human</span>
        )}
      </div>
      {detail && <p className="mt-0.5 text-[10px] text-gray-600 truncate">{detail}</p>}
      {event.reason && <p className="mt-0.5 text-[10px] text-gray-500 truncate">{event.reason}</p>}
    </li>
  )
}

export default function SafetyFeedPanel(): React.JSX.Element {
  const { events, error, loading } = useSafetyFeed()

  return (
    <section
      aria-label="Safety Shepherd feed"
      className="flex flex-col gap-3 rounded-lg border border-gray-800 bg-[#050505] p-3 font-mono"
    >
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400">Safety Feed</h2>
        <span
          className={`ml-auto h-2 w-2 rounded-full ${
            error ? 'bg-red-500' : 'bg-cyan-400 animate-pulse'
          }`}
          aria-hidden
        />
      </div>

      {error && (
        <p role="alert" className="text-xs text-red-400">
          Shepherd unreachable: {error}
        </p>
      )}

      {loading && !error && (
        <p className="text-xs text-gray-500 animate-pulse">Listening for verdicts…</p>
      )}

      {!loading && !error && events.length === 0 && (
        <p className="text-xs text-gray-500">No verdicts yet — the Shepherd is watching.</p>
      )}

      <ul className="flex flex-col gap-0.5 overflow-y-auto max-h-[70vh]">
        {events.map((event) => (
          <FeedRow key={event.id} event={event} />
        ))}
      </ul>
    </section>
  )
}
