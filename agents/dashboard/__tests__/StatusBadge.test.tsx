import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { StatusBadge } from '../components/ui/StatusBadge'

describe('StatusBadge', () => {
  const statuses = ['healthy', 'warning', 'error', 'idle'] as const

  statuses.forEach((status) => {
    it(`renders ${status} correctly`, () => {
      render(<StatusBadge status={status} />)
      expect(screen.getByRole('status', { name: `Status: ${status}` })).toBeInTheDocument()
    })
  })
})
