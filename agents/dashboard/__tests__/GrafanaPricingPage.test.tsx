import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import PricingPage from '../app/pricing/page'

describe('/pricing embeds Grafana', () => {
  const prev = process.env.NEXT_PUBLIC_GRAFANA_URL

  beforeEach(() => {
    process.env.NEXT_PUBLIC_GRAFANA_URL = 'http://127.0.0.1:3001'
  })

  afterEach(() => {
    process.env.NEXT_PUBLIC_GRAFANA_URL = prev
  })

  it('renders an iframe pointing at Grafana launchpad by default', () => {
    render(<PricingPage />)
    const iframe = screen.getByTestId('grafana-iframe') as HTMLIFrameElement
    expect(iframe).toBeInTheDocument()
    expect(iframe.getAttribute('src')).toContain('http://127.0.0.1:3001')
    expect(iframe.getAttribute('src')).toContain('/d/hypercode-ecosystem-launchpad')
  })

  it('renders Grafana toolbar buttons', () => {
    render(<PricingPage />)
    expect(screen.getByRole('button', { name: 'Launchpad' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dashboards' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Explore' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Alerting' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Pop out' })).toBeInTheDocument()
  })
})

