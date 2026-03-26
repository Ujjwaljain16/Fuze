import React, { useEffect, useState } from 'react'
import { X } from 'lucide-react'

export default function MobileConsole() {
  const [logs, setLogs] = useState([])
  const [isOpen, setIsOpen] = useState(false)
  const isMobile = window.innerWidth <= 768

  useEffect(() => {
    // Only show on mobile and in development
    if (!isMobile || import.meta.env.PROD) {
      return
    }

    // Capture console.log, console.error, console.warn
    const originalLog = console.log
    const originalError = console.error
    const originalWarn = console.warn

    const addLog = (message, type = 'log') => {
      setLogs((prev) => {
        const newLogs = [
          ...prev,
          {
            id: Date.now() + Math.random(),
            message: String(message),
            type,
            timestamp: new Date().toLocaleTimeString()
          }
        ]
        // Keep only last 50 logs
        return newLogs.slice(-50)
      })
    }

    console.log = function (...args) {
      originalLog(...args)
      addLog(args.map((a) => (typeof a === 'object' ? JSON.stringify(a) : a)).join(' '), 'log')
    }

    console.error = function (...args) {
      originalError(...args)
      addLog(args.map((a) => (typeof a === 'object' ? JSON.stringify(a) : a)).join(' '), 'error')
    }

    console.warn = function (...args) {
      originalWarn(...args)
      addLog(args.map((a) => (typeof a === 'object' ? JSON.stringify(a) : a)).join(' '), 'warn')
    }

    return () => {
      console.log = originalLog
      console.error = originalError
      console.warn = originalWarn
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!isMobile || import.meta.env.PROD) {
    return null
  }

  return (
    <div className="fixed bottom-0 right-0 z-50">
      {/* Floating button to open console */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="m-4 px-3 py-2 bg-cyan-600 text-white text-xs rounded font-mono hover:bg-cyan-700"
        >
          Console ({logs.length})
        </button>
      )}

      {/* Console panel */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-black bg-opacity-95 m-0">
          {/* Header */}
          <div className="flex items-center justify-between p-3 border-b border-gray-700">
            <span className="text-cyan-400 font-bold text-sm">📱 Mobile Console</span>
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-400 hover:text-white"
            >
              <X size={20} />
            </button>
          </div>

          {/* Logs */}
          <div className="flex-1 overflow-y-auto p-3 font-mono text-xs space-y-1">
            {logs.length === 0 ? (
              <div className="text-gray-600">Waiting for logs...</div>
            ) : (
              logs.map((log) => (
                <div
                  key={log.id}
                  className={`${
                    log.type === 'error'
                      ? 'text-red-400'
                      : log.type === 'warn'
                        ? 'text-yellow-400'
                        : 'text-gray-300'
                  }`}
                >
                  <span className="text-gray-600">[{log.timestamp}]</span> {log.message}
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="p-2 border-t border-gray-700 bg-gray-900 text-gray-500 text-xs">
            {logs.length} logs • Scroll to see more
          </div>
        </div>
      )}
    </div>
  )
}
