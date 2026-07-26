/**
 * Unified Real-Time Event Client for FUZE Frontend
 * Manages single SSE connection to /api/realtime/stream with Last-Event-ID replay support
 */

import { baseURL } from './api'

class RealtimeClient {
  constructor() {
    this.eventSource = null
    this.lastEventId = null
    this.listeners = new Map()
    this.isConnecting = false
    this.reconnectTimer = null
    this.reconnectDelay = 2000
  }

  connect() {
    if (this.eventSource || this.isConnecting) return

    const storedUser = localStorage.getItem('user')
    let token = null
    if (storedUser) {
      try {
        const parsed = JSON.parse(storedUser)
        token = parsed?.token || parsed?.access_token
      } catch {
        // Ignore parse error
      }
    }

    if (!token) {
      return
    }

    this.isConnecting = true
    const url = new URL(`${baseURL}/api/realtime/stream`)
    url.searchParams.set('token', token)

    if (this.lastEventId) {
      url.searchParams.set('last_event_id', this.lastEventId)
    }

    try {
      this.eventSource = new EventSource(url.toString(), { withCredentials: true })

      this.eventSource.onopen = () => {
        this.isConnecting = false
        this.reconnectDelay = 2000
      }

      this.eventSource.onerror = () => {
        this.isConnecting = false
        this.disconnect()
        this.scheduleReconnect()
      }

      // Default event handlers for pipeline & domain events
      const knownEvents = [
        'system.connected',
        'bookmark.pipeline.scraping.started',
        'bookmark.pipeline.scraping.completed',
        'bookmark.pipeline.embedding.started',
        'bookmark.pipeline.embedding.completed',
        'bookmark.pipeline.embedding.failed',
        'bookmark.pipeline.analysis.started',
        'bookmark.pipeline.analysis.completed',
        'bookmark.pipeline.analysis.failed',
        'bookmark.domain.created',
        'bookmark.domain.updated',
        'bookmark.domain.deleted'
      ]

      knownEvents.forEach((eventType) => {
        this.eventSource.addEventListener(eventType, (e) => {
          if (e.lastEventId) {
            this.lastEventId = e.lastEventId
          }
          try {
            const data = JSON.parse(e.data)
            this.notifyListeners(eventType, data)
            window.dispatchEvent(new CustomEvent('fuzeRealtimeEvent', { detail: data }))
          } catch (err) {
            console.warn('Realtime event parse error:', err)
          }
        })
      })

    } catch {
      this.isConnecting = false
      this.scheduleReconnect()
    }
  }

  scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, this.reconnectDelay)

    this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 30000)
  }

  subscribe(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType).add(callback)

    return () => {
      const callbacks = this.listeners.get(eventType)
      if (callbacks) {
        callbacks.delete(callback)
      }
    }
  }

  notifyListeners(eventType, payload) {
    const callbacks = this.listeners.get(eventType)
    if (callbacks) {
      callbacks.forEach((cb) => {
        try {
          cb(payload)
        } catch (err) {
          console.error(`Error in realtime listener for ${eventType}:`, err)
        }
      })
    }
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
    this.isConnecting = false
  }
}

export const realtimeClient = new RealtimeClient()
