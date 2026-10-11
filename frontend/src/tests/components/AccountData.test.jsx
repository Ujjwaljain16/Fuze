import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import api from '../../services/api'
import AccountData from '../../components/AccountData'

const logout = vi.fn()
const navigate = vi.fn()
const toast = { success: vi.fn(), error: vi.fn() }

vi.mock('../../contexts/AuthContext', () => ({ useAuth: () => ({ logout }) }))
vi.mock('../../contexts/ToastContext', () => ({ useToast: () => toast }))
vi.mock('react-router-dom', () => ({ useNavigate: () => navigate }))

const openConfirm = () => fireEvent.click(screen.getByRole('button', { name: /delete account/i }))

describe('AccountData', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    logout.mockReset()
    navigate.mockReset()
    toast.success.mockReset()
    toast.error.mockReset()
  })

  it('downloads the export through the API client', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ data: new Blob(['{}']) })
    URL.createObjectURL = vi.fn(() => 'blob:export')
    URL.revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    render(<AccountData />)
    fireEvent.click(screen.getByRole('button', { name: /export my data/i }))

    await waitFor(() => expect(toast.success).toHaveBeenCalled())
    expect(get).toHaveBeenCalledWith('/api/account/export', { responseType: 'blob' })
    expect(click).toHaveBeenCalled()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:export')
  })

  it('asks for confirmation and the password, then signs out and leaves', async () => {
    const del = vi.spyOn(api, 'delete').mockResolvedValue({ data: { message: 'Account deleted' } })
    render(<AccountData hasPassword />)

    openConfirm()
    expect(del).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'my-password' } })
    fireEvent.click(screen.getByRole('button', { name: /delete permanently/i }))

    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/', { replace: true }))
    expect(del).toHaveBeenCalledWith('/api/account', { data: { password: 'my-password' } })
    expect(logout).toHaveBeenCalled()
  })

  it('does not send the request without a password', () => {
    const del = vi.spyOn(api, 'delete')
    render(<AccountData hasPassword />)
    openConfirm()
    fireEvent.click(screen.getByRole('button', { name: /delete permanently/i }))
    expect(del).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent(/password/i)
  })

  it('hides the password field for accounts without a password', async () => {
    const del = vi.spyOn(api, 'delete').mockResolvedValue({ data: {} })
    render(<AccountData hasPassword={false} />)
    openConfirm()
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /delete permanently/i }))
    await waitFor(() => expect(logout).toHaveBeenCalled())
    expect(del).toHaveBeenCalledWith('/api/account', { data: {} })
  })

  it('shows the error and stays signed in when deletion is refused', async () => {
    vi.spyOn(api, 'delete').mockRejectedValue({
      response: { status: 403, data: { message: 'Password is incorrect', error: 'invalid_password' } },
    })
    render(<AccountData hasPassword />)
    openConfirm()
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /delete permanently/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Password is incorrect')
    expect(logout).not.toHaveBeenCalled()
    expect(navigate).not.toHaveBeenCalled()
  })
})
