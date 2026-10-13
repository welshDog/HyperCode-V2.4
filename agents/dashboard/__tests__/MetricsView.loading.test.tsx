import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MetricsView } from '../components/views/MetricsView'

vi.mock('../hooks/useMetrics', () => ({
  useMetrics: () => ({ metrics: null, loading: true, refetch: vi.fn() }),
}))
vi.mock('../components/ui/ToastProvider', () => ({
  useToast: () => ({ toast: vi.fn() }),
}))

describe('MetricsView loading state', () => {
  it('shows the hourglass emoji, not a raw \\u23F3 escape', () => {
    const { container } = render(<MetricsView />)
    expect(screen.getByText(/Loading metrics/)).toBeInTheDocument()
    expect(container.textContent).toContain('\u23F3')
    // a literal backslash-u sequence in the DOM text means a JSX text escape was left unprocessed
    expect(container.textContent).not.toMatch(/\\u[0-9A-Fa-f]{4}/)
  })
})
