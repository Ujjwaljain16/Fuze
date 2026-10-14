/**
 * Profile page: "Member Since" needs the full profile (the sign-in response doesn't carry it), and the form
 * saves username and interests with one PUT /api/profile.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router'
import { ToastProvider } from '../../contexts/ToastContext'

const refreshUser = vi.fn(() => Promise.resolve(true))
let currentUser

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: true, user: currentUser, logout: vi.fn(), refreshUser }),
}))

vi.mock('../../services/api', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    default: {
      get: vi.fn(() => Promise.resolve({ data: {} })),
      put: vi.fn(() => Promise.resolve({ data: { message: 'Profile updated successfully' } })),
      post: vi.fn(() => Promise.resolve({ data: {} })),
      defaults: { headers: { common: {} } },
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    },
  }
})

import api from '../../services/api'
import Profile from '../../pages/Profile'

const renderProfile = () =>
  render(
    <BrowserRouter>
      <ToastProvider>
        <Profile />
      </ToastProvider>
    </BrowserRouter>
  )

describe('Profile page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    currentUser = {
      id: 1,
      username: 'ujjwal',
      email: 'u@example.com',
      technology_interests: 'Python',
      created_at: '2026-07-04T10:00:00Z',
    }
  })

  it('refreshes the user when it opens, since a stored session may lack the full profile', async () => {
    renderProfile()
    await waitFor(() => expect(refreshUser).toHaveBeenCalled())
  })

  it('shows the member-since date when the profile has one, and N/A only when it does not', () => {
    const { unmount } = renderProfile()
    expect(screen.getByText('Member Since')).toBeInTheDocument()
    expect(screen.queryByText('N/A')).not.toBeInTheDocument()
    unmount()

    currentUser = { id: 1, username: 'ujjwal', email: 'u@example.com' }
    renderProfile()
    expect(screen.getByText('N/A')).toBeInTheDocument()
  })

  it('saves username and interests with one PUT to /api/profile and refreshes the user', async () => {
    renderProfile()
    const interests = screen.getByDisplayValue('Python')
    fireEvent.change(interests, { target: { value: 'Python, Go' } })
    fireEvent.submit(interests.closest('form'))

    await waitFor(() =>
      expect(api.put).toHaveBeenCalledWith('/api/profile', { username: 'ujjwal', technology_interests: 'Python, Go' })
    )
    await waitFor(() => expect(refreshUser.mock.calls.length).toBeGreaterThan(1))
    expect(await screen.findByText('Profile updated successfully!')).toBeInTheDocument()
  })

  it('shows the server message when the save is refused', async () => {
    api.put.mockRejectedValueOnce({ response: { data: { message: 'Username already taken' } } })
    renderProfile()
    const interests = screen.getByDisplayValue('Python')
    fireEvent.submit(interests.closest('form'))

    expect(await screen.findByText('Username already taken')).toBeInTheDocument()
  })
})
