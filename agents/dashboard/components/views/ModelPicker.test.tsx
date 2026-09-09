import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ModelPicker, MODELS, modelLabel } from './ModelPicker'

describe('ModelPicker', () => {
  it('renders a Cloud group and a Free / Local group', () => {
    render(<ModelPicker value="claude-sonnet-5" onChange={() => {}} />)
    const select = screen.getByRole('combobox') as HTMLSelectElement
    const groups = Array.from(select.querySelectorAll('optgroup'))
    expect(groups).toHaveLength(2)
    expect(groups[0].label).toMatch(/cloud/i)
    expect(groups[1].label).toMatch(/free \/ local/i)
  })

  it('lists the free / local model options', () => {
    render(<ModelPicker value="claude-sonnet-5" onChange={() => {}} />)
    expect(screen.getByRole('option', { name: /Nemotron 3 Super 120B/ })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Qwen3 4B/ })).toBeInTheDocument()
  })

  it('disables every free / local option until the FCC path lands', () => {
    render(<ModelPicker value="claude-sonnet-5" onChange={() => {}} />)
    for (const m of MODELS.filter((x) => x.group === 'free')) {
      const opt = screen.getByRole('option', { name: new RegExp(m.label) }) as HTMLOptionElement
      expect(opt.disabled).toBe(true)
    }
    for (const m of MODELS.filter((x) => x.group === 'cloud')) {
      const opt = screen.getByRole('option', { name: new RegExp(m.label) }) as HTMLOptionElement
      expect(opt.disabled).toBe(false)
    }
  })

  it('calls onChange with the picked id when a Cloud option is selected', () => {
    const onChange = vi.fn()
    render(<ModelPicker value="claude-sonnet-5" onChange={onChange} />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'claude-opus-4-8' } })
    expect(onChange).toHaveBeenCalledWith('claude-opus-4-8')
  })

  it('shows the Cloud-vs-Free helper copy', () => {
    render(<ModelPicker value="claude-sonnet-5" onChange={() => {}} />)
    expect(screen.getByText(/uses credits/i)).toBeInTheDocument()
  })

  it('modelLabel resolves known ids, last path segment, and the empty case', () => {
    expect(modelLabel('claude-sonnet-5')).toBe('Sonnet 5')
    expect(modelLabel('nvidia_nim/nvidia/nemotron-3-super-120b-a12b')).toBe('Nemotron 3 Super 120B')
    expect(modelLabel('some/unknown/thing')).toBe('thing')
    expect(modelLabel('bare-id')).toBe('bare-id')
    expect(modelLabel(undefined)).toBe('—')
  })

  it('keeps claude-sonnet-5 as the default (MODELS[0])', () => {
    expect(MODELS[0].id).toBe('claude-sonnet-5')
  })
})
