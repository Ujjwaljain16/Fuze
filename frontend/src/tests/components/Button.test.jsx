/**
 * Unit tests for Button component
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Button from '../../components/Button'

describe('Button', () => {
  it('renders button with text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    
    fireEvent.click(screen.getByText('Click me'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('disables button when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>)
    expect(screen.getByText('Disabled')).toBeDisabled()
  })

  it('applies variant classes', () => {
    const { container } = render(<Button variant="primary">Primary</Button>)
    const button = container.querySelector('button')
    // Button uses Tailwind classes, check for gradient which indicates primary variant
    expect(button.className).toContain('bg-gradient-to-r')
    expect(button.className).toContain('from-cyan-600')
  })
})


describe('Button variants', () => {
  it('makes secondary look different from primary (Cancel used to look exactly like Save)', async () => {
    const { render: r } = await import('@testing-library/react')
    const { default: Btn } = await import('../../components/Button')
    const primary = r(<Btn variant="primary">Save</Btn>).container.firstChild.className
    const secondary = r(<Btn variant="secondary">Cancel</Btn>).container.firstChild.className
    expect(primary).toMatch(/bg-gradient-to-r/)
    expect(secondary).not.toMatch(/bg-gradient-to-r/)
  })
})
