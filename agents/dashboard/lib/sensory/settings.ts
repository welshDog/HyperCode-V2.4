// Sensory Settings — one model for everything that changes how heavy the UI feels.
// Pure and SSR-safe; the React provider, the CSS (app/sensory.css) and the pre-paint boot script
// all derive from this file, so they cannot drift apart (see __tests__/sensory.test.ts).
//
// Only settings that actually DO something today are modelled. Notification batching, sound and
// playful labels are deliberately absent until they are wired — a control that does nothing is a lie.

export const STORAGE_KEY = 'hc-sensory-settings'
export const BEFORE_CALM_KEY = 'hc-sensory-before-calm'

export const OPTIONS = {
  motion: ['off', 'reduced', 'full'],
  density: ['roomy', 'normal', 'compact'],
  contrast: ['normal', 'high'],
  font: ['inter', 'dyslexia'],
  progress: ['hidden', 'quiet', 'full'],
  layout: ['calm', 'full'],
} as const

export type SettingKey = keyof typeof OPTIONS
export type SensorySettings = { [K in SettingKey]: (typeof OPTIONS)[K][number] }
export type PresetName = 'calm' | 'focus' | 'energise'

export const PRESETS: Record<PresetName, SensorySettings> = {
  calm: { motion: 'off', density: 'roomy', contrast: 'normal', font: 'inter', progress: 'hidden', layout: 'calm' },
  focus: { motion: 'reduced', density: 'normal', contrast: 'normal', font: 'inter', progress: 'quiet', layout: 'full' },
  energise: { motion: 'full', density: 'normal', contrast: 'normal', font: 'inter', progress: 'full', layout: 'full' },
}

// Calm is the default for new people (spec decision D10, recommended: yes).
export const DEFAULT_SETTINGS: SensorySettings = PRESETS.calm

export const SETTING_KEYS = Object.keys(OPTIONS) as SettingKey[]

/** Anything → a valid settings object. Bad or missing fields fall back to the default, per field. */
export function sanitize(raw: unknown): SensorySettings {
  const src = raw && typeof raw === 'object' ? (raw as Record<string, unknown>) : {}
  const out: Record<string, string> = {}
  for (const key of SETTING_KEYS) {
    const allowed = OPTIONS[key] as readonly string[]
    const value = src[key]
    out[key] = typeof value === 'string' && allowed.includes(value) ? value : DEFAULT_SETTINGS[key]
  }
  return out as unknown as SensorySettings
}

export function presetOf(settings: SensorySettings): PresetName | 'custom' {
  for (const name of Object.keys(PRESETS) as PresetName[]) {
    if (SETTING_KEYS.every((k) => PRESETS[name][k] === settings[k])) return name
  }
  return 'custom'
}

/** The data-* attributes set on <html>. CSS keys off these. */
export function toAttributes(settings: SensorySettings): Record<string, string> {
  const attrs: Record<string, string> = { 'data-sensory': presetOf(settings) }
  for (const key of SETTING_KEYS) attrs[`data-${key}`] = settings[key]
  return attrs
}

export function applyToElement(el: Pick<HTMLElement, 'setAttribute'>, settings: SensorySettings): void {
  for (const [name, value] of Object.entries(toAttributes(settings))) el.setAttribute(name, value)
}

// ── storage (never throws: private windows, blocked storage and corrupt JSON all fall back) ──
type StorageLike = Pick<Storage, 'getItem' | 'setItem'>

function safeStorage(): StorageLike | null {
  try {
    return typeof window !== 'undefined' ? window.localStorage : null
  } catch {
    return null
  }
}

function read(key: string, storage: StorageLike | null): unknown {
  try {
    const text = storage?.getItem(key)
    return text ? JSON.parse(text) : null
  } catch {
    return null
  }
}

export function loadSettings(storage: StorageLike | null = safeStorage()): SensorySettings {
  return sanitize(read(STORAGE_KEY, storage))
}

export function saveSettings(settings: SensorySettings, storage: StorageLike | null = safeStorage()): void {
  try {
    storage?.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch {
    // storage unavailable: the settings still apply for this session
  }
}

export function loadBeforeCalm(storage: StorageLike | null = safeStorage()): SensorySettings | null {
  const raw = read(BEFORE_CALM_KEY, storage)
  return raw ? sanitize(raw) : null
}

export function saveBeforeCalm(settings: SensorySettings | null, storage: StorageLike | null = safeStorage()): void {
  try {
    if (settings) storage?.setItem(BEFORE_CALM_KEY, JSON.stringify(settings))
  } catch {
    // ignore
  }
}

// ── Calm Mode: one switch ──
export const isCalm = (s: SensorySettings): boolean => s.layout === 'calm'

/** Turning Calm on remembers what you had; turning it off puts it back (Focus if nothing was saved). */
export function toggleCalm(
  current: SensorySettings,
  before: SensorySettings | null,
): { next: SensorySettings; before: SensorySettings | null } {
  if (isCalm(current)) {
    const restore = before && !isCalm(before) ? before : PRESETS.focus
    return { next: restore, before: null }
  }
  return { next: PRESETS.calm, before: current }
}

// ── legacy "ND mode" (the old header toggle) kept consistent with the new settings ──
export type NdMode = 'default' | 'dyslexia' | 'high-contrast' | 'focus'

export function ndModeOf(s: SensorySettings): NdMode {
  if (s.font === 'dyslexia') return 'dyslexia'
  if (s.contrast === 'high') return 'high-contrast'
  if (presetOf(s) === 'focus') return 'focus'
  return 'default'
}

export function applyNdMode(s: SensorySettings, mode: string): SensorySettings {
  switch (mode) {
    case 'dyslexia':
      return { ...s, font: 'dyslexia' }
    case 'high-contrast':
      return { ...s, contrast: 'high' }
    case 'focus':
      return { ...PRESETS.focus }
    default:
      return { ...s, font: 'inter', contrast: 'normal' }
  }
}

/**
 * Inline script for <head>: applies saved settings BEFORE first paint so there is no flash.
 * Built from OPTIONS/DEFAULT_SETTINGS, so it validates exactly like sanitize().
 */
export function bootScript(): string {
  const options = JSON.stringify(OPTIONS)
  const defaults = JSON.stringify(DEFAULT_SETTINGS)
  const presets = JSON.stringify(PRESETS)
  return `(function(){try{var O=${options},D=${defaults},P=${presets},s={};try{s=JSON.parse(localStorage.getItem(${JSON.stringify(
    STORAGE_KEY,
  )})||'{}')||{}}catch(e){}var r=document.documentElement,m={};for(var k in O){var v=s&&s[k];m[k]=O[k].indexOf(v)>-1?v:D[k];r.setAttribute('data-'+k,m[k])}var n='custom';for(var p in P){var ok=true;for(var k2 in O){if(P[p][k2]!==m[k2]){ok=false;break}}if(ok){n=p;break}}r.setAttribute('data-sensory',n)}catch(e){}})();`
}
