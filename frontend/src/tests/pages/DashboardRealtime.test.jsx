/**
 * The dashboard's live pipeline counters follow the events the backend actually publishes:
 * backend/utils/event_bus.py XADDs `bookmark.pipeline.<stage>.<status>` events, the SSE gateway
 * sends them as `event: <type>` / `data: <json>`, and services/realtime.js relays them on the
 * window. The dashboard used to match `bookmark.scraping.started` etc., which never arrive.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { BrowserRouter } from 'react-router'
import Dashboard from '../../pages/Dashboard'
import { AuthProvider } from '../../contexts/AuthContext'
import { ToastProvider } from '../../contexts/ToastContext'
import { realtimeClient } from '../../services/realtime'
import { applyPipelineEvent, parsePipelineEventType } from '../../utils/pipelineEvents'
import api from '../../services/api'

vi.mock('../../services/api', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    default: {
      get: vi.fn(),
      post: vi.fn(),
      defaults: { headers: { common: {} } },
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    },
    initializeCSRF: vi.fn(() => Promise.resolve()),
  }
})

class FakeEventSource {
  static instances = []

  constructor(url, options) {
    this.url = url
    this.options = options
    this.listeners = {}
    FakeEventSource.instances.push(this)
  }

  addEventListener(type, listener) {
    (this.listeners[type] ||= []).push(listener)
  }

  close() {
    this.closed = true
  }

  // What the browser does for one SSE frame: `id: ...\nevent: <type>\ndata: <json>\n\n`.
  emit(type, body, id) {
    const message = new MessageEvent(type, { data: JSON.stringify(body), lastEventId: id || '' })
    for (const listener of this.listeners[type] || []) listener(message)
  }
}

let sequence = 0

// Exactly the payload publish_pipeline_event() appends to the user's Redis stream.
const pipelineEvent = (type, { bookmarkId = 41, data = {}, error = null } = {}) => ({
  event_id: `evt_${++sequence}`,
  schema_version: 1,
  pipeline_run_id: 'run_abc123',
  bookmark_id: bookmarkId,
  user_id: 1,
  sequence,
  type,
  data,
  error,
  metadata: {},
  timestamp: '2026-10-12T09:30:00.000000',
})

const counter = (stage) => screen.getByTestId(`pipeline-${stage}`).textContent

describe('Dashboard live pipeline counters', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
    localStorage.clear()
    localStorage.setItem('user', JSON.stringify({ id: 1, username: 'testuser', token: 'access-token' }))

    api.post.mockImplementation((url) => {
      if (url === '/api/realtime/stream-ticket') return Promise.resolve({ data: { ticket: 'ticket-1' } })
      return Promise.resolve({ data: {} })
    })
    api.get.mockImplementation((url) => {
      if (url.includes('/dashboard/summary')) {
        return Promise.resolve({
          data: {
            stats: {
              total_bookmarks: { value: 10, change: '+0%', change_value: 0 },
              active_projects: { value: 1, change: '+0', change_value: 0 },
              weekly_saves: { value: 2, change: '+0%', change_value: 0 },
              success_rate: { value: 90, change: '+0%', change_value: 0 },
            },
            recentBookmarks: [],
            recentProjects: [],
            totalBookmarks: 10,
            totalProjects: 1,
            pipeline_stats: { scraping: 0, embedding: 0, analyzing: 2, analyzed: 5 },
          },
        })
      }
      if (url === '/api/profile') return Promise.resolve({ data: { id: 1, username: 'testuser' } })
      return Promise.resolve({ data: {} })
    })
  })

  afterEach(() => {
    realtimeClient.disconnect()
    realtimeClient.lastEventId = null
    vi.unstubAllGlobals()
  })

  it('updates counters and toasts from real pipeline events', async () => {
    render(
      <BrowserRouter>
        <ToastProvider>
          <AuthProvider>
            <Dashboard />
          </AuthProvider>
        </ToastProvider>
      </BrowserRouter>
    )

    await waitFor(() => expect(counter('analyzed')).toBe('5'))
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1))
    const stream = FakeEventSource.instances[0]
    expect(stream.url).toContain('ticket=ticket-1')

    act(() => stream.emit('bookmark.pipeline.scraping.started',
      pipelineEvent('bookmark.pipeline.scraping.started', { data: { url: 'https://example.com/post' } }), '1-0'))
    expect(counter('scraping')).toBe('1')

    act(() => stream.emit('bookmark.pipeline.scraping.completed',
      pipelineEvent('bookmark.pipeline.scraping.completed', {
        data: { title: 'Post', content_length: 1200, quality_score: 8, strategy: 'trafilatura' },
      }), '2-0'))
    expect(counter('scraping')).toBe('0')

    act(() => stream.emit('bookmark.pipeline.analysis.started',
      pipelineEvent('bookmark.pipeline.analysis.started'), '3-0'))
    expect(counter('analyzing')).toBe('3')

    act(() => stream.emit('bookmark.pipeline.analysis.completed',
      pipelineEvent('bookmark.pipeline.analysis.completed', { data: { duration_ms: 900 } }), '4-0'))
    expect(counter('analyzing')).toBe('2')
    expect(counter('analyzed')).toBe('6')

    act(() => stream.emit('bookmark.pipeline.analysis.failed',
      pipelineEvent('bookmark.pipeline.analysis.failed', {
        error: { error_code: 'RATE_LIMIT_EXCEEDED', retryable: true },
      }), '5-0'))
    expect(counter('analyzing')).toBe('1')
    expect(await screen.findByText(/Gemini rate limit was reached/)).toBeInTheDocument()

    // The SSE id is kept for Last-Event-ID replay on reconnect.
    expect(realtimeClient.lastEventId).toBe('5-0')
  })
})

describe('applyPipelineEvent', () => {
  const start = { scraping: 0, embedding: 0, analyzing: 0, analyzed: 0 }

  it('recognises only bookmark.pipeline.<stage>.<status>', () => {
    expect(parsePipelineEventType('bookmark.pipeline.embedding.failed')).toEqual({ stage: 'embedding', status: 'failed' })
    expect(parsePipelineEventType('bookmark.scraping.started')).toBeNull()
    expect(parsePipelineEventType('bookmark.pipeline.backpressure_applied')).toBeNull()
    expect(parsePipelineEventType('system.connected')).toBeNull()
  })

  it('never lets a counter go negative and ignores unrelated events', () => {
    expect(applyPipelineEvent(start, { type: 'bookmark.pipeline.embedding.completed' }).embedding).toBe(0)
    expect(applyPipelineEvent(start, { type: 'system.connected' })).toBe(start)
    const embedding = applyPipelineEvent(start, { type: 'bookmark.pipeline.embedding.started' })
    expect(embedding.embedding).toBe(1)
    expect(applyPipelineEvent(embedding, { type: 'bookmark.pipeline.embedding.failed' }).embedding).toBe(0)
  })
})
