import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import {
  BEFORE_CALM_KEY, DEFAULT_SETTINGS, OPTIONS, PRESETS, SETTING_KEYS, STORAGE_KEY, applyNdMode, bootScript,
  isCalm, loadBeforeCalm, loadSettings, ndModeOf, presetOf, sanitize, saveBeforeCalm, saveSettings, toAttributes,
  toggleCalm, type PresetName, type SensorySettings,
} from '@/lib/sensory/settings'

const root = join(__dirname, '..')
const read = (p: string) => readFileSync(join(root, p), 'utf-8')

function fakeStorage(initial: Record<string, string> = {}) {
  const data = { ...initial }
  return { data, getItem: (k: string) => data[k] ?? null, setItem: (k: string, v: string) => { data[k] = v } }
}

describe('presets and defaults', () => {
  it('every preset uses only allowed values', () => {
    for (const preset of Object.values(PRESETS)) {
      for (const key of SETTING_KEYS) expect((OPTIONS[key] as readonly string[]).includes(preset[key])).toBe(true)
    }
  })

  it('new people start in Calm', () => {
    expect(DEFAULT_SETTINGS).toEqual(PRESETS.calm)
    expect(isCalm(DEFAULT_SETTINGS)).toBe(true)
  })

  it('calm means no motion, hidden progress and the calm layout; energise is the opposite', () => {
    expect(PRESETS.calm).toMatchObject({ motion: 'off', progress: 'hidden', layout: 'calm', density: 'roomy' })
    expect(PRESETS.energise).toMatchObject({ motion: 'full', progress: 'full', layout: 'full' })
  })

  it('presets are all different from each other', () => {
    const names = Object.keys(PRESETS) as PresetName[]
    for (const a of names) for (const b of names) if (a !== b) expect(presetOf(PRESETS[a])).not.toBe(b)
  })
})

describe('sanitize', () => {
  it.each([null, undefined, 5, 'x', [], true])('turns %s into the defaults', (raw) => {
    expect(sanitize(raw)).toEqual(DEFAULT_SETTINGS)
  })

  it('keeps valid fields and replaces only the bad ones', () => {
    expect(sanitize({ motion: 'full', density: 'huge', contrast: 3, font: 'dyslexia', extra: 'x' })).toEqual({
      ...DEFAULT_SETTINGS, motion: 'full', font: 'dyslexia',
    })
  })

  it('never returns unknown keys', () => {
    expect(Object.keys(sanitize({ evil: 1, motion: 'off' })).sort()).toEqual([...SETTING_KEYS].sort())
  })
})

describe('presetOf and attributes', () => {
  it('recognises each preset and calls anything else custom', () => {
    for (const name of Object.keys(PRESETS) as PresetName[]) expect(presetOf(PRESETS[name])).toBe(name)
    expect(presetOf({ ...PRESETS.calm, motion: 'full' })).toBe('custom')
  })

  it('maps every setting to a data attribute plus the preset name', () => {
    const attrs = toAttributes(PRESETS.focus)
    expect(attrs['data-sensory']).toBe('focus')
    for (const key of SETTING_KEYS) expect(attrs[`data-${key}`]).toBe(PRESETS.focus[key])
    expect(Object.keys(attrs)).toHaveLength(SETTING_KEYS.length + 1)
  })
})

describe('storage', () => {
  it('round-trips', () => {
    const s = fakeStorage()
    saveSettings(PRESETS.energise, s)
    expect(loadSettings(s)).toEqual(PRESETS.energise)
  })

  it('falls back to the default for missing, corrupt or hostile storage', () => {
    expect(loadSettings(fakeStorage())).toEqual(DEFAULT_SETTINGS)
    expect(loadSettings(fakeStorage({ [STORAGE_KEY]: '{not json' }))).toEqual(DEFAULT_SETTINGS)
    expect(loadSettings(fakeStorage({ [STORAGE_KEY]: '{"motion":"<script>"}' }))).toEqual(DEFAULT_SETTINGS)
    expect(loadSettings(null)).toEqual(DEFAULT_SETTINGS)
  })

  it('never throws when storage itself throws', () => {
    const broken = { getItem: () => { throw new Error('blocked') }, setItem: () => { throw new Error('blocked') } }
    expect(loadSettings(broken)).toEqual(DEFAULT_SETTINGS)
    expect(() => saveSettings(PRESETS.focus, broken)).not.toThrow()
    expect(loadBeforeCalm(broken)).toBeNull()
    expect(() => saveBeforeCalm(PRESETS.focus, broken)).not.toThrow()
  })

  it('remembers what you had before Calm', () => {
    const s = fakeStorage()
    expect(loadBeforeCalm(s)).toBeNull()
    saveBeforeCalm(PRESETS.energise, s)
    expect(loadBeforeCalm(s)).toEqual(PRESETS.energise)
    expect(s.data[BEFORE_CALM_KEY]).toBeTruthy()
    saveBeforeCalm(null, s)
    expect(loadBeforeCalm(s)).toEqual(PRESETS.energise) // null never wipes a good value
  })
})

describe('Calm Mode switch', () => {
  it('turning Calm on remembers the current settings', () => {
    const { next, before } = toggleCalm(PRESETS.energise, null)
    expect(next).toEqual(PRESETS.calm)
    expect(before).toEqual(PRESETS.energise)
  })

  it('turning Calm off restores what you had', () => {
    const custom: SensorySettings = { ...PRESETS.focus, font: 'dyslexia' }
    expect(toggleCalm(PRESETS.calm, custom)).toEqual({ next: custom, before: null })
  })

  it('turning Calm off with nothing saved goes to Focus, never stays Calm', () => {
    expect(toggleCalm(PRESETS.calm, null).next).toEqual(PRESETS.focus)
    expect(toggleCalm(PRESETS.calm, PRESETS.calm).next).toEqual(PRESETS.focus)
  })

  it('on → off → on keeps your earlier choice', () => {
    const on = toggleCalm(PRESETS.energise, null)
    const off = toggleCalm(on.next, on.before)
    expect(off.next).toEqual(PRESETS.energise)
  })
})

describe('legacy ND mode stays consistent', () => {
  it('maps settings to the old four modes', () => {
    expect(ndModeOf(PRESETS.calm)).toBe('default')
    expect(ndModeOf(PRESETS.focus)).toBe('focus')
    expect(ndModeOf({ ...PRESETS.energise, font: 'dyslexia' })).toBe('dyslexia')
    expect(ndModeOf({ ...PRESETS.energise, contrast: 'high' })).toBe('high-contrast')
  })

  it('applying an old mode and reading it back agrees', () => {
    for (const mode of ['dyslexia', 'high-contrast', 'focus', 'default']) {
      expect(ndModeOf(applyNdMode(PRESETS.energise, mode))).toBe(mode)
    }
  })

  it('"default" clears font and contrast but keeps the rest', () => {
    const s = applyNdMode({ ...PRESETS.energise, font: 'dyslexia', contrast: 'high' }, 'default')
    expect(s).toEqual(PRESETS.energise)
  })

  it('an unknown mode behaves like default instead of throwing', () => {
    expect(applyNdMode(PRESETS.focus, 'zzz')).toEqual(PRESETS.focus)
  })
})

describe('CSS covers every option (no control without a rule)', () => {
  const css = read('app/sensory.css')
  for (const key of SETTING_KEYS) {
    for (const value of OPTIONS[key]) {
      it(`has a rule for [data-${key}="${value}"]`, () => {
        expect(css).toContain(`[data-${key}="${value}"]`)
      })
    }
  }

  it('is imported by globals.css after the tokens', () => {
    const g = read('app/globals.css')
    expect(g).toContain('@import "./sensory.css"')
    expect(g.indexOf('./tokens.css')).toBeLessThan(g.indexOf('./sensory.css'))
  })

  it('motion off really switches animation and transitions off', () => {
    expect(css).toMatch(/\[data-motion="off"\] \*[\s\S]*animation: none !important[\s\S]*transition: none !important/)
  })

  it('a pressed button still looks pressed in Calm', () => {
    expect(css).toMatch(/\[data-layout="calm"\] \.btn\.active \{[^}]*border-color: var\(--text-primary\)/)
  })

  it('hidden progress hides only things marked data-gamify', () => {
    expect(css).toContain('[data-progress="hidden"] [data-gamify] { display: none !important; }')
  })
})

describe('pre-paint boot script', () => {
  function run(stored: string | null | 'throw' | 'missing') {
    const attrs: Record<string, string> = {}
    const document = { documentElement: { setAttribute: (k: string, v: string) => { attrs[k] = v } } }
    const localStorage =
      stored === 'missing' ? undefined : { getItem: () => { if (stored === 'throw') throw new Error('x'); return stored } }
    new Function('document', 'localStorage', bootScript())(document, localStorage)
    return attrs
  }

  it.each(Object.keys(PRESETS) as PresetName[])('applies the saved %s preset exactly like the app does', (name) => {
    expect(run(JSON.stringify(PRESETS[name]))).toEqual(toAttributes(PRESETS[name]))
  })

  it('applies a custom mix', () => {
    const custom = { ...PRESETS.focus, font: 'dyslexia', contrast: 'high' } as SensorySettings
    expect(run(JSON.stringify(custom))).toEqual(toAttributes(custom))
  })

  it.each([null, '', '{bad json', '"string"', '[]', '{"motion":"<img onerror=1>"}', 'throw', 'missing'] as const)(
    'falls back to the Calm defaults for %s and never throws',
    (stored) => {
      expect(run(stored)).toEqual(toAttributes(DEFAULT_SETTINGS))
    },
  )

  it('validates per field like sanitize()', () => {
    const attrs = run(JSON.stringify({ motion: 'full', density: 'nope' }))
    expect(attrs).toEqual(toAttributes(sanitize({ motion: 'full', density: 'nope' })))
  })

  it('uses the same storage key as the app', () => {
    expect(bootScript()).toContain(JSON.stringify(STORAGE_KEY))
  })
})

describe('layout.tsx', () => {
  const layout = read('app/layout.tsx')

  it('ships the Calm defaults on <html> so the server render matches a new person', () => {
    for (const [attr, value] of Object.entries(toAttributes(DEFAULT_SETTINGS))) {
      expect(layout).toContain(`${attr}="${value}"`)
    }
  })

  it('runs the boot script in <head> and wraps the app in the provider', () => {
    expect(layout).toContain('bootScript()')
    expect(layout).toContain('<SensoryProvider>')
  })
})
