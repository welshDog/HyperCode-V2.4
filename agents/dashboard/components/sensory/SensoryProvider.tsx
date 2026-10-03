'use client'

import React, { createContext, useContext, useMemo, useSyncExternalStore } from 'react'
import { PRESETS, applyNdMode, ndModeOf, type NdMode, type PresetName, type SensorySettings } from '@/lib/sensory/settings'
import { getServerSnapshot, getSnapshot, setSettings, subscribe, toggleCalmMode, updateSettings } from '@/lib/sensory/store'

interface SensoryContextValue {
  settings: SensorySettings
  update: (patch: Partial<SensorySettings>) => void
  applyPreset: (name: PresetName) => void
  toggleCalmMode: () => void
  ndMode: NdMode
  setNdMode: (mode: string) => void
}

const SensoryContext = createContext<SensoryContextValue | null>(null)

const applyPreset = (name: PresetName): void => setSettings({ ...PRESETS[name] })
const setNdMode = (mode: string): void => setSettings(applyNdMode(getSnapshot(), mode))

export function SensoryProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  // Server and first client render use the default (Calm); the pre-paint boot script has already put
  // the saved attributes on <html>, and the store then serves the saved settings.
  const settings = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
  const value = useMemo<SensoryContextValue>(
    () => ({ settings, update: updateSettings, applyPreset, toggleCalmMode, ndMode: ndModeOf(settings), setNdMode }),
    [settings],
  )
  return <SensoryContext.Provider value={value}>{children}</SensoryContext.Provider>
}

export function useSensory(): SensoryContextValue {
  const ctx = useContext(SensoryContext)
  if (!ctx) throw new Error('useSensory must be used inside <SensoryProvider>')
  return ctx
}
