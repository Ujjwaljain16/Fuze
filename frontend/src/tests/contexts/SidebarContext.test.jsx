import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { SidebarProvider, useSidebar } from '../../contexts/SidebarContext'

const Probe = () => {
  const { isOpen, setOpen } = useSidebar()
  return (
    <div>
      <span data-testid="open">{String(isOpen)}</span>
      <button onClick={() => setOpen(true)}>open</button>
    </div>
  )
}

const setWidth = (width) => Object.defineProperty(window, 'innerWidth', { value: width, configurable: true, writable: true })
const renderProbe = () => render(<SidebarProvider><Probe /></SidebarProvider>)
const original = window.innerWidth

describe('sidebar / drawer initial state', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => setWidth(original))

  it('starts closed on a phone, so the drawer does not cover the page for a new visitor', () => {
    setWidth(375)
    renderProbe()
    expect(screen.getByTestId('open').textContent).toBe('false')
  })

  it('starts closed on a phone even when "open" was saved earlier (from a desktop visit, or an old session)', () => {
    localStorage.setItem('sidebar_open', 'true')
    setWidth(390)
    renderProbe()
    expect(screen.getByTestId('open').textContent).toBe('false')
  })

  it('still opens when the user taps the menu', () => {
    setWidth(375)
    renderProbe()
    act(() => screen.getByText('open').click())
    expect(screen.getByTestId('open').textContent).toBe('true')
  })

  it('on a desktop keeps the saved choice, open by default', () => {
    setWidth(1280)
    renderProbe()
    expect(screen.getByTestId('open').textContent).toBe('true')
  })

  it('on a desktop restores a closed sidebar', () => {
    localStorage.setItem('sidebar_open', 'false')
    setWidth(1280)
    renderProbe()
    expect(screen.getByTestId('open').textContent).toBe('false')
  })

  it('treats 900px as a phone and 901px as a desktop, matching the CSS', () => {
    setWidth(900)
    const { unmount } = renderProbe()
    expect(screen.getByTestId('open').textContent).toBe('false')
    unmount()
    setWidth(901)
    renderProbe()
    expect(screen.getByTestId('open').textContent).toBe('true')
  })
})
