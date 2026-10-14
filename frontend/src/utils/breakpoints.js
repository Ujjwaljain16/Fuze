/** At or below this width the app uses the phone layout: a drawer menu instead of a sidebar. */
export const MOBILE_BREAKPOINT = 900

export const isMobileWidth = () => typeof window !== 'undefined' && window.innerWidth <= MOBILE_BREAKPOINT
