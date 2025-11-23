/**
 * Shared resize hook to reduce duplicate event listeners
 * Throttles resize events for better performance
 */
import { useState, useEffect } from 'react'

const useResize = (breakpoints = { mobile: 768, smallMobile: 480 }) => {
  const [windowSize, setWindowSize] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1024,
    height: typeof window !== 'undefined' ? window.innerHeight : 768,
    isMobile: typeof window !== 'undefined' ? window.innerWidth <= breakpoints.mobile : false,
    isSmallMobile: typeof window !== 'undefined' ? window.innerWidth <= breakpoints.smallMobile : false,
  })

  useEffect(() => {
    let timeoutId = null

    const handleResize = () => {
      // Throttle resize events
      if (timeoutId) {
        clearTimeout(timeoutId)
      }

      timeoutId = setTimeout(() => {
        const width = window.innerWidth
        const height = window.innerHeight
        setWindowSize({
          width,
          height,
          isMobile: width <= breakpoints.mobile,
          isSmallMobile: width <= breakpoints.smallMobile,
        })
      }, 150) // Throttle to 150ms
    }

    window.addEventListener('resize', handleResize, { passive: true })
    
    // Initial check
    handleResize()

    return () => {
      window.removeEventListener('resize', handleResize)
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }, [breakpoints.mobile, breakpoints.smallMobile])

  return windowSize
}

export default useResize

