import React from 'react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { ToastProvider, useToast } from '@/components/ui/ToastProvider'
import { FocusSessionControl } from '@/components/crew/FocusSessionControl'
import {
  STORAGE_KEY, sanitize, startFocus, endFocus, setMinutes, remainingSeconds, getSnapshot, isFocusActive, resetFocusStore,
} from '@/lib/focus/store'

// vitest.setup.ts mocks ToastProvider globally; this file needs the real one.
vi.unmock('@/components/ui/ToastProvider')

beforeEach(() => {
  window.localStorage.clear()
  document.documentElement.removeAttribute('data-focus')
  resetFocusStore()
})
afterEach(() => vi.useRealTimers())

describe('focus store', () => {
  it('sanitizes junk to the inactive default', () => {
    expect(sanitize(null)).toEqual({ active: false, startedAt: null, minutes: 25 })
    expect(sanitize({ active: true })).toMatchObject({ active: false }) // active but no start time
    expect(sanitize({ active: true, startedAt: 'x', minutes: 25 })).toMatchObject({ active: false })
    expect(sanitize({ active: false, minutes: 999 }).minutes).toBe(25)
    expect(sanitize({ active: true, startedAt: 5, minutes: 45 })).toEqual({ active: true, startedAt: 5, minutes: 45 })
  })

  it('start sets data-focus and persists; end clears both', () => {
    startFocus(10, 1000)
    expect(document.documentElement.getAttribute('data-focus')).toBe('on')
    expect(JSON.parse(window.localStorage.getItem(STORAGE_KEY) as string)).toEqual({ active: true, startedAt: 1000, minutes: 10 })
    expect(isFocusActive()).toBe(true)
    endFocus()
    expect(document.documentElement.hasAttribute('data-focus')).toBe(false)
    expect(isFocusActive()).toBe(false)
    expect(getSnapshot().minutes).toBe(10) // remembers your chunk length
  })

  it('survives a reload', () => {
    startFocus(45, 2000)
    resetFocusStore() // simulates a fresh page load
    expect(getSnapshot()).toEqual({ active: true, startedAt: 2000, minutes: 45 })
  })

  it('counts down and stops at zero (never negative)', () => {
    const s = { active: true, startedAt: 0, minutes: 10 as const }
    expect(remainingSeconds(s, 0)).toBe(600)
    expect(remainingSeconds(s, 599_500)).toBe(1)
    expect(remainingSeconds(s, 9_999_999)).toBe(0)
    expect(remainingSeconds({ active: false, startedAt: null, minutes: 25 })).toBe(1500)
  })

  it('setMinutes changes the chunk length without starting', () => {
    setMinutes(45)
    expect(getSnapshot()).toMatchObject({ active: false, minutes: 45 })
  })
})

function Pusher(): React.JSX.Element {
  const { pushToast } = useToast()
  return (
    <>
      <button onClick={() => pushToast({ title: 'Build finished', variant: 'success' })}>info</button>
      <button onClick={() => pushToast({ title: 'Build failed', variant: 'error' })}>err</button>
    </>
  )
}

describe('FocusSessionControl + quiet toasts', () => {
  const setup = () => render(<ToastProvider><FocusSessionControl /><Pusher /></ToastProvider>)

  it('offers a chunk length and Start; the timer is a suggestion, not a rule', () => {
    setup()
    expect(screen.getByRole('combobox', { name: 'Focus chunk length' })).toHaveValue('25')
    fireEvent.click(screen.getByRole('button', { name: 'Start focus' }))
    expect(screen.getByRole('timer')).toHaveTextContent(/Focus: 25:00 left/)
    expect(document.documentElement.getAttribute('data-focus')).toBe('on')
  })

  it('when time is up it says so but does NOT end the session', () => {
    vi.useFakeTimers()
    setup()
    act(() => { startFocus(10, Date.now()) })
    act(() => { vi.advanceTimersByTime(11 * 60_000) })
    expect(screen.getByRole('timer')).toHaveTextContent('Chunk done. Break when you are ready.')
    expect(isFocusActive()).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'End focus' }))
    expect(isFocusActive()).toBe(false)
  })

  it('non-error toasts wait quietly in the bell during focus; errors still show', () => {
    setup()
    fireEvent.click(screen.getByRole('button', { name: 'Start focus' }))
    fireEvent.click(screen.getByRole('button', { name: 'info' }))
    expect(screen.queryByText('Build finished')).toBeNull() // not shown as a toast
    expect(screen.getByTestId('focus-waiting')).toHaveTextContent('1 waiting in the bell')
    fireEvent.click(screen.getByRole('button', { name: 'err' }))
    expect(screen.getByText('Build failed')).toBeInTheDocument() // errors may interrupt
  })

  it('outside focus, toasts behave as normal', () => {
    setup()
    fireEvent.click(screen.getByRole('button', { name: 'info' }))
    expect(screen.getByText('Build finished')).toBeInTheDocument()
  })
})
