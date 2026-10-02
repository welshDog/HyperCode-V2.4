// Focus session: one chunk of work with the app held quiet. A suggestion, never a forced timer —
// when the time is up it says so once and stays out of the way until you end it.

export const STORAGE_KEY = 'hc-focus-session'
export const CHUNK_OPTIONS = [10, 25, 45] as const
export type ChunkMinutes = (typeof CHUNK_OPTIONS)[number]

export interface FocusState {
  active: boolean
  startedAt: number | null // epoch ms
  minutes: ChunkMinutes
}

const DEFAULT: FocusState = { active: false, startedAt: null, minutes: 25 }
let state: FocusState | null = null
const listeners = new Set<() => void>()

export function sanitize(raw: unknown): FocusState {
  const r = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const minutes = (CHUNK_OPTIONS as readonly number[]).includes(r.minutes as number) ? (r.minutes as ChunkMinutes) : DEFAULT.minutes
  const startedAt = typeof r.startedAt === 'number' && Number.isFinite(r.startedAt) && r.startedAt > 0 ? r.startedAt : null
  return r.active === true && startedAt !== null ? { active: true, startedAt, minutes } : { ...DEFAULT, minutes }
}

function load(): FocusState {
  try {
    const text = typeof window !== 'undefined' ? window.localStorage.getItem(STORAGE_KEY) : null
    return sanitize(text ? JSON.parse(text) : null)
  } catch {
    return DEFAULT
  }
}

function apply(next: FocusState): void {
  if (typeof document === 'undefined') return
  if (next.active) document.documentElement.setAttribute('data-focus', 'on')
  else document.documentElement.removeAttribute('data-focus')
}

function commit(next: FocusState): void {
  state = next
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // storage blocked: the session still works until the tab closes
  }
  apply(next)
  listeners.forEach((l) => l())
}

export const getSnapshot = (): FocusState => (state ??= load())
export const getServerSnapshot = (): FocusState => DEFAULT
/** For code that must not subscribe (e.g. the toast layer). */
export const isFocusActive = (): boolean => getSnapshot().active

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  apply(getSnapshot())
  return () => listeners.delete(listener)
}

export function startFocus(minutes: ChunkMinutes = getSnapshot().minutes, now: number = Date.now()): void {
  commit({ active: true, startedAt: now, minutes })
}

export function endFocus(): void {
  commit({ active: false, startedAt: null, minutes: getSnapshot().minutes })
}

export function setMinutes(minutes: ChunkMinutes): void {
  commit({ ...getSnapshot(), minutes })
}

export function remainingSeconds(s: FocusState, now: number = Date.now()): number {
  if (!s.active || s.startedAt === null) return s.minutes * 60
  return Math.max(0, Math.ceil((s.startedAt + s.minutes * 60_000 - now) / 1000))
}

export function resetFocusStore(): void {
  state = null
  listeners.clear()
}
