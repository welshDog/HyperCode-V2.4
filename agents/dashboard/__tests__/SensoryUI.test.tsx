import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act, within } from '@testing-library/react'
import { SensoryProvider, useSensory } from '@/components/sensory/SensoryProvider'
import { CalmModeToggle } from '@/components/sensory/CalmModeToggle'
import { SensorySettingsPanel } from '@/components/sensory/SensorySettingsPanel'
import { XPBar } from '@/components/ui/XPBar'
import { OPTIONS, PRESETS, STORAGE_KEY, toAttributes } from '@/lib/sensory/settings'
import { resetStore } from '@/lib/sensory/store'

vi.mock('@/components/views/StudioView', () => ({ StudioView: () => <div data-testid="studio" /> }))
vi.mock('@/components/views/SkillFinder', () => ({ SkillFinder: () => <div data-testid="skill-finder" /> }))
vi.mock('@/components/crew/CalmCardPanel', () => ({ CalmCardPanel: () => <div data-testid="calm-card" /> }))

const html = document.documentElement
const attr = (name: string) => html.getAttribute(`data-${name}`)

function wrap(ui: React.ReactElement) {
  return render(<SensoryProvider>{ui}</SensoryProvider>)
}

beforeEach(() => {
  localStorage.clear()
  resetStore()
  for (const a of [...html.getAttributeNames()]) if (a.startsWith('data-')) html.removeAttribute(a)
})

describe('SensoryProvider', () => {
  it('starts new people in Calm and puts the attributes on <html>', () => {
    wrap(<div />)
    for (const [k, v] of Object.entries(toAttributes(PRESETS.calm))) expect(html.getAttribute(k)).toBe(v)
  })

  it('loads saved settings', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(PRESETS.energise))
    wrap(<div />)
    expect(attr('motion')).toBe('full')
    expect(attr('sensory')).toBe('energise')
  })

  it('ignores corrupt storage', () => {
    localStorage.setItem(STORAGE_KEY, '{nope')
    wrap(<div />)
    expect(attr('sensory')).toBe('calm')
  })

  it('follows a change made in another tab', () => {
    wrap(<div />)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(PRESETS.focus))
    act(() => { window.dispatchEvent(new StorageEvent('storage', { key: STORAGE_KEY })) })
    expect(attr('sensory')).toBe('focus')
  })

  it('throws a clear error outside the provider', () => {
    const Bad = () => { useSensory(); return null }
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Bad />)).toThrow(/SensoryProvider/)
    spy.mockRestore()
  })
})

describe('CalmModeToggle', () => {
  it('says its state in words and is a pressed-state button', () => {
    wrap(<CalmModeToggle />)
    const btn = screen.getByRole('button', { name: /Calm mode/ })
    expect(btn).toHaveTextContent('Calm mode: On')
    expect(btn).toHaveAttribute('aria-pressed', 'true')
  })

  it('turns off to Focus and back on, with no confirmation dialog', () => {
    wrap(<CalmModeToggle />)
    const btn = screen.getByRole('button', { name: /Calm mode/ })
    fireEvent.click(btn)
    expect(btn).toHaveTextContent('Calm mode: Off')
    expect(attr('layout')).toBe('full')
    expect(attr('sensory')).toBe('focus')
    fireEvent.click(btn)
    expect(btn).toHaveTextContent('Calm mode: On')
    expect(attr('motion')).toBe('off')
  })

  it('remembers what you had before Calm', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(PRESETS.energise))
    wrap(<CalmModeToggle />)
    const btn = screen.getByRole('button', { name: /Calm mode/ })
    fireEvent.click(btn) // on
    expect(attr('sensory')).toBe('calm')
    fireEvent.click(btn) // off → back to energise
    expect(attr('sensory')).toBe('energise')
  })

  it('saves the choice', () => {
    wrap(<CalmModeToggle />)
    fireEvent.click(screen.getByRole('button', { name: /Calm mode/ }))
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}').layout).toBe('full')
  })
})

describe('SensorySettingsPanel', () => {
  it('has every option of every setting as a labelled radio', () => {
    wrap(<SensorySettingsPanel />)
    for (const key of Object.keys(OPTIONS) as (keyof typeof OPTIONS)[]) {
      const radios = screen.getAllByRole('radio').filter((r) => (r as HTMLInputElement).name === key)
      expect(radios.map((r) => (r as HTMLInputElement).value)).toEqual([...OPTIONS[key]])
    }
  })

  it('presets apply everything at once and show which one is active', () => {
    wrap(<SensorySettingsPanel />)
    const group = screen.getByRole('group', { name: 'Presets' })
    expect(within(group).getByRole('button', { name: 'Calm' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(within(group).getByRole('button', { name: 'Energise' }))
    expect(attr('sensory')).toBe('energise')
    expect(within(group).getByRole('button', { name: 'Energise' })).toHaveAttribute('aria-pressed', 'true')
    expect(within(group).getByRole('button', { name: 'Calm' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('changing one setting applies at once and the preset becomes Custom', () => {
    wrap(<SensorySettingsPanel />)
    fireEvent.click(screen.getByLabelText('Full', { selector: 'input[name="motion"]' }))
    expect(attr('motion')).toBe('full')
    expect(attr('sensory')).toBe('custom')
    expect(screen.getByTestId('preset-help')).toHaveTextContent('Custom')
  })

  it('reflects saved settings in the controls', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...PRESETS.focus, font: 'dyslexia' }))
    wrap(<SensorySettingsPanel />)
    expect(screen.getByLabelText('Dyslexia-friendly')).toBeChecked()
    expect(screen.getByLabelText('Reduced')).toBeChecked()
  })

  it('says progress still counts while hidden', () => {
    wrap(<SensorySettingsPanel />)
    expect(screen.getByText(/Progress still counts while hidden/)).toBeInTheDocument()
  })
})

describe('legacy ND toggle compatibility', () => {
  function Probe() {
    const { ndMode, setNdMode, settings } = useSensory()
    return (
      <div>
        <span data-testid="nd">{ndMode}</span>
        <span data-testid="font">{settings.font}</span>
        <button onClick={() => setNdMode('dyslexia')}>dys</button>
        <button onClick={() => setNdMode('default')}>def</button>
      </div>
    )
  }

  it('the old toggle writes the new settings and reads them back', () => {
    wrap(<Probe />)
    expect(screen.getByTestId('nd')).toHaveTextContent('default')
    fireEvent.click(screen.getByText('dys'))
    expect(screen.getByTestId('nd')).toHaveTextContent('dyslexia')
    expect(attr('font')).toBe('dyslexia')
    fireEvent.click(screen.getByText('def'))
    expect(attr('font')).toBe('inter')
  })
})

describe('XPBar progress marker', () => {
  it('is marked so Calm can hide it', () => {
    const { container } = render(<XPBar xp={10} maxXp={100} level={1} />)
    expect(container.querySelector('[data-gamify]')).not.toBeNull()
  })
})

describe('/ide layout', () => {
  async function ide() {
    const { default: IDEPage } = await import('@/app/ide/page')
    return wrap(<IDEPage />)
  }

  it('Calm: the Calm Card comes first and the skill finder is tucked away', async () => {
    await ide()
    const nodes = screen.getAllByTestId(/calm-card|studio|calm-more/).map((n) => n.getAttribute('data-testid'))
    expect(nodes).toEqual(['calm-card', 'calm-more', 'studio'])
    const more = screen.getByTestId('calm-more') as HTMLDetailsElement
    expect(more.open).toBe(false)
    expect(within(more).getByTestId('skill-finder')).toBeInTheDocument()
    expect(within(more).getByText(/More tools/)).toBeInTheDocument()
  })

  it('Full: nothing is tucked away', async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(PRESETS.focus))
    await ide()
    expect(screen.queryByTestId('calm-more')).toBeNull()
    expect(screen.getByTestId('skill-finder')).toBeInTheDocument()
    expect(screen.getByTestId('calm-card')).toBeInTheDocument()
  })
})
