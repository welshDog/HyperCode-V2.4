import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { XPBar } from '../components/ui/XPBar'

describe('XPBar', () => {
  it('renders correct percentage', () => {
    render(<XPBar xp={250} maxXp={500} level={3} />)
    const bar = screen.getByRole('progressbar')
    expect(bar).toHaveAttribute('aria-valuenow', '50')
    expect(bar).toHaveAttribute('aria-label', '50% to next level')
  })

  it('caps at 100%', () => {
    render(<XPBar xp={600} maxXp={500} level={5} />)
    const bar = screen.getByRole('progressbar')
    expect(bar).toHaveAttribute('aria-valuenow', '100')
  })

  it('shows level number', () => {
    render(<XPBar xp={100} maxXp={500} level={7} />)
    expect(screen.getByText('LVL 7')).toBeInTheDocument()
  })
})
