/**
 * Optimized mouse position tracking hook
 * Throttles mouse move events and only tracks when needed
 */
import { useState, useEffect, useRef } from 'react'

const useMousePosition = (enabled = true, throttleMs = 16) => {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const rafId = useRef(null)
  const lastUpdate = useRef(0)

  useEffect(() => {
    if (!enabled) return

    const handleMouseMove = (e) => {
      const now = Date.now()
      
      // Throttle using requestAnimationFrame for smooth updates
      if (now - lastUpdate.current >= throttleMs) {
        if (rafId.current) {
          cancelAnimationFrame(rafId.current)
        }
        
        rafId.current = requestAnimationFrame(() => {
          setMousePos({ x: e.clientX, y: e.clientY })
          lastUpdate.current = now
        })
      }
    }

    window.addEventListener('mousemove', handleMouseMove, { passive: true })

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      if (rafId.current) {
        cancelAnimationFrame(rafId.current)
      }
    }
  }, [enabled, throttleMs])

  return mousePos
}

export default useMousePosition

