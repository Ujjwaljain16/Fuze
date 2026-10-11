import { useState } from 'react'
import { Link } from 'react-router'
import { BookOpenText, ChevronDown, CircleAlert, ExternalLink, LoaderCircle, MessageSquareText, Send } from 'lucide-react'
import api from '../services/api'
import { getSafeHref } from '../utils/urlSafety'

export const MAX_QUESTION_LENGTH = 500
const MIN_QUESTION_LENGTH = 3

const EXAMPLES = [
  'What did I save about tuning Postgres indexes?',
  'Summarise what my bookmarks say about React Server Components',
  'Which articles compare RAG and fine-tuning?',
]

// Errors the API reports as {error, message}; key/quota problems point the user at Settings.
const describeError = (err) => {
  const status = err?.response?.status
  const data = err?.response?.data || {}
  const message = data.message || (status === 429
    ? 'You are asking too quickly. Wait a minute and try again.'
    : 'Could not get an answer right now. Please try again.')
  const needsSettings = data.error === 'gemini_key_required' || data.error === 'gemini_quota_exceeded'
  return { message, needsSettings }
}

/** One numbered citation chip: opens the bookmark, shows the cited passage on hover or focus. */
const CitationChip = ({ citation }) => (
  <span className="relative inline-block group align-baseline mx-0.5">
    <a
      href={getSafeHref(citation.url)}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Source ${citation.n}: ${citation.title}`}
      className="inline-flex items-center justify-center min-w-[1.5rem] px-1.5 py-0.5 text-xs font-semibold rounded-md bg-cyan-600/20 text-cyan-300 border border-cyan-500/30 hover:bg-cyan-600/40 hover:text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/40 transition-colors duration-200"
    >
      {citation.n}
    </a>
    <span
      role="tooltip"
      className="pointer-events-none invisible opacity-0 group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100 absolute z-20 left-1/2 -translate-x-1/2 bottom-full mb-2 w-72 max-w-[80vw] p-3 rounded-xl bg-gray-900 border border-gray-700 shadow-2xl text-left transition-opacity duration-200"
    >
      <span className="block text-sm font-semibold text-white mb-1 truncate">{citation.title}</span>
      <span className="block text-xs text-gray-400 leading-relaxed">{citation.snippet}</span>
    </span>
  </span>
)

/** The answer text with each [n] marker replaced by its citation chip. */
const AnswerText = ({ answer, citations }) => {
  const byNumber = new Map(citations.map((c) => [c.n, c]))
  const parts = answer.split(/(\[\d+\])/g)
  return (
    <p className="text-gray-200 leading-relaxed whitespace-pre-line" data-testid="ask-answer">
      {parts.map((part, i) => {
        const match = /^\[(\d+)\]$/.exec(part)
        if (!match) return <span key={i}>{part}</span>
        const citation = byNumber.get(Number(match[1]))
        // The server already drops citations outside the passages it sent; never render a dangling one.
        return citation ? <CitationChip key={i} citation={citation} /> : null
      })}
    </p>
  )
}

const SourceItem = ({ citation }) => {
  const [open, setOpen] = useState(false)
  return (
    <li className="bg-gradient-to-br from-gray-800/50 to-black/50 border border-gray-700 rounded-xl p-4 hover:border-cyan-500/30 transition-all duration-300">
      <div className="flex items-start gap-3">
        <span className="flex-shrink-0 inline-flex items-center justify-center w-7 h-7 text-sm font-semibold rounded-lg bg-cyan-600/20 text-cyan-300">
          {citation.n}
        </span>
        <div className="flex-1 min-w-0">
          <a
            href={getSafeHref(citation.url)}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-white hover:text-cyan-300 transition-colors duration-200 break-words inline-flex items-center gap-1.5"
          >
            <span>{citation.title}</span>
            <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
          </a>
          <p className="text-xs text-cyan-400/80 truncate">{citation.url}</p>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="mt-2 inline-flex items-center gap-1 text-xs text-gray-400 hover:text-cyan-300 transition-colors duration-200"
          >
            <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
            {open ? 'Hide passage' : 'Show passage'}
          </button>
          {open && (
            <blockquote className="mt-2 pl-3 border-l-2 border-cyan-500/30 text-sm text-gray-400 leading-relaxed">
              {citation.snippet}
            </blockquote>
          )}
        </div>
      </div>
    </li>
  )
}

const AskBookmarks = () => {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [asked, setAsked] = useState('')

  const trimmed = question.trim()
  const canAsk = !loading && trimmed.length >= MIN_QUESTION_LENGTH && trimmed.length <= MAX_QUESTION_LENGTH

  const ask = async (e) => {
    e?.preventDefault()
    if (!canAsk) return
    setLoading(true)
    setError(null)
    setResult(null)
    setAsked(trimmed)
    try {
      // Retrieval plus a model call can outlast the default 30 s client timeout.
      const response = await api.post('/api/ask', { question: trimmed }, { timeout: 60000 })
      setResult(response.data)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  const citations = result?.citations || []
  const nothingFound = result && citations.length === 0

  return (
    <div className="space-y-6">
      <div className="p-4 md:p-6 bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl hover:border-cyan-500/30 transition-all duration-300">
        <form onSubmit={ask} className="space-y-3">
          <label htmlFor="ask-question" className="block text-sm font-medium text-gray-300">
            Ask a question. The answer comes only from pages you have saved.
          </label>
          <textarea
            id="ask-question"
            rows={3}
            value={question}
            maxLength={MAX_QUESTION_LENGTH}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) ask(e)
            }}
            placeholder="e.g. What did I save about handling OAuth refresh tokens?"
            className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300 resize-y"
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-gray-500">{trimmed.length}/{MAX_QUESTION_LENGTH}</span>
            <button
              type="submit"
              disabled={!canAsk}
              className="bg-gradient-to-r from-cyan-600 to-teal-600 px-6 py-2.5 rounded-xl font-semibold text-white hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center gap-2"
            >
              {loading ? <LoaderCircle className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              <span>{loading ? 'Asking...' : 'Ask'}</span>
            </button>
          </div>
        </form>
      </div>

      {loading && (
        <div className="text-center py-10" role="status">
          <div className="relative mb-4 inline-block">
            <BookOpenText className="w-8 h-8 text-cyan-400 mx-auto animate-pulse" />
            <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-40 animate-pulse" />
          </div>
          <p className="text-cyan-400">Reading your bookmarks...</p>
        </div>
      )}

      {error && !loading && (
        <div role="alert" className="p-4 border rounded-xl bg-red-500/10 border-red-500/20 text-red-400 flex items-start gap-3">
          <CircleAlert className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p>{error.message}</p>
            {error.needsSettings && (
              <Link to="/profile" className="mt-1 inline-block text-sm text-cyan-400 hover:text-cyan-300 underline">
                Open Settings
              </Link>
            )}
          </div>
        </div>
      )}

      {result && !loading && (
        <div className="p-4 md:p-6 bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl space-y-5">
          <p className="text-sm text-gray-500">
            <span className="text-gray-400 font-medium">You asked:</span> {asked}
          </p>
          {nothingFound ? (
            <div className="p-4 border rounded-xl bg-yellow-500/10 border-yellow-500/20 text-yellow-300" data-testid="ask-not-found">
              <p className="whitespace-pre-line">{result.answer}</p>
            </div>
          ) : (
            <AnswerText answer={result.answer} citations={citations} />
          )}
          {citations.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-300 mb-3">
                Sources <span className="text-gray-500 font-normal">({result.used_passages} passages read)</span>
              </h3>
              <ol className="space-y-3">
                {citations.map((c) => <SourceItem key={c.n} citation={c} />)}
              </ol>
            </div>
          )}
        </div>
      )}

      {!result && !error && !loading && (
        <div className="p-6 border border-dashed border-gray-800 rounded-2xl text-center">
          <MessageSquareText className="w-8 h-8 text-cyan-400/70 mx-auto mb-3" />
          <p className="text-gray-400 mb-4">Ask anything about what you have saved. Every answer cites the bookmarks it came from.</p>
          <div className="flex flex-wrap justify-center gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => setQuestion(ex)}
                className="px-3 py-1.5 text-xs rounded-lg bg-gray-800/60 border border-gray-700 text-gray-300 hover:border-cyan-500/40 hover:text-cyan-300 transition-colors duration-200"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default AskBookmarks
