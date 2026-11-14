/**
 * Choosing a context on the Recommendations page fetches recommendations for that context straight away.
 * It used to call the fetch with the previous (empty) context, so the user landed on an empty page until they
 * pressed Refresh.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router'
import { ToastProvider } from '../../contexts/ToastContext'

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: true, user: { id: 1, username: 'u' }, logout: vi.fn() }),
}))

vi.mock('../../services/api', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    refreshTokenIfNeeded: vi.fn(() => Promise.resolve()),
    default: {
      get: vi.fn(() => Promise.resolve({ data: { unified_orchestrator_available: false } })),
      post: vi.fn(() => Promise.resolve({ data: { recommendations: [] } })),
      defaults: { headers: { common: {} } },
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    },
  }
})

const project = { type: 'project', id: 12, title: 'Notes app', description: 'find a note by meaning', technologies: 'pgvector' }
const task = { type: 'task', id: 5, project_id: 12, title: 'Rate limit login', description: '', technologies: 'Flask' }

vi.mock('../../components/SmartContextSelector', () => ({
  default: ({ onSelect }) => (
    <div>
      <button onClick={() => onSelect(project)}>pick project</button>
      <button onClick={() => onSelect(task)}>pick task</button>
    </div>
  ),
}))

import api from '../../services/api'
import Recommendations from '../../pages/Recommendations'

const open = async () => {
  render(
    <BrowserRouter>
      <ToastProvider>
        <Recommendations />
      </ToastProvider>
    </BrowserRouter>
  )
  fireEvent.click((await screen.findAllByText(/Select Context/i, { selector: 'button' }))[0])
}

const recommendationCalls = () =>
  api.post.mock.calls.filter(([url]) => url === '/api/recommendations/unified-orchestrator')

describe('Choosing a recommendations context', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fetches recommendations for the project that was just chosen, without pressing Refresh', async () => {
    await open()
    expect(recommendationCalls()).toHaveLength(0)

    fireEvent.click(await screen.findByText('pick project'))

    await waitFor(() => expect(recommendationCalls()).toHaveLength(1))
    expect(recommendationCalls()[0][1]).toMatchObject({ title: 'Notes app', project_id: 12 })
  })

  it('uses the new context, not the previous one, when the user changes it', async () => {
    await open()
    fireEvent.click(await screen.findByText('pick project'))
    await waitFor(() => expect(recommendationCalls()).toHaveLength(1))

    fireEvent.click((await screen.findAllByText(/Change Context/i))[0])
    fireEvent.click(await screen.findByText('pick task'))

    await waitFor(() => expect(recommendationCalls()).toHaveLength(2))
    expect(recommendationCalls()[1][1]).toMatchObject({ title: 'Rate limit login', task_id: 5, project_id: 12 })
  })
})
