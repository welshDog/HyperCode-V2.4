// A tiny external store for Sensory Settings, shaped for React's useSyncExternalStore.
// Server snapshot = the default (Calm); the client snapshot is read from localStorage once and
// then cached (the snapshot must be referentially stable between changes).

import {
  DEFAULT_SETTINGS, STORAGE_KEY, applyToElement, loadBeforeCalm, loadSettings, sanitize, saveBeforeCalm,
  saveSettings, toggleCalm, type SensorySettings,
} from './settings'

let cache: SensorySettings | null = null
const listeners = new Set<() => void>()

export function getSnapshot(): SensorySettings {
  if (cache === null) cache = loadSettings()
  return cache
}

export function getServerSnapshot(): SensorySettings {
  return DEFAULT_SETTINGS
}

function emit(): void {
  listeners.forEach((l) => l())
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  // Make sure <html> matches what we are about to render (the boot script normally did this already).
  if (typeof document !== 'undefined') applyToElement(document.documentElement, getSnapshot())
  const onStorage = (e: StorageEvent): void => {
    if (e.key !== null && e.key !== STORAGE_KEY) return
    cache = loadSettings()
    if (typeof document !== 'undefined') applyToElement(document.documentElement, cache)
    emit() // another tab changed it
  }
  if (typeof window !== 'undefined') window.addEventListener('storage', onStorage)
  return () => {
    listeners.delete(listener)
    if (typeof window !== 'undefined') window.removeEventListener('storage', onStorage)
  }
}

export function setSettings(next: SensorySettings): void {
  cache = sanitize(next)
  saveSettings(cache)
  if (typeof document !== 'undefined') applyToElement(document.documentElement, cache)
  emit()
}

export function updateSettings(patch: Partial<SensorySettings>): void {
  setSettings({ ...getSnapshot(), ...patch })
}

export function toggleCalmMode(): void {
  const { next, before } = toggleCalm(getSnapshot(), loadBeforeCalm())
  saveBeforeCalm(before)
  setSettings(next)
}

/** For tests: forget the cache so the next read hits storage again. */
export function resetStore(): void {
  cache = null
  listeners.clear()
}
