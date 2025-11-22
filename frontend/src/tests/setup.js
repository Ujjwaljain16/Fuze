import { expect, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
})

// Mock localStorage with actual storage implementation
const localStorageMock = (() => {
  let store = {}
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = String(value)
    },
    removeItem: (key) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
  }
})()
global.localStorage = localStorageMock

// Mock sessionStorage with actual storage implementation
const sessionStorageMock = (() => {
  let store = {}
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = String(value)
    },
    removeItem: (key) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
  }
})()
global.sessionStorage = sessionStorageMock

// Mock EventSource for Server-Sent Events (SSE) - not available in jsdom
class EventSourceMock {
  constructor(url, options) {
    this.url = url
    this.options = options
    this.readyState = 0 // CONNECTING
    this._onopen = null
    this._onmessage = null
    this._onerror = null
    this.listeners = {
      open: [],
      message: [],
      error: []
    }
    
    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = 1 // OPEN
      const openEvent = { type: 'open' }
      if (this._onopen) {
        this._onopen(openEvent)
      }
      this.listeners.open.forEach(listener => {
        if (typeof listener === 'function') {
          listener(openEvent)
        } else if (listener.handleEvent) {
          listener.handleEvent(openEvent)
        }
      })
    }, 0)
  }
  
  get onopen() {
    return this._onopen
  }
  
  set onopen(handler) {
    this._onopen = handler
  }
  
  get onmessage() {
    return this._onmessage
  }
  
  set onmessage(handler) {
    this._onmessage = handler
  }
  
  get onerror() {
    return this._onerror
  }
  
  set onerror(handler) {
    this._onerror = handler
  }
  
  addEventListener(type, listener) {
    if (this.listeners[type]) {
      this.listeners[type].push(listener)
    }
  }
  
  removeEventListener(type, listener) {
    if (this.listeners[type]) {
      this.listeners[type] = this.listeners[type].filter(l => l !== listener)
    }
  }
  
  close() {
    this.readyState = 2 // CLOSED
  }
}

global.EventSource = EventSourceMock

