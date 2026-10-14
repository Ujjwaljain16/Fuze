/**
 * The profile form checks a typed username for availability. The account's own name, and a check that could not
 * be completed, must not disable saving; a name that really is taken must, and must say so.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'

vi.mock('../../services/api', () => ({
  checkUsernameAvailability: vi.fn(),
}))

import { checkUsernameAvailability } from '../../services/api'
import ProfileForm from '../../components/ProfileForm'

const renderForm = (username, currentUsername = 'ujjwal') =>
  render(
    <ProfileForm
      formData={{ username, technology_interests: 'Python' }}
      onInputChange={() => {}}
      onSubmit={(e) => e.preventDefault()}
      loading={false}
      currentUsername={currentUsername}
    />
  )

const settle = () => act(async () => { await vi.advanceTimersByTimeAsync(600) })
const saveButton = () => screen.getByRole('button', { name: /update profile/i })

describe('ProfileForm username check', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    checkUsernameAvailability.mockReset()
  })
  afterEach(() => vi.useRealTimers())

  it('does not check, and does not block saving, when the username is the account\'s own', async () => {
    renderForm('ujjwal')
    await settle()
    expect(checkUsernameAvailability).not.toHaveBeenCalled()
    expect(saveButton()).toBeEnabled()
  })

  it('treats the account\'s own name as its own regardless of case', async () => {
    renderForm('UjjWal')
    await settle()
    expect(checkUsernameAvailability).not.toHaveBeenCalled()
    expect(saveButton()).toBeEnabled()
  })

  it('blocks saving and says so when another account has the name', async () => {
    checkUsernameAvailability.mockResolvedValue({ available: false, suggestions: ['ujjwal2', 'ujjwal_7'] })
    renderForm('someone')
    await settle()
    expect(saveButton()).toBeDisabled()
    expect(screen.getByText(/That username is taken/)).toHaveTextContent('Try: ujjwal2, ujjwal_7')
  })

  it('allows saving a free name', async () => {
    checkUsernameAvailability.mockResolvedValue({ available: true, suggestions: [] })
    renderForm('brand_new')
    await settle()
    expect(saveButton()).toBeEnabled()
    expect(screen.queryByText(/taken/)).not.toBeInTheDocument()
  })

  it('does not treat a failed check (network, rate limit) as "taken"', async () => {
    checkUsernameAvailability.mockResolvedValue({ available: false, error: 'Too many requests', suggestions: [] })
    renderForm('brand_new')
    await settle()
    expect(saveButton()).toBeEnabled()
    expect(screen.queryByText(/That username is taken/)).not.toBeInTheDocument()
  })
})
