/**
 * View Registry — Plugin system for dashboard panes
 * Add new views here without touching HyperShellLayout
 */
import type { ComponentType } from 'react'

export interface ViewManifest {
  id:          string
  title:       string
  description: string
  component:   ComponentType
  gridArea?:   string
  minWidth?:   number
  minHeight?:  number
}

const registry = new Map<string, ViewManifest>()

export function registerView(manifest: ViewManifest): void {
  if (registry.has(manifest.id)) {
    console.warn(`[ViewRegistry] Overwriting view: ${manifest.id}`)
  }
  registry.set(manifest.id, manifest)
}

export function getView(id: string): ViewManifest | undefined {
  return registry.get(id)
}

export function listViews(): ViewManifest[] {
  return Array.from(registry.values())
}
