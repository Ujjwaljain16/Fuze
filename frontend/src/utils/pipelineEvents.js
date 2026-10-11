/**
 * Live pipeline events, as published by backend/utils/event_bus.py and relayed by
 * services/realtime.js on the window as `fuzeRealtimeEvent` (detail = the event body).
 *
 * Types are `bookmark.pipeline.<stage>.<status>`: stage is scraping, embedding or analysis;
 * status is started, completed or failed.
 */
const PREFIX = 'bookmark.pipeline.'

// Which dashboard counter each stage moves while it is in flight.
const IN_FLIGHT_COUNTER = {
  scraping: 'scraping',
  embedding: 'embedding',
  analysis: 'analyzing',
}

export function parsePipelineEventType(type) {
  if (typeof type !== 'string' || !type.startsWith(PREFIX)) return null
  const [stage, status, ...rest] = type.slice(PREFIX.length).split('.')
  if (rest.length || !IN_FLIGHT_COUNTER[stage] || !['started', 'completed', 'failed'].includes(status)) return null
  return { stage, status }
}

/** Returns the counters after `event`, or the same object when the event does not move them. */
export function applyPipelineEvent(stats, event) {
  const parsed = parsePipelineEventType(event?.type)
  if (!parsed) return stats
  const counter = IN_FLIGHT_COUNTER[parsed.stage]
  const current = stats[counter] || 0
  if (parsed.status === 'started') {
    return { ...stats, [counter]: current + 1 }
  }
  const next = { ...stats, [counter]: Math.max(0, current - 1) }
  if (parsed.stage === 'analysis' && parsed.status === 'completed') {
    next.analyzed = (stats.analyzed || 0) + 1
  }
  return next
}

/** A toast for events worth telling the user about, or null. */
export function pipelineEventToast(event) {
  const parsed = parsePipelineEventType(event?.type)
  if (!parsed || parsed.status !== 'failed') return null
  const code = event?.error?.error_code
  if (parsed.stage === 'scraping') {
    return {
      type: 'warning',
      message: "Couldn't fetch a saved page. The bookmark is kept and stays searchable by its title and notes.",
    }
  }
  if (parsed.stage === 'analysis') {
    return {
      type: 'warning',
      message: code === 'RATE_LIMIT_EXCEEDED'
        ? 'AI analysis is paused: the Gemini rate limit was reached. It will resume automatically.'
        : 'AI analysis failed for a bookmark. It will be retried.',
    }
  }
  return { type: 'warning', message: 'Indexing a bookmark for search failed. It will be retried.' }
}
