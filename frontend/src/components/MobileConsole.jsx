import React, { useEffect, useState } from 'react'
import { X } from 'lucide-react'

function stringifyArg(arg) {
  if (typeof arg === 'string') {
    return arg
  }
  try {
    return JSON.stringify(arg)
  } catch {
    return String(arg)
  }
}

export default function MobileConsole() {
  const [logs, setLogs] = useState([])
  const [isOpen, setIsOpen] = useState(false)
  const isMobile = window.innerWidth <= 768

  useEffect(() => {
    if (!isMobile) {
      return undefined
    }

    const originalLog = console.log
    const originalError = console.error
    const originalWarn = console.warn

    const addLog = (message, type = 'log') => {
      setLogs((prev) => {
        const next = prev.concat({
          id: `${Date.now()}-${Math.random()}`,
          message,
          type,
          timestamp: new Date().toLocaleTimeString()
        })
        return next.slice(-50)
      })
    }

    console.log = (...args) => {
      originalLog(...args)
      addLog(args.map(stringifyArg).join(' '), 'log')
    }

    console.error = (...args) => {
      originalError(...args)
      addLog(args.map(stringifyArg).join(' '), 'error')
    }

    console.warn = (...args) => {
      originalWarn(...args)
      addLog(args.map(stringifyArg).join(' '), 'warn')
    }

    return () => {
      console.log = originalLog
      console.error = originalError
      console.warn = originalWarn
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!isMobile) {
    return null
  }

  return (
    <div className="fixed bottom-0 right-0 z-50">
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="m-4 rounded bg-cyan-600 px-3 py-2 font-mono text-xs text-white hover:bg-cyan-700"
        >
          Console ({logs.length})
        </button>
      )}

      {isOpen && (
        <div className="fixed inset-0 z-50 m-0 flex flex-col bg-black bg-opacity-95">
          <div className="flex items-center justify-between border-b border-gray-700 p-3">
            <span className="text-sm font-bold text-cyan-400">Mobile Console</span>
            <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-white">
              <X size={20} />
            </button>
          </div>

          <div className="flex-1 space-y-1 overflow-y-auto p-3 font-mono text-xs">
            {logs.length === 0 ? (
              <div className="text-gray-600">Waiting for logs...</div>
            ) : (
              logs.map((log) => (
                <div
                  key={log.id}
                  className={
                    log.type === 'error'
                      ? 'text-red-400'
                      : log.type === 'warn'
                        ? 'text-yellow-400'
                        : 'text-gray-300'
                  }
                >
                  <span className="text-gray-600">[{log.timestamp}]</span> {log.message}
                </div>
              ))
            )}
          </div>

          <div className="border-t border-gray-700 bg-gray-900 p-2 text-xs text-gray-500">
            {logs.length} logs | Scroll to see more
          </div>
        </div>
      )}
    </div>
  )
}
