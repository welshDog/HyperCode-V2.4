'use client'

import React from 'react'
import { useSensory } from './SensoryProvider'
import { OPTIONS, PRESETS, presetOf, type PresetName, type SettingKey } from '@/lib/sensory/settings'

// Literal labels first; the explanation sits underneath, never instead.
const PRESET_INFO: Record<PresetName, { label: string; help: string }> = {
  calm: { label: 'Calm', help: 'No motion, roomy spacing, progress hidden, one thing at a time.' },
  focus: { label: 'Focus', help: 'Very little motion, quiet progress, everything available.' },
  energise: { label: 'Energise', help: 'Full motion and progress visuals.' },
}

const GROUPS: { key: SettingKey; title: string; help: string; labels: Record<string, string> }[] = [
  { key: 'motion', title: 'Motion', help: 'Animations, glows and transitions.', labels: { off: 'Off', reduced: 'Reduced', full: 'Full' } },
  { key: 'density', title: 'Spacing', help: 'How much room panels have.', labels: { roomy: 'Roomy', normal: 'Normal', compact: 'Compact' } },
  { key: 'contrast', title: 'Contrast', help: 'Text and borders against the background.', labels: { normal: 'Normal', high: 'High' } },
  { key: 'font', title: 'Reading font', help: 'The typeface used across the app.', labels: { inter: 'Standard', dyslexia: 'Dyslexia-friendly' } },
  { key: 'progress', title: 'Progress and rewards', help: 'XP bars and wallet. Progress still counts while hidden.', labels: { hidden: 'Hidden', quiet: 'Quiet', full: 'Full' } },
  { key: 'layout', title: 'Layout', help: 'Calm puts the summary first and tucks extra tools away.', labels: { calm: 'Calm', full: 'Full' } },
]

export function SensorySettingsPanel(): React.JSX.Element {
  const { settings, update, applyPreset } = useSensory()
  const current = presetOf(settings)

  return (
    <div className="pane sensory-settings">
      <div className="pane-header">
        <span className="pane-title">Sensory settings</span>
      </div>
      <div className="pane-body">
        <p style={{ marginBottom: 12 }}>Changes apply straight away and are saved on this device.</p>

        <div role="group" aria-label="Presets" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
          {(Object.keys(PRESETS) as PresetName[]).map((name) => (
            <button
              key={name}
              type="button"
              className={`btn${current === name ? ' active' : ''}`}
              aria-pressed={current === name}
              onClick={() => applyPreset(name)}
              title={PRESET_INFO[name].help}
            >
              {PRESET_INFO[name].label}
            </button>
          ))}
        </div>
        <p data-testid="preset-help" style={{ marginBottom: 16, color: 'var(--text-secondary)' }}>
          {current === 'custom' ? 'Custom: you changed something from a preset.' : PRESET_INFO[current].help}
        </p>

        {GROUPS.map((g) => (
          <fieldset key={g.key} style={{ border: 'none', marginBottom: 14 }}>
            <legend style={{ fontWeight: 600 }}>{g.title}</legend>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 6 }}>{g.help}</p>
            <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
              {OPTIONS[g.key].map((value) => (
                <label key={value} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <input
                    type="radio"
                    name={g.key}
                    value={value}
                    checked={settings[g.key] === value}
                    onChange={() => update({ [g.key]: value } as Partial<typeof settings>)}
                  />
                  {g.labels[value]}
                </label>
              ))}
            </div>
          </fieldset>
        ))}
      </div>
    </div>
  )
}
