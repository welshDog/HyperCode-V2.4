// Morning Card: one fetch on load, a manual refresh, no polling. A failure is said plainly, never hidden.
import type { CalmCardData } from '@/lib/agui/types'

export type Light = 'green' | 'amber' | 'red'
export interface MorningState {
  phase: 'idle' | 'loading' | 'ready' | 'error'
  card: CalmCardData | null
  light: Light | null
}

const INITIAL: MorningState = { phase: 'idle', card: null, light: null }
let state: MorningState = INITIAL
const listeners = new Set<() => void>()

export const getSnapshot = (): MorningState => state
export const getServerSnapshot = (): MorningState => INITIAL

function set(next: Partial<MorningState>): void {
  state = { ...state, ...next }
  listeners.forEach((l) => l())
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function resetMorningStore(): void {
  state = INITIAL
  listeners.clear()
}

const isLight = (v: unknown): v is Light => v === 'green' || v === 'amber' || v === 'red'

function isCard(v: unknown): v is CalmCardData {
  if (!v || typeof v !== 'object') return false
  const c = v as Partial<CalmCardData>
  return typeof c.status === 'string' && Array.isArray(c.tldr) && c.tldr.every((t) => typeof t === 'string')
    && typeof c.next_action === 'string' && Array.isArray(c.details) && typeof c.plain_text === 'string'
}

export async function loadMorning(): Promise<void> {
  set({ phase: 'loading' })
  try {
    const res = await fetch('/api/crew/morning', { cache: 'no-store' })
    const body: unknown = res.ok ? await res.json() : null
    const b = body && typeof body === 'object' ? (body as Record<string, unknown>) : null
    if (b && isCard(b.calmCard)) {
      set({ phase: 'ready', card: b.calmCard, light: isLight(b.light) ? b.light : null })
      return
    }
  } catch {
    // fall through to the honest error state
  }
  set({ phase: 'error' })
}
