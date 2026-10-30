// Allow-list for the browser -> core proxy (app/api/core/[...path]).
// Only paths the UI actually calls are forwarded. The service JWT is injected
// for reads only: writes must carry the caller's own Authorization header.

type Rule = { method: string; pattern: RegExp; open?: boolean }

const ID = '[A-Za-z0-9_-]{1,64}'

const RULES: Rule[] = [
  { method: 'GET', pattern: /^agents\/status$/ },
  { method: 'GET', pattern: /^projects$/ },
  { method: 'GET', pattern: /^tasks$/ },
  { method: 'GET', pattern: new RegExp(`^tasks/${ID}$`) },
  { method: 'GET', pattern: /^broski\/wallet$/ },
  { method: 'GET', pattern: /^logs$/ },
  { method: 'GET', pattern: /^orchestrator\/system\/health$/ },
  { method: 'GET', pattern: /^orchestrator\/agents$/ },
  { method: 'GET', pattern: /^flows\/active$/ },
  { method: 'GET', pattern: new RegExp(`^flows/runs/${ID}$`) },
  { method: 'GET', pattern: new RegExp(`^flows/runs/${ID}/events$`) },
  // Login carries its own credentials, so it needs no token to be sent.
  { method: 'POST', pattern: /^auth\/login\/access-token$/, open: true },
  { method: 'POST', pattern: /^tasks$/ },
  { method: 'POST', pattern: /^execute$/ },
  { method: 'POST', pattern: /^hypersync\/handoff$/ },
  { method: 'POST', pattern: /^hypersync\/redeem$/ },
  { method: 'POST', pattern: /^orchestrator\/approvals\/respond$/ },
]

export type CoreDecision =
  | { allowed: true; upstreamPath: string; useServiceAuth: boolean; requireCallerAuth: boolean }
  | { allowed: false; reason: 'path' | 'method' }

/** Drops a leading `api/v1` and any trailing slash; null if a segment is unsafe. */
function normalise(segments: string[]): string[] | null {
  const parts = segments[0] === 'api' && segments[1] === 'v1' ? segments.slice(2) : [...segments]
  while (parts.length && parts[parts.length - 1] === '') parts.pop()
  if (parts.length === 0) return null
  for (const p of parts) {
    if (p === '' || p === '.' || p === '..' || /[\/%\0]/.test(p)) return null
  }
  return parts
}

export function evaluateCoreRequest(method: string, segments: string[]): CoreDecision {
  const parts = normalise(segments)
  if (!parts) return { allowed: false, reason: 'path' }
  const path = parts.join('/')
  const matches = RULES.filter((r) => r.pattern.test(path))
  if (matches.length === 0) return { allowed: false, reason: 'path' }
  const m = method.toUpperCase()
  const rule = matches.find((r) => r.method === m || (m === 'HEAD' && r.method === 'GET'))
  if (!rule) return { allowed: false, reason: 'method' }
  const read = rule.method === 'GET'
  return {
    allowed: true,
    upstreamPath: `/api/v1/${parts.map(encodeURIComponent).join('/')}`,
    useServiceAuth: read,
    requireCallerAuth: !read && !rule.open,
  }
}
