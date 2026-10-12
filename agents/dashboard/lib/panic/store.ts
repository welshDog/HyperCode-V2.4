// Panic: pause everything the operator is running, with one click and no confirmation.
// External store (useSyncExternalStore). It only ever claims "Saved" when core says it saved.

export interface HeldRun {
  taskId: string
  pausedAt?: string | null
  card?: { tldr?: string[]; next_action?: string } | null
}

export type PanicPhase = 'idle' | 'working' | 'error'

export interface PanicState {
  phase: PanicPhase
  held: HeldRun[]
  message: string | null
  loaded: boolean
}

const INITIAL: PanicState = { phase: 'idle', held: [], message: null, loaded: false }
let state: PanicState = INITIAL
const listeners = new Set<() => void>()

export const getSnapshot = (): PanicState => state
export const getServerSnapshot = (): PanicState => INITIAL

function set(next: Partial<PanicState>): void {
  state = { ...state, ...next }
  listeners.forEach((l) => l())
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function resetPanicStore(): void {
  state = INITIAL
  listeners.clear()
}

const asHeld = (v: unknown): HeldRun[] =>
  Array.isArray(v)
    ? v.filter((x): x is HeldRun => !!x && typeof x === 'object' && typeof (x as HeldRun).taskId === 'string')
    : []

async function call(path: string, method: 'GET' | 'POST'): Promise<Record<string, unknown> | null> {
  try {
    const res = await fetch(path, { method, cache: 'no-store' })
    if (!res.ok) return null
    return (await res.json()) as Record<string, unknown>
  } catch {
    return null
  }
}

/** What is currently held (survives a refresh or a restart). Quiet: a failure just means "unknown". */
export async function loadHeld(): Promise<void> {
  const body = await call('/api/crew/panic', 'GET')
  set(body ? { held: asHeld(body.paused), loaded: true } : { loaded: true })
}

export async function panic(): Promise<void> {
  set({ phase: 'working' })
  const body = await call('/api/crew/panic', 'POST')
  if (!body || body.saved !== true) {
    // Never say "Saved" unless core confirmed it.
    set({ phase: 'error', message: "Couldn't reach the crew, so nothing was changed. Try again." })
    return
  }
  const fresh = asHeld(body.paused)
  const keep = state.held.filter((h) => !fresh.some((f) => f.taskId === h.taskId))
  const note = body.ledger === false ? ' (The audit note could not be written.)' : ''
  set({
    phase: 'idle',
    held: [...fresh, ...keep],
    message: `${typeof body.message === 'string' ? body.message : 'Saved.'}${note}`,
  })
  void loadHeld()
}

export async function resume(): Promise<void> {
  set({ phase: 'working' })
  const body = await call('/api/crew/panic/resume', 'POST')
  if (!body) {
    set({ phase: 'error', message: "Couldn't resume. Nothing was changed. Try again." })
    return
  }
  set({ phase: 'idle', held: [], message: 'Resumed. The crew carries on from where it stopped.' })
  void loadHeld()
}

export function dismissMessage(): void {
  set({ message: null })
}
