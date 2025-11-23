import { useState, useEffect, useMemo } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import api from '../services/api'
import { useErrorHandler } from '../hooks/useErrorHandler'
import useResize from '../hooks/useResize'
import useMousePosition from '../hooks/useMousePosition'
import { 
  Bookmark, FolderOpen, Plus, ExternalLink, Calendar, Sparkles, Lightbulb, 
  Settings, Zap, Grid3X3, List, Star, Clock, TrendingUp, 
  BarChart3, Globe, MoreHorizontal, Tag, LogOut
} from 'lucide-react'
import OnboardingBanner from '../components/OnboardingBanner'
import logo1 from '../assets/logo1.svg'

const Dashboard = () => {
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()
  const { handleError } = useErrorHandler()
  
  // Clean username for display - memoized to avoid recalculation
  const cleanDisplayName = useMemo(() => {
    const displayName = user?.username || user?.name || 'User'
    return displayName.replace(/[^\w\s]/g, '').trim() || 'User'
  }, [user?.username, user?.name])
  const [stats, setStats] = useState({
    bookmarks: 0,
    projects: 0
  })
  const [dashboardStats, setDashboardStats] = useState({
    total_bookmarks: { value: 0, change: '0%', change_value: 0 },
    active_projects: { value: 0, change: '0', change_value: 0 },
    weekly_saves: { value: 0, change: '0%', change_value: 0 },
    success_rate: { value: 0, change: '0%', change_value: 0 }
  })
  const [recentBookmarks, setRecentBookmarks] = useState([])
  const [recentProjects, setRecentProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [importProgress, setImportProgress] = useState(null)
  const [analysisProgress, setAnalysisProgress] = useState(null)
  const [viewMode, setViewMode] = useState('grid')
  
  // Use optimized hooks for resize and mouse tracking
  const { isMobile, isSmallMobile } = useResize({ mobile: 768, smallMobile: 480 })
  const mousePos = useMousePosition(true, 16) // Throttle to 16ms (60fps)

  useEffect(() => {
    if (isAuthenticated) {
      fetchDashboardData()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated])

  // Use Server-Sent Events for progress updates - LAZY INITIALIZATION
  // Only open SSE streams AFTER dashboard data has loaded to avoid blocking
  useEffect(() => {
    if (!isAuthenticated || !user?.id || loading) return // Wait for dashboard to load first

    const token = localStorage.getItem('token')
    if (!token) return

    // Get base URL for SSE (use same logic as api.js)
    const getBaseURL = () => {
      const isDevelopment = window.location.hostname === 'localhost' || 
                           window.location.hostname === '127.0.0.1'
      if (isDevelopment) {
        return import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'
      } else {
        return import.meta.env.VITE_API_URL
      }
    }

    const baseURL = getBaseURL()
    let combinedEventSource = null
    let closedByIdle = false

    const openCombinedStream = () => {
      // Close existing stream if open
      if (combinedEventSource && combinedEventSource.readyState !== EventSource.CLOSED) {
        combinedEventSource.close()
      }

      // Use combined SSE endpoint - single connection for both import and analysis
      combinedEventSource = new EventSource(
        `${baseURL}/api/bookmarks/progress/stream?token=${encodeURIComponent(token)}`,
        { withCredentials: true }
      )

      combinedEventSource.onmessage = (event) => {
        try {
          // Skip heartbeat comments
          if (event.data.trim().startsWith(':')) {
            return
          }
          
          const message = JSON.parse(event.data)
          
          // Handle different message types
          if (message.type === 'idle' && message.message?.includes('Closing connection')) {
            closedByIdle = true
            combinedEventSource.close()
            setImportProgress(null)
            setAnalysisProgress(null)
            return
          }
          
          if (message.type === 'timeout') {
            console.warn('SSE stream timeout:', message.message)
            combinedEventSource.close()
            return
          }
          
          if (message.type === 'error') {
            console.error('SSE stream error:', message.message)
            return
          }
          
          // Handle import progress
          if (message.type === 'import') {
            if (message.data) {
              closedByIdle = false // Reset idle flag when we get activity
              setImportProgress(message.data)
            } else {
              setImportProgress(null)
            }
          }
          
          // Handle analysis progress
          if (message.type === 'analysis') {
            if (message.data) {
              closedByIdle = false // Reset idle flag when we get activity
              setAnalysisProgress(message.data)
            } else {
              setAnalysisProgress(null)
            }
          }
        } catch (error) {
          console.error('Error parsing combined progress:', error)
        }
      }

      combinedEventSource.onerror = (error) => {
        // If connection was closed due to idle timeout, prevent automatic reconnection
        if (combinedEventSource.readyState === EventSource.CLOSED && closedByIdle) {
          console.log('Combined progress SSE closed (idle timeout) - not reconnecting')
          return
        }
        
        // If connection closes but wasn't closed by idle, allow reconnection (might be network issue)
        if (combinedEventSource.readyState === EventSource.CLOSED && !closedByIdle) {
          console.log('Combined progress SSE closed (will reconnect if needed)')
          // Reopen after a short delay if not closed by idle
          setTimeout(() => {
            if (!closedByIdle) {
              openCombinedStream()
            }
          }, 2000)
          return
        }
        
        // Log other errors
        if (combinedEventSource.readyState === EventSource.CONNECTING) {
          console.warn('Combined progress SSE reconnecting...')
        } else {
          console.error('Combined progress SSE error:', error)
        }
      }
    }

    // Open combined stream initially (after dashboard loads)
    openCombinedStream()

    // Poll to check if stream needs to be reopened (e.g., if import starts after idle closure)
    // Check every 5 seconds if stream is closed and reopen if needed
    const checkAndReopenStream = setInterval(() => {
      // If stream is closed but not due to idle, try to reopen
      if (combinedEventSource && combinedEventSource.readyState === EventSource.CLOSED && !closedByIdle) {
        console.log('Reopening combined progress SSE stream...')
        openCombinedStream()
      }
    }, 5000) // Check every 5 seconds

    // Cleanup on unmount or when auth changes
    return () => {
      clearInterval(checkAndReopenStream)
      if (combinedEventSource) combinedEventSource.close()
    }
  }, [isAuthenticated, user?.id, loading]) // Also depend on loading to delay until dashboard loads

  const fetchDashboardData = async () => {
    // Use AbortController to cancel requests if component unmounts
    const abortController = new AbortController()
    
    try {
      // Use Promise.allSettled to handle partial failures gracefully
      // This prevents one slow request from blocking others
      const results = await Promise.allSettled([
        api.get('/api/bookmarks?per_page=5', { 
          signal: abortController.signal,
          timeout: 15000 // 15 seconds - should be fast with caching
        }),
        api.get('/api/projects', { 
          signal: abortController.signal,
          timeout: 15000
        }),
        api.get('/api/bookmarks/dashboard/stats', { 
          signal: abortController.signal,
          timeout: 15000
        })
      ])
      
      // Handle each result independently
      const [bookmarksResult, projectsResult, statsResult] = results
      
      // Process bookmarks
      if (bookmarksResult.status === 'fulfilled') {
        const bookmarksRes = bookmarksResult.value
        setRecentBookmarks(bookmarksRes.data.bookmarks || [])
        setStats(prev => ({
          ...prev,
          bookmarks: bookmarksRes.data.total || 0
        }))
      } else {
        console.error('Failed to fetch bookmarks:', bookmarksResult.reason)
        handleError(bookmarksResult.reason, 'bookmarks')
      }
      
      // Process projects
      if (projectsResult.status === 'fulfilled') {
        const projectsRes = projectsResult.value
        setRecentProjects(projectsRes.data.projects?.slice(0, 3) || [])
        setStats(prev => ({
          ...prev,
          projects: projectsRes.data.projects?.length || 0
        }))
      } else {
        console.error('Failed to fetch projects:', projectsResult.reason)
        handleError(projectsResult.reason, 'projects')
      }
      
      // Process stats
      if (statsResult.status === 'fulfilled') {
        const statsRes = statsResult.value
        if (statsRes.data) {
          setDashboardStats({
            total_bookmarks: statsRes.data.total_bookmarks || { value: 0, change: '0%', change_value: 0 },
            active_projects: statsRes.data.active_projects || { value: 0, change: '0', change_value: 0 },
            weekly_saves: statsRes.data.weekly_saves || { value: 0, change: '0%', change_value: 0 },
            success_rate: statsRes.data.success_rate || { value: 0, change: '0%', change_value: 0 }
          })
        }
      } else {
        console.error('Failed to fetch stats:', statsResult.reason)
        handleError(statsResult.reason, 'dashboard stats')
      }
      
      // Set loading to false after processing all results (even if some failed)
      setLoading(false)

      // NOTE: Recommendations are now loaded only on the Recommendations page
      // to avoid unnecessary API calls and rate limiting
      // Users can navigate to /recommendations to see personalized suggestions
    } catch (error) {
      // Handle main data loading error with user notification
      handleError(error, 'dashboard data')
      setLoading(false)
    }
  }


  // Removed checkImportProgress and checkAnalysisProgress - now using SSE

  const handleCreateProject = () => {
    navigate('/projects')
  }

  const handleSaveContent = () => {
    navigate('/save-content')
  }

  const handleInstallExtension = () => {
    window.location.href = '/extension/download'
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen text-white relative overflow-hidden" style={{ backgroundColor: '#0F0F1E' }}>
        {/* Animated Background */}
        <div className="fixed inset-0 opacity-10">
          <div 
            className="absolute w-96 h-96 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(77, 208, 225, 0.3) 0%, transparent 70%)',
              left: mousePos.x - 192,
              top: mousePos.y - 192,
              transition: 'all 0.3s ease-out'
            }}
          />
        </div>

        {/* Lightning Grid Background */}
        <div className="fixed inset-0 opacity-5">
          <div className="grid grid-cols-24 grid-rows-24 h-full w-full">
            {Array.from({ length: 576 }).map((_, i) => (
              <div
                key={i}
                className="border border-cyan-500/10 animate-pulse"
                style={{
                  animationDelay: `${Math.random() * 5}s`,
                  animationDuration: `${4 + Math.random() * 3}s`
                }}
              />
            ))}
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-center min-h-screen p-8">
          <div className="max-w-4xl mx-auto text-center">
            <div className="mb-8">
              <div className="flex items-center justify-center space-x-3 mb-4">
                <div className="relative">
                  <Zap className={`${isMobile ? 'w-8 h-8' : 'w-12 h-12'} text-cyan-400`} />
                  <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                </div>
                <span className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold bg-gradient-to-r from-cyan-400 via-teal-400 to-emerald-400 bg-clip-text text-transparent`}>
                  Fuze
                </span>
              </div>
              <div className={`text-cyan-300 font-medium tracking-wider uppercase opacity-80 ${isMobile ? 'mb-3 text-sm' : 'mb-4'}`}>
                Strike Through the Chaos
              </div>
              <p className="text-xl text-gray-300 mb-8">
                Your intelligent bookmark manager with semantic search and Chrome extension integration.
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 hover:border-cyan-500/30 transition-all duration-300 group">
                <div className="p-3 bg-gradient-to-r from-cyan-600/20 via-teal-600/20 to-emerald-600/20 rounded-xl group-hover:scale-110 transition-transform duration-300 mb-4">
                  <Bookmark className="w-8 h-8 text-cyan-400 mx-auto" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">Smart Bookmarks</h3>
                <p className="text-gray-400">Save and organize web content with intelligent categorization</p>
              </div>
              <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 hover:border-cyan-500/30 transition-all duration-300 group">
                <div className="p-3 bg-gradient-to-r from-green-600/20 to-emerald-600/20 rounded-xl group-hover:scale-110 transition-transform duration-300 mb-4">
                  <FolderOpen className="w-8 h-8 text-green-400 mx-auto" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">Project Organization</h3>
                <p className="text-gray-400">Group bookmarks by projects and tasks for better workflow</p>
              </div>
              <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 hover:border-cyan-500/30 transition-all duration-300 group">
                <div className="p-3 bg-gradient-to-r from-orange-600/20 to-red-600/20 rounded-xl group-hover:scale-110 transition-transform duration-300 mb-4">
                  <ExternalLink className="w-8 h-8 text-orange-400 mx-auto" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">Chrome Extension</h3>
                <p className="text-gray-400">One-click bookmarking from any webpage with auto-sync</p>
              </div>
              <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 hover:border-cyan-500/30 transition-all duration-300 group">
                <div className="p-3 bg-gradient-to-r from-cyan-600/20 to-emerald-600/20 rounded-xl group-hover:scale-110 transition-transform duration-300 mb-4">
                  <Sparkles className="w-8 h-8 text-cyan-400 mx-auto" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">AI Recommendations</h3>
                <p className="text-gray-400">Get intelligent content suggestions based on your interests</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen text-white relative overflow-hidden flex items-center justify-center" style={{ backgroundColor: '#0F0F1E' }}>
        {/* Animated Background */}
        <div className="fixed inset-0 opacity-10">
          <div 
            className="absolute w-96 h-96 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(77, 208, 225, 0.3) 0%, transparent 70%)',
              left: mousePos.x - 192,
              top: mousePos.y - 192,
              transition: 'all 0.3s ease-out'
            }}
          />
        </div>

        <div className="text-center relative z-10">
          <div className="relative mb-4">
            <Grid3X3 className={`${isMobile ? 'w-8 h-8' : 'w-12 h-12'} text-cyan-400 mx-auto animate-spin`} />
            <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
          </div>
          <p className="text-xl text-gray-300">Loading your dashboard...</p>
        </div>
      </div>
    )
  }

  const dashboardStatsArray = [
    { 
      label: 'Total Bookmarks', 
      value: dashboardStats.total_bookmarks.value.toString(), 
      change: dashboardStats.total_bookmarks.change, 
      changeValue: dashboardStats.total_bookmarks.change_value,
      icon: Bookmark 
    },
    { 
      label: 'Active Projects', 
      value: dashboardStats.active_projects.value.toString(), 
      change: dashboardStats.active_projects.change, 
      changeValue: dashboardStats.active_projects.change_value,
      icon: FolderOpen 
    },
    { 
      label: 'Weekly Saves', 
      value: dashboardStats.weekly_saves.value.toString(), 
      change: dashboardStats.weekly_saves.change, 
      changeValue: dashboardStats.weekly_saves.change_value,
      icon: TrendingUp 
    },
    { 
      label: 'Success Rate', 
      value: `${Math.round(dashboardStats.success_rate.value)}%`, 
      change: dashboardStats.success_rate.change, 
      changeValue: dashboardStats.success_rate.change_value,
      icon: BarChart3 
    }
  ]

  return (
    <div className="min-h-screen text-white relative overflow-hidden" style={{ backgroundColor: '#0F0F1E' }}>
      {/* Animated Background */}
      <div className="fixed inset-0 opacity-10" style={{ backgroundColor: '#0F0F1E' }}>
        <div 
          className="absolute w-96 h-96 rounded-full"
          style={{
            background: 'radial-gradient(circle, rgba(77, 208, 225, 0.3) 0%, transparent 70%)',
            left: mousePos.x - 192,
            top: mousePos.y - 192,
            transition: 'all 0.3s ease-out'
          }}
        />
      </div>
        
      {/* Lightning Grid Background */}
      <div className="fixed inset-0 opacity-5" style={{ backgroundColor: '#0F0F1E' }}>
        <div className="grid grid-cols-24 grid-rows-24 h-full w-full">
          {Array.from({ length: 576 }).map((_, i) => (
            <div
              key={i}
              className="border border-cyan-500/10 animate-pulse"
              style={{
                animationDelay: `${Math.random() * 5}s`,
                animationDuration: `${4 + Math.random() * 3}s`
              }}
            />
          ))}
        </div>
      </div>

      <div className="relative z-10" style={{ backgroundColor: '#0F0F1E', minHeight: '100vh' }}>
        {/* Main Content */}
        <div className="w-full" style={{ backgroundColor: '#0F0F1E' }}>
          {/* Dashboard Content */}
          <main className={`${isMobile ? 'p-4' : 'p-4 md:p-6 lg:p-8'} max-w-[1600px] mx-auto`} style={{ backgroundColor: '#0F0F1E' }}>
            {/* Header with Logo and Logout */}
            <div className={`flex items-center justify-between ${isMobile ? 'mb-4 pt-2' : 'mb-6 pt-4'} ${isSmallMobile ? 'flex-col gap-4' : ''} ${isMobile ? 'mt-12' : ''}`}>
              {/* Logo - Top Left (Home Link) */}
              <Link
                to="/"
                className="logo-container"
                style={{ 
                  cursor: 'pointer',
                  marginLeft: isMobile ? '0' : '0'
                }}
              >
                <img 
                  src={logo1}
                  alt="FUZE Logo"
                  style={{
                    backgroundColor: 'transparent',
                    mixBlendMode: 'normal'
                  }}
                />
              </Link>

              {/* Logout Button - Top Right */}
              <button
                onClick={handleLogout}
                className="flex items-center gap-2.5 px-5 py-3 rounded-xl transition-all duration-300 group"
                style={{
                  background: 'rgba(20, 20, 20, 0.6)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  backdropFilter: 'blur(10px)',
                  color: '#9ca3af'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.5)'
                  e.currentTarget.style.background = 'rgba(30, 20, 20, 0.8)'
                  e.currentTarget.style.color = '#ef4444'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 4px 16px rgba(239, 68, 68, 0.3)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.2)'
                  e.currentTarget.style.background = 'rgba(20, 20, 20, 0.6)'
                  e.currentTarget.style.color = '#9ca3af'
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <LogOut className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-300" />
                {!isSmallMobile && <span className="text-base font-medium">Logout</span>}
              </button>
            </div>
            {/* Onboarding Banner */}
            <OnboardingBanner />
            
            {/* Welcome Section */}
            <div className={`${isMobile ? 'mt-0 mb-6 p-4' : 'mt-0 mb-8 p-6 md:p-8'} bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl rounded-2xl border border-gray-800 shadow-2xl`}>
              <div className={`flex ${isSmallMobile ? 'flex-col gap-3' : 'items-center gap-4'} mb-4`}>
                <div className="relative flex-shrink-0">
                  <Zap className={`${isMobile ? 'w-6 h-6' : 'w-8 h-8'} text-cyan-400`} />
                  <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                </div>
                <div className="flex-1 min-w-0">
                  <h1 className={`${isSmallMobile ? 'text-2xl' : isMobile ? 'text-3xl' : 'text-3xl md:text-4xl'} font-bold break-words`} style={{ 
                    wordBreak: 'break-word', 
                    overflowWrap: 'anywhere',
                    background: 'linear-gradient(to right, #4DD0E1, #14B8A6, #10B981)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                    width: '100%',
                    maxWidth: '100%',
                    display: 'block',
                    lineHeight: '1.2'
                  }}>
                    Welcome back, {cleanDisplayName}!
                  </h1>
                </div>
              </div>
              <p className={`text-gray-300 ${isMobile ? 'text-base' : 'text-lg md:text-xl'} break-words`} style={{ wordBreak: 'break-word', overflowWrap: 'anywhere', lineHeight: '1.6' }}>Here's what's happening with your bookmarks and projects.</p>
            </div>

            {/* Stats Cards */}
            <div className={`grid grid-cols-1 ${isMobile ? 'sm:grid-cols-2' : 'sm:grid-cols-2 lg:grid-cols-4'} ${isMobile ? 'gap-3' : 'gap-4 md:gap-6'} ${isMobile ? 'mb-6' : 'mb-8'}`}>
              {dashboardStatsArray.map((stat, index) => (
                <div key={index} className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 hover:border-cyan-500/30 transition-all duration-300 group">
                  <div className="flex items-center justify-between mb-4">
                    <div className="p-3 bg-gradient-to-r from-cyan-600/20 via-teal-600/20 to-emerald-600/20 rounded-xl group-hover:scale-110 transition-transform duration-300">
                      <stat.icon className="w-6 h-6 text-cyan-400" />
                    </div>
                    <div className={`text-sm font-medium ${
                      stat.changeValue > 0 ? 'text-green-400' : 
                      stat.changeValue < 0 ? 'text-red-400' : 
                      'text-gray-400'
                    }`}>
                      {stat.change}
                    </div>
                  </div>
                  <div className="text-2xl font-bold text-white mb-1">{stat.value}</div>
                  <div className="text-gray-400 text-sm">{stat.label}</div>
                </div>
              ))}
            </div>

            {/* Import Progress Indicator */}
            {importProgress && importProgress.status !== 'no_import' && (
              <div className="bg-gradient-to-r from-cyan-600/10 via-teal-600/10 to-emerald-600/10 border border-cyan-500/20 rounded-xl p-4 mb-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-cyan-600/20 rounded-lg flex items-center justify-center">
                      <Bookmark className="w-4 h-4 text-cyan-400" />
                    </div>
                    <div>
                      <h4 className="text-white font-semibold">
                        {importProgress.status === 'processing' ? 'Importing Bookmarks' : 'Import Completed'}
                      </h4>
                      <p className="text-gray-400 text-sm">
                        {importProgress.processed} of {importProgress.total} bookmarks processed
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-white font-bold text-lg">
                      {Math.round((importProgress.processed / importProgress.total) * 100)}%
                    </div>
                    {importProgress.status === 'completed' && (
                      <div className="text-green-400 text-sm">
                        ✓ {importProgress.added} added, {importProgress.skipped} skipped
                      </div>
                    )}
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
                  <div
                    className="bg-gradient-to-r from-cyan-500 via-teal-500 to-emerald-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${(importProgress.processed / importProgress.total) * 100}%` }}
                  ></div>
                </div>

                <div className="flex justify-between text-xs text-gray-400">
                  <span>Added: {importProgress.added}</span>
                  <span>Skipped: {importProgress.skipped}</span>
                  <span>Errors: {importProgress.errors}</span>
                </div>
              </div>
            )}

            {/* Analysis Progress Indicator */}
            {analysisProgress && (analysisProgress.status === 'analyzing' || analysisProgress.pending_items > 0) && (
              <div className="bg-gradient-to-r from-cyan-600/10 to-emerald-600/10 border border-cyan-500/20 rounded-xl p-4 mb-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-cyan-600/20 rounded-lg flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-cyan-400" />
                    </div>
                    <div>
                      <h4 className="text-white font-semibold">
                        {analysisProgress.status === 'analyzing' ? 'Analyzing Content' : 'Content Analysis'}
                      </h4>
                      <p className="text-gray-400 text-sm">
                        {analysisProgress.status === 'analyzing'
                          ? `Analyzing: ${analysisProgress.current_item || 'Content'}`
                          : analysisProgress.pending_items > 0
                            ? `${analysisProgress.pending_items} items waiting for analysis`
                            : 'All content analyzed'
                        }
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    {analysisProgress.status === 'analyzing' && (
                      <>
                        <div className="text-white font-bold text-lg">
                          {Math.round((analysisProgress.processed / analysisProgress.total) * 100)}%
                        </div>
                        <div className="text-green-400 text-sm">
                          {analysisProgress.processed}/{analysisProgress.total} processed
                        </div>
                      </>
                    )}
                    {analysisProgress.status === 'idle' && analysisProgress.pending_items > 0 && (
                      <div className="text-yellow-400 text-sm">
                        {analysisProgress.pending_items} pending
                      </div>
                    )}
                  </div>
                </div>

                {analysisProgress.status === 'analyzing' && (
                  <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
                    <div
                      className="bg-gradient-to-r from-cyan-500 to-emerald-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${(analysisProgress.processed / analysisProgress.total) * 100}%` }}
                    ></div>
                  </div>
                )}

                <div className="text-xs text-gray-400">
                  {analysisProgress.status === 'analyzing'
                    ? 'AI is analyzing your bookmarks to provide better recommendations. This may take a few minutes.'
                    : analysisProgress.pending_items > 0
                      ? 'Your bookmarks are being analyzed in the background. Recommendations will improve as analysis completes.'
                      : 'All your content has been analyzed for optimal recommendations.'
                  }
                </div>
              </div>
            )}

            {/* Action Bar */}
            <div className={`flex flex-col ${isMobile ? 'gap-3' : 'md:flex-row items-stretch md:items-center justify-between gap-4'} ${isMobile ? 'mb-6' : 'mb-8'}`}>
              <div className={`flex ${isSmallMobile ? 'flex-col' : 'flex-col sm:flex-row'} items-stretch sm:items-center gap-3 flex-1`}>
                <button 
                  onClick={handleSaveContent}
                  className="px-4 md:px-6 py-3 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 flex items-center justify-center space-x-2 group relative overflow-hidden whitespace-nowrap"
                  style={{
                    background: 'rgba(20, 20, 20, 0.6)',
                    border: '1px solid rgba(77, 208, 225, 0.2)',
                    backdropFilter: 'blur(10px)',
                    color: '#9ca3af'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(77, 208, 225, 0.5)'
                    e.currentTarget.style.background = 'rgba(20, 20, 20, 0.8)'
                    e.currentTarget.style.color = '#4DD0E1'
                    e.currentTarget.style.transform = 'translateY(-2px)'
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(77, 208, 225, 0.3)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(77, 208, 225, 0.2)'
                    e.currentTarget.style.background = 'rgba(20, 20, 20, 0.6)'
                    e.currentTarget.style.color = '#9ca3af'
                    e.currentTarget.style.transform = 'translateY(0)'
                    e.currentTarget.style.boxShadow = 'none'
                  }}
                >
                  <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
                  <span>Save New Content</span>
                </button>
                
                <button 
                  onClick={handleCreateProject}
                  className="px-4 md:px-6 py-3 border border-gray-700 rounded-xl hover:border-green-500/50 hover:bg-green-500/10 transition-all duration-300 transform hover:scale-105 flex items-center justify-center space-x-2 group relative overflow-hidden whitespace-nowrap"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-green-500/10 to-emerald-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                  <FolderOpen className="w-5 h-5 group-hover:text-green-400 transition-colors duration-300 relative z-10" />
                  <span className="group-hover:text-green-400 transition-colors duration-300 relative z-10">Create Project</span>
                </button>
                
                <button 
                  onClick={handleInstallExtension}
                  className="px-4 md:px-6 py-3 border border-gray-700 rounded-xl hover:border-orange-500/50 hover:bg-orange-500/10 transition-all duration-300 transform hover:scale-105 flex items-center justify-center space-x-2 group relative overflow-hidden whitespace-nowrap"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-orange-500/10 to-red-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                  <ExternalLink className="w-5 h-5 group-hover:text-orange-400 group-hover:rotate-12 transition-all duration-300 relative z-10" />
                  <span className="group-hover:text-orange-400 transition-colors duration-300 relative z-10">Install Extension</span>
                </button>
              </div>
                
              <div className="flex items-center justify-center sm:justify-start">
                <div className="flex items-center space-x-2 bg-gray-800/50 rounded-xl p-1">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-2 rounded-lg transition-all duration-300 ${viewMode === 'grid' ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-500/25' : 'text-gray-400 hover:text-white hover:bg-gray-700/50'}`}
                  >
                    <Grid3X3 className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-2 rounded-lg transition-all duration-300 ${viewMode === 'list' ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-500/25' : 'text-gray-400 hover:text-white hover:bg-gray-700/50'}`}
                  >
                    <List className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 md:gap-8">
              {/* Main Content */}
              <div className="lg:col-span-2 space-y-6 md:space-y-8">
                {/* AI Recommendations Teaser */}
                <div className="bg-gradient-to-br from-cyan-600/10 to-emerald-600/10 backdrop-blur-xl border border-cyan-500/20 rounded-2xl p-6 hover:border-cyan-500/30 transition-all duration-300">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="p-3 bg-gradient-to-r from-cyan-600/20 to-emerald-600/20 rounded-xl">
                      <Sparkles className="w-6 h-6 text-cyan-400" />
                    </div>
                    <div>
                      <h2 className="text-lg md:text-xl font-semibold text-white">AI-Powered Recommendations</h2>
                      <p className="text-sm text-cyan-400 font-medium">Discover personalized content</p>
                    </div>
                  </div>

                  <p className="text-gray-300 mb-6">
                    Get intelligent content suggestions based on your saved bookmarks and interests.
                    Our AI analyzes your content to recommend the most relevant learning resources.
                  </p>

                  <Link
                    to="/recommendations"
                    className="inline-flex items-center space-x-2 bg-gradient-to-r from-cyan-600 to-emerald-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105"
                  >
                    <Lightbulb className="w-5 h-5" />
                    <span>Explore Recommendations</span>
                    <ExternalLink className="w-4 h-4" />
                  </Link>
                </div>

                {/* Recent Projects Section */}
                <div>
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-6">
                    <div className="flex items-center space-x-3">
                      <FolderOpen className="w-5 h-5 md:w-6 md:h-6 text-green-400" />
                      <h2 className="text-lg md:text-xl font-semibold text-white">Recent Projects</h2>
                    </div>
                    <Link to="/projects" className="text-sm md:text-base text-cyan-400 hover:text-cyan-300 transition-colors duration-300 flex items-center space-x-2 whitespace-nowrap">
                      <span>View All</span>
                      <ExternalLink className="w-4 h-4" />
                    </Link>
                  </div>
          
                  {recentProjects.length > 0 ? (
                    <div className="grid grid-cols-1 gap-6">
                      {recentProjects.map((project) => (
                        <div key={project.id} className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 hover:border-green-500/30 transition-all duration-300">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <h4 className="text-lg font-semibold text-white mb-2">{project.title}</h4>
                              {project.description && (
                                <p className="text-gray-400 mb-4">{project.description}</p>
                              )}
                              {project.technologies && (
                                <div className="flex flex-wrap gap-2 mb-4">
                                  {project.technologies.split(',').map((tech, index) => (
                                    <span key={index} className="px-2 py-1 bg-green-600/20 text-green-400 text-xs rounded-lg">
                                      {tech.trim()}
                                    </span>
                                  ))}
                                </div>
                              )}
                              <div className="flex items-center space-x-2 text-xs text-gray-500">
                                <Calendar className="w-4 h-4" />
                                <span>Updated {new Date(project.created_at || project.updated_at).toLocaleDateString()}</span>
                              </div>
                            </div>
                            <Link 
                              to={`/projects/${project.id}`}
                              className="p-2 bg-green-600/20 hover:bg-green-600/30 text-green-400 rounded-lg transition-colors duration-300 flex-shrink-0"
                            >
                              <ExternalLink className="w-5 h-5" />
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12 bg-gradient-to-br from-gray-900/30 to-black/30 rounded-2xl border border-gray-800">
                      <div className="p-4 bg-gradient-to-r from-green-600/20 to-emerald-600/20 rounded-full w-16 h-16 mx-auto mb-4">
                        <FolderOpen className="w-8 h-8 text-green-400 mx-auto mt-2" />
                      </div>
                      <h3 className="text-xl font-semibold text-white mb-2">No projects yet</h3>
                      <p className="text-gray-400 mb-6">Create your first project to start organizing your bookmarks and tasks.</p>
                      <button 
                        onClick={handleCreateProject}
                        className="bg-gradient-to-r from-green-600 to-emerald-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-green-500/25 transition-all duration-300 transform hover:scale-105 flex items-center space-x-2 mx-auto"
                      >
                        <Plus className="w-5 h-5" />
                        <span>Create Project</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* Recent Bookmarks Section */}
                <div>
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-6">
                    <div className="flex items-center space-x-3">
                      <Bookmark className="w-5 h-5 md:w-6 md:h-6 text-cyan-400" />
                      <h2 className="text-lg md:text-xl font-semibold text-white">Recent Bookmarks</h2>
                    </div>
                    <Link to="/bookmarks" className="text-sm md:text-base text-cyan-400 hover:text-cyan-300 transition-colors duration-300 flex items-center space-x-2 whitespace-nowrap">
                      <span>View All</span>
                      <ExternalLink className="w-4 h-4" />
                    </Link>
                  </div>
          
                  {recentBookmarks.length > 0 ? (
                    viewMode === 'grid' ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {recentBookmarks.map((bookmark) => (
                          <div key={bookmark.id} className="group bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl overflow-hidden hover:border-cyan-500/30 transition-all duration-300 hover:transform hover:scale-[1.02]">
                            <div className="aspect-video bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center">
                              <Globe className="w-12 h-12 text-gray-600" />
                            </div>
                            
                            <div className="p-6">
                              <div className="flex items-start justify-between mb-3">
                                <h3 className="font-semibold text-white group-hover:text-cyan-400 transition-colors duration-300 line-clamp-2 flex-1">
                                  {bookmark.title}
                                </h3>
                                <button className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex-shrink-0 ml-2">
                                  <Star className="w-5 h-5 text-gray-400 hover:text-yellow-500" />
                                </button>
                              </div>
                              
                              <p className="text-cyan-400 text-sm mb-2 break-all">{bookmark.url}</p>
                              {bookmark.description && (
                                <p className="text-gray-400 text-sm mb-4 line-clamp-2">{bookmark.description}</p>
                              )}
                              
                              {bookmark.category && (
                                <div className="flex flex-wrap gap-2 mb-4">
                                  <span className="px-2 py-1 bg-cyan-600/20 text-cyan-400 text-xs rounded-lg">
                                    {bookmark.category}
                                  </span>
                                </div>
                              )}
                              
                              <div className="flex items-center justify-between">
                                <div className="text-xs text-gray-500">
                                  <Clock className="w-3 h-3 inline mr-1" />
                                  Recently saved
                                </div>
                                <a 
                                  href={bookmark.url} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="p-2 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 rounded-lg transition-colors duration-300"
                                >
                                  <ExternalLink className="w-4 h-4" />
                                </a>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {recentBookmarks.map((bookmark) => (
                          <div key={bookmark.id} className="flex items-center gap-4 p-4 bg-gradient-to-r from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-xl hover:border-cyan-500/30 transition-all duration-300">
                            <div className="w-12 h-12 bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg flex items-center justify-center flex-shrink-0">
                              <Globe className="w-6 h-6 text-gray-600" />
                            </div>
                            
                            <div className="flex-1 min-w-0">
                              <h3 className="font-semibold text-white mb-1 truncate">{bookmark.title}</h3>
                              <p className="text-cyan-400 text-sm mb-1 truncate">{bookmark.url}</p>
                              {bookmark.description && (
                                <p className="text-gray-400 text-sm line-clamp-1">{bookmark.description}</p>
                              )}
                              {bookmark.category && (
                                <span className="inline-block px-2 py-1 bg-cyan-600/20 text-cyan-400 text-xs rounded-lg mt-2">
                                  {bookmark.category}
                                </span>
                              )}
                            </div>
                            
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <button>
                                <Star className="w-5 h-5 text-gray-400 hover:text-yellow-500 transition-colors" />
                              </button>
                              <a 
                                href={bookmark.url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                              >
                                <ExternalLink className="w-5 h-5 text-gray-400 hover:text-cyan-400 transition-colors" />
                              </a>
                              <button>
                                <MoreHorizontal className="w-5 h-5 text-gray-400 hover:text-white transition-colors" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )
                  ) : (
                    <div className="text-center py-12 bg-gradient-to-br from-gray-900/30 to-black/30 rounded-2xl border border-gray-800">
                      <div className="p-4 bg-gradient-to-r from-cyan-600/20 via-teal-600/20 to-emerald-600/20 rounded-full w-16 h-16 mx-auto mb-4">
                        <Bookmark className="w-8 h-8 text-cyan-400 mx-auto mt-2" />
                      </div>
                      <h3 className="text-xl font-semibold text-white mb-2">No bookmarks yet</h3>
                      <p className="text-gray-400 mb-6">Start by adding your first bookmark using the Chrome extension or web form.</p>
                      <button 
                        onClick={handleSaveContent}
                        className="bg-gradient-to-r from-cyan-600 via-teal-600 to-emerald-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 flex items-center space-x-2 mx-auto"
                      >
                        <Plus className="w-5 h-5" />
                        <span>Save New Content</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Sidebar Content */}
              <div className="space-y-6 md:space-y-8">
                {/* Quick Stats */}
                <div>
                  <h3 className="text-base md:text-lg font-semibold text-white mb-4">Quick Overview</h3>
                  <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-gray-400 text-sm md:text-base">This Week</span>
                        <span className="text-white font-semibold text-sm md:text-base">{dashboardStats.weekly_saves.value} saves</span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-gray-400 text-sm md:text-base">Most Used Tag</span>
                        <span className="px-2 py-1 bg-cyan-600/20 text-cyan-400 text-xs rounded-lg">
                          {recentBookmarks.length > 0 && recentBookmarks[0].category ? recentBookmarks[0].category : 'General'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-gray-400 text-sm md:text-base">Success Rate</span>
                        <span className="text-green-400 font-semibold text-sm md:text-base">{Math.round(dashboardStats.success_rate.value)}%</span>
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-gray-400 text-sm md:text-base">Active Projects</span>
                        <span className="text-white font-semibold text-sm md:text-base">{stats.projects}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Recent Activity */}
                <div>
                  <h3 className="text-base md:text-lg font-semibold text-white mb-4">Recent Activity</h3>
                  <div className="space-y-4">
                    {recentProjects.length > 0 ? (
                      <div className="flex items-start space-x-3 p-4 bg-gradient-to-r from-gray-900/30 to-black/30 rounded-xl">
                        <div className="w-8 h-8 bg-gradient-to-r from-green-600/20 to-emerald-600/20 rounded-full flex items-center justify-center mt-1 flex-shrink-0">
                          <Plus className="w-4 h-4 text-green-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white">
                            <span className="text-green-400">Created</span> new project
                          </p>
                          <div className="flex items-center justify-between mt-1 gap-2">
                            <span className="text-xs text-gray-500 truncate">{recentProjects[0].title}</span>
                            <span className="text-xs text-gray-500 whitespace-nowrap">Recently</span>
                          </div>
                        </div>
                      </div>
                    ) : recentBookmarks.length > 0 ? (
                      <div className="flex items-start space-x-3 p-4 bg-gradient-to-r from-gray-900/30 to-black/30 rounded-xl">
                        <div className="w-8 h-8 bg-gradient-to-r from-cyan-600/20 via-teal-600/20 to-emerald-600/20 rounded-full flex items-center justify-center mt-1 flex-shrink-0">
                          <Bookmark className="w-4 h-4 text-cyan-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white">
                            <span className="text-cyan-400">Saved</span> new bookmark
                          </p>
                          <div className="flex items-center justify-between mt-1 gap-2">
                            <span className="text-xs text-gray-500 truncate">{recentBookmarks[0].title}</span>
                            <span className="text-xs text-gray-500 whitespace-nowrap">Recently</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="bg-gradient-to-r from-gray-900/30 to-black/30 rounded-xl p-6 border border-gray-800">
                        <div className="text-center">
                          <div className="w-12 h-12 bg-gradient-to-r from-cyan-600/20 via-teal-600/20 to-emerald-600/20 rounded-full flex items-center justify-center mx-auto mb-3">
                            <Sparkles className="w-6 h-6 text-cyan-400" />
                          </div>
                          <h4 className="text-white font-semibold mb-2">No recent activity</h4>
                          <p className="text-gray-400 text-sm mb-4">Start by saving some content to see your activity here!</p>
                          <button 
                            onClick={handleSaveContent}
                            className="bg-gradient-to-r from-cyan-600 via-teal-600 to-emerald-600 px-4 py-2 rounded-lg text-sm font-medium hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300"
                          >
                            Save First Content
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>

      <style jsx>{`
        .logo-container {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
          background: transparent;
          border: none;
          box-shadow: none;
          transition: transform 0.3s ease;
          padding: 0;
          clip-path: circle(50% at 50% 50%);
          -webkit-clip-path: circle(50% at 50% 50%);
          position: relative;
        }
        
        .logo-container:hover {
          transform: scale(1.05) !important;
        }
        
        .logo-container img {
          width: 100%;
          height: 100%;
          object-fit: contain;
          clip-path: circle(50% at 50% 50%);
          -webkit-clip-path: circle(50% at 50% 50%);
          mix-blend-mode: normal;
        }
        
        @media (max-width: 768px) {
          .logo-container {
            width: 90px;
            height: 90px;
            padding: 0;
          }
        }
        
        @media (max-width: 480px) {
          .logo-container {
            width: 70px;
            height: 70px;
            padding: 0;
          }
        }
        
        .line-clamp-1 {
          display: -webkit-box;
          -webkit-line-clamp: 1;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  )
}

export default Dashboard