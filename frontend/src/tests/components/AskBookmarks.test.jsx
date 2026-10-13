import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import AskBookmarks from '../../components/AskBookmarks'
import api from '../../services/api'

vi.mock('../../services/api', () => ({
  default: { post: vi.fn(), get: vi.fn() },
}))

const renderAsk = () => render(<MemoryRouter><AskBookmarks /></MemoryRouter>)

const askQuestion = async (user, text = 'How do I tune HNSW?') => {
  await user.type(screen.getByLabelText(/ask a question/i), text)
  await user.click(screen.getByRole('button', { name: /^ask$/i }))
}

const ANSWER = {
  answer: 'Raise ef_search for recall [1]. IVFFlat is the other option [2]. Made up [9].',
  citations: [
    { n: 1, bookmark_id: 11, title: 'HNSW tuning', url: 'https://example.com/hnsw', snippet: 'Raise ef_search to trade speed for recall.' },
    { n: 2, bookmark_id: 12, title: 'Vector indexes', url: 'https://example.com/ivf', snippet: 'IVFFlat needs lists chosen at build time.' },
  ],
  used_passages: 6,
}

describe('AskBookmarks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows the empty state and fills the box from an example', async () => {
    const user = userEvent.setup()
    renderAsk()
    expect(screen.getByText(/every answer cites the bookmarks/i)).toBeInTheDocument()
    const example = screen.getByRole('button', { name: /tuning postgres indexes/i })
    await user.click(example)
    expect(screen.getByLabelText(/ask a question/i)).toHaveValue(example.textContent)
  })

  it('does not send questions that are too short', async () => {
    const user = userEvent.setup()
    renderAsk()
    await user.type(screen.getByLabelText(/ask a question/i), 'hi')
    expect(screen.getByRole('button', { name: /^ask$/i })).toBeDisabled()
    expect(api.post).not.toHaveBeenCalled()
  })

  it('renders the answer with citation chips that open the cited bookmarks', async () => {
    let resolve
    api.post.mockReturnValue(new Promise((r) => { resolve = r }))
    const user = userEvent.setup()
    renderAsk()
    await askQuestion(user)

    expect(screen.getByText(/reading your bookmarks/i)).toBeInTheDocument()
    expect(api.post).toHaveBeenCalledWith('/api/ask', { question: 'How do I tune HNSW?' }, { timeout: 60000 })
    resolve({ data: ANSWER })

    const answer = await screen.findByTestId('ask-answer')
    const chip1 = within(answer).getByRole('link', { name: 'Source 1: HNSW tuning' })
    expect(chip1).toHaveAttribute('href', 'https://example.com/hnsw')
    expect(chip1).toHaveAttribute('target', '_blank')
    expect(within(answer).getByRole('link', { name: 'Source 2: Vector indexes' })).toHaveAttribute('href', 'https://example.com/ivf')
    // A marker with no matching citation is not rendered as a chip or left as raw text.
    expect(answer.textContent).not.toContain('[9]')
    expect(within(answer).getAllByRole('link')).toHaveLength(2)
    // The cited passage is available on hover.
    expect(within(answer).getAllByRole('tooltip', { hidden: true })[0]).toHaveTextContent('Raise ef_search to trade speed for recall.')
    expect(screen.getByText(/6 passages read/i)).toBeInTheDocument()
  })

  it('expands a source to show the passage it came from', async () => {
    api.post.mockResolvedValue({ data: ANSWER })
    const user = userEvent.setup()
    renderAsk()
    await askQuestion(user)
    const toggles = await screen.findAllByRole('button', { name: /show passage/i })
    expect(screen.queryByText('IVFFlat needs lists chosen at build time.', { selector: 'blockquote' })).not.toBeInTheDocument()
    await user.click(toggles[1])
    expect(screen.getByText('IVFFlat needs lists chosen at build time.', { selector: 'blockquote' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /hide passage/i })).toHaveAttribute('aria-expanded', 'true')
  })

  it('lists a page once, with every passage that was cited from it', async () => {
    api.post.mockResolvedValue({
      data: {
        answer: 'Docker packages apps [1][2]. Compose runs several containers [3].',
        citations: [
          { n: 1, bookmark_id: 5, title: 'Awesome Docker', url: 'https://example.com/awesome', snippet: 'A curated list of Docker resources.' },
          { n: 2, bookmark_id: 5, title: 'Awesome Docker', url: 'https://example.com/awesome', snippet: 'Docker Engine is a portable runtime.' },
          { n: 3, bookmark_id: 6, title: 'Compose guide', url: 'https://example.com/compose', snippet: 'Define multi-container apps.' },
        ],
        used_passages: 9,
      },
    })
    const user = userEvent.setup()
    renderAsk()
    await askQuestion(user)
    const rows = await screen.findAllByRole('listitem')
    expect(rows).toHaveLength(2)                                       // two pages, not three passages
    expect(within(rows[0]).getByTestId('source-numbers')).toHaveTextContent('1, 2')
    expect(within(rows[1]).getByTestId('source-numbers')).toHaveTextContent('3')
    // the answer still has a chip for every citation
    expect(within(screen.getByTestId('ask-answer')).getAllByRole('link')).toHaveLength(3)

    await user.click(within(rows[0]).getByRole('button', { name: /show 2 passages/i }))
    expect(screen.getByText('A curated list of Docker resources.', { selector: 'blockquote' })).toBeInTheDocument()
    expect(screen.getByText('Docker Engine is a portable runtime.', { selector: 'blockquote' })).toBeInTheDocument()
    expect(within(rows[1]).getByRole('button', { name: /show passage$/i })).toBeInTheDocument()   // a single passage keeps its label
  })

  it('says plainly when nothing in the bookmarks answers the question', async () => {
    api.post.mockResolvedValue({ data: { answer: "I couldn't find anything in your saved bookmarks.", citations: [], used_passages: 0 } })
    const user = userEvent.setup()
    renderAsk()
    await askQuestion(user)
    expect(await screen.findByTestId('ask-not-found')).toHaveTextContent("couldn't find anything")
    expect(screen.queryByText(/sources/i)).not.toBeInTheDocument()
  })

  it('shows the server message and a Settings link when there is no Gemini key', async () => {
    api.post.mockRejectedValue({ response: { status: 402, data: { error: 'gemini_key_required', message: 'Add your Gemini API key in Settings.' } } })
    const user = userEvent.setup()
    renderAsk()
    await askQuestion(user)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Add your Gemini API key in Settings.')
    expect(within(alert).getByRole('link', { name: /open settings/i })).toHaveAttribute('href', '/profile')
  })

  it('shows a generic error when the request fails without a message', async () => {
    api.post.mockRejectedValue(new Error('Network Error'))
    const user = userEvent.setup()
    renderAsk()
    await askQuestion(user)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/could not get an answer/i)
    expect(within(alert).queryByRole('link')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: /^ask$/i })).toBeEnabled())
  })

  it('never renders an unsafe bookmark URL as a live link', async () => {
    api.post.mockResolvedValue({ data: {
      answer: 'See this [1].',
      citations: [{ n: 1, bookmark_id: 3, title: 'Evil', url: 'javascript:alert(1)', snippet: 'x' }],
      used_passages: 1,
    } })
    const user = userEvent.setup()
    renderAsk()
    await askQuestion(user)
    const chip = await screen.findByRole('link', { name: 'Source 1: Evil' })
    expect(chip).toHaveAttribute('href', '#')
  })
})
