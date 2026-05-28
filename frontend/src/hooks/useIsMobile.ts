import { useEffect, useState } from 'react'

export function useIsMobile(breakpoint = 768) {
  const getIsMobile = () => {
    if (typeof window === 'undefined') return false
    return window.innerWidth < breakpoint
  }

  const [isMobile, setIsMobile] = useState(getIsMobile)

  useEffect(() => {
    const handleResize = () => setIsMobile(getIsMobile())
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [breakpoint])

  return isMobile
}
