import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import api from '../services/api'
import { useErrorHandler } from '../hooks/useErrorHandler'
import { optimizedApiCall } from '../utils/apiOptimization'
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
  
  // Debug user data
  console.log('Dashboard user data:', user)
  console.log('User username:', user?.username)
  console.log('User name:', user?.name)
  
  // Clean username for display
  const displayName = user?.username || user?.name || 'User'
  const cleanDisplayName = displayName.replace(/[^\w\s]/g, '').trim() || 'User'
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
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      fetchDashboardData()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated])

  // Use Server-Sent Events for progress updates instead of polling
  useEffect(() => {
    if (!isAuthenticated || !user?.id) return

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

    // EventSource doesn't support custom headers, so we'll use query param or cookie
    // Since we're using JWT in localStorage, we need to pass it as query param
    // Note: In production, consider using cookies for SSE auth instead
    
    // Import progress SSE
    const importEventSource = new EventSource(
      `${baseURL}/api/bookmarks/import/progress/stream?token=${encodeURIComponent(token)}`,
      { withCredentials: true }
    )

    importEventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.status !== 'no_import') {
          setImportProgress(data)
        } else {
          setImportProgress(null)
        }
      } catch (error) {
        console.error('Error parsing import progress:', error)
      }
    }

    importEventSource.onerror = (error) => {
      console.error('Import progress SSE error:', error)
      // EventSource will automatically reconnect on error
    }

    // Analysis progress SSE
    const analysisEventSource = new EventSource(
      `${baseURL}/api/bookmarks/analysis/progress/stream?token=${encodeURIComponent(token)}`,
      { withCredentials: true }
    )

    analysisEventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setAnalysisProgress(data)
      } catch (error) {
        console.error('Error parsing analysis progress:', error)
      }
    }

    analysisEventSource.onerror = (error) => {
      console.error('Analysis progress SSE error:', error)
      // EventSource will automatically reconnect on error
    }

    // Cleanup on unmount or when auth changes
    return () => {
      importEventSource.close()
      analysisEventSource.close()
    }
  }, [isAuthenticated, user?.id])

  const fetchDashboardData = async () => {
    try {
      // TEMPORARY: Direct API calls to debug timeout issues
      // Removed optimization layer to test if it's causing problems
      const [bookmarksRes, projectsRes, statsRes] = await Promise.all([
        api.get('/api/bookmarks?per_page=5'),
        api.get('/api/projects'),
        api.get('/api/bookmarks/dashboard/stats')
      ])

      setRecentBookmarks(bookmarksRes.data.bookmarks || [])
      setRecentProjects(projectsRes.data.projects?.slice(0, 3) || [])
      setStats({
        bookmarks: bookmarksRes.data.total || 0,
        projects: projectsRes.data.projects?.length || 0
      })

      // Set dashboard stats with real calculated values
      if (statsRes.data) {
        setDashboardStats({
          total_bookmarks: statsRes.data.total_bookmarks || { value: 0, change: '0%', change_value: 0 },
          active_projects: statsRes.data.active_projects || { value: 0, change: '0', change_value: 0 },
          weekly_saves: statsRes.data.weekly_saves || { value: 0, change: '0%', change_value: 0 },
          success_rate: statsRes.data.success_rate || { value: 0, change: '0%', change_value: 0 }
        })
      }

      // Set loading to false after main data is loaded
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
    window.open('https://chrome.google.com/webstore', '_blank')
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-black text-white relative overflow-hidden">
        {/* Animated Background */}
        <div className="fixed inset-0 opacity-10">
          <div 
            className="absolute w-96 h-96 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, transparent 70%)',
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
                className="border border-blue-500/10 animate-pulse"
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
                  <Zap className="w-12 h-12 text-blue-400" />
                  <div className="absolute inset-0 blur-lg bg-blue-400 opacity-50 animate-pulse" />
                </div>
                <span className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                  Fuze
                </span>
              </div>
              <div className="text-blue-300 font-medium tracking-wider uppercase opacity-80 mb-4">
                Strike Through the Chaos
              </div>
              <p className="text-xl text-gray-300 mb-8">
                Your intelligent bookmark manager with semantic search and Chrome extension integration.
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 hover:border-blue-500/30 transition-all duration-300 group">
                <div className="p-3 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl group-hover:scale-110 transition-transform duration-300 mb-4">
                  <Bookmark className="w-8 h-8 text-blue-400 mx-auto" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">Smart Bookmarks</h3>
                <p className="text-gray-400">Save and organize web content with intelligent categorization</p>
              </div>
              <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 hover:border-blue-500/30 transition-all duration-300 group">
                <div className="p-3 bg-gradient-to-r from-green-600/20 to-emerald-600/20 rounded-xl group-hover:scale-110 transition-transform duration-300 mb-4">
                  <FolderOpen className="w-8 h-8 text-green-400 mx-auto" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">Project Organization</h3>
                <p className="text-gray-400">Group bookmarks by projects and tasks for better workflow</p>
              </div>
              <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 hover:border-blue-500/30 transition-all duration-300 group">
                <div className="p-3 bg-gradient-to-r from-orange-600/20 to-red-600/20 rounded-xl group-hover:scale-110 transition-transform duration-300 mb-4">
                  <ExternalLink className="w-8 h-8 text-orange-400 mx-auto" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">Chrome Extension</h3>
                <p className="text-gray-400">One-click bookmarking from any webpage with auto-sync</p>
              </div>
              <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 hover:border-blue-500/30 transition-all duration-300 group">
                <div className="p-3 bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-xl group-hover:scale-110 transition-transform duration-300 mb-4">
                  <Sparkles className="w-8 h-8 text-purple-400 mx-auto" />
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
      <div className="min-h-screen bg-black text-white relative overflow-hidden flex items-center justify-center">
        {/* Animated Background */}
        <div className="fixed inset-0 opacity-10">
          <div 
            className="absolute w-96 h-96 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, transparent 70%)',
              left: mousePos.x - 192,
              top: mousePos.y - 192,
              transition: 'all 0.3s ease-out'
            }}
          />
        </div>

        <div className="text-center relative z-10">
          <div className="relative mb-4">
            <Grid3X3 className="w-12 h-12 text-blue-400 mx-auto animate-spin" />
            <div className="absolute inset-0 blur-lg bg-blue-400 opacity-50 animate-pulse" />
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
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 opacity-10">
        <div 
          className="absolute w-96 h-96 rounded-full"
          style={{
            background: 'radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, transparent 70%)',
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
              className="border border-blue-500/10 animate-pulse"
              style={{
                animationDelay: `${Math.random() * 5}s`,
                animationDuration: `${4 + Math.random() * 3}s`
              }}
            />
          ))}
        </div>
      </div>

      <div className="relative z-10">
        {/* Main Content */}
        <div className="w-full">
          {/* Dashboard Content */}
          <main className="p-4 md:p-6 lg:p-8 max-w-[1600px] mx-auto">
            {/* Header with Logo and Logout */}
            <div className="flex items-center justify-between mb-8 pt-6">
              {/* Logo - Top Left (Home Link) */}
              <Link
                to="/"
                className="logo-container"
                style={{ 
                  cursor: 'pointer'
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
                <span className="text-base font-medium">Logout</span>
              </button>
            </div>
            {/* Onboarding Banner */}
            <OnboardingBanner />
            
            {/* Welcome Section */}
            <div className="mt-8 mb-8 bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl rounded-2xl p-6 md:p-8 border border-gray-800 shadow-2xl overflow-visible">
              <div className="flex items-center space-x-4 mb-4 min-w-0">
                <div className="relative flex-shrink-0">
                  <Zap className="w-8 h-8 text-blue-400" />
                  <div className="absolute inset-0 blur-lg bg-blue-400 opacity-50 animate-pulse" />
                </div>
                <h1 className="text-3xl md:text-4xl font-bold flex-1 min-w-0 break-words" style={{ 
                  wordBreak: 'break-word', 
                  overflowWrap: 'anywhere',
                  background: 'linear-gradient(to right, #60a5fa, #a855f7)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                  color: '#60a5fa',
                  width: '100%',
                  maxWidth: '100%',
                  display: 'block'
                }}>
                  Welcome back, {cleanDisplayName}!
                </h1>
              </div>
              <p className="text-gray-300 text-lg md:text-xl break-words" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>Here's what's happening with your bookmarks and projects.</p>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
              {dashboardStatsArray.map((stat, index) => (
                <div key={index} className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6 hover:border-blue-500/30 transition-all duration-300 group">
                  <div className="flex items-center justify-between mb-4">
                    <div className="p-3 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl group-hover:scale-110 transition-transform duration-300">
                      <stat.icon className="w-6 h-6 text-blue-400" />
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
              <div className="bg-gradient-to-r from-blue-600/10 to-purple-600/10 border border-blue-500/20 rounded-xl p-4 mb-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-600/20 rounded-lg flex items-center justify-center">
                      <Bookmark className="w-4 h-4 text-blue-400" />
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
                    className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
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
              <div className="bg-gradient-to-r from-purple-600/10 to-pink-600/10 border border-purple-500/20 rounded-xl p-4 mb-6">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-purple-600/20 rounded-lg flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-purple-400" />
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
                      className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all duration-300"
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
            <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 mb-8">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 flex-1">
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
                    className={`p-2 rounded-lg transition-all duration-300 ${viewMode === 'grid' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25' : 'text-gray-400 hover:text-white hover:bg-gray-700/50'}`}
                  >
                    <Grid3X3 className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-2 rounded-lg transition-all duration-300 ${viewMode === 'list' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25' : 'text-gray-400 hover:text-white hover:bg-gray-700/50'}`}
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
                <div className="bg-gradient-to-br from-purple-600/10 to-pink-600/10 backdrop-blur-xl border border-purple-500/20 rounded-2xl p-6 hover:border-purple-500/30 transition-all duration-300">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="p-3 bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-xl">
                      <Sparkles className="w-6 h-6 text-purple-400" />
                    </div>
                    <div>
                      <h2 className="text-lg md:text-xl font-semibold text-white">AI-Powered Recommendations</h2>
                      <p className="text-sm text-purple-400 font-medium">Discover personalized content</p>
                    </div>
                  </div>

                  <p className="text-gray-300 mb-6">
                    Get intelligent content suggestions based on your saved bookmarks and interests.
                    Our AI analyzes your content to recommend the most relevant learning resources.
                  </p>

                  <Link
                    to="/recommendations"
                    className="inline-flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-purple-500/25 transition-all duration-300 transform hover:scale-105"
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
                    <Link to="/projects" className="text-sm md:text-base text-blue-400 hover:text-blue-300 transition-colors duration-300 flex items-center space-x-2 whitespace-nowrap">
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
                      <Bookmark className="w-5 h-5 md:w-6 md:h-6 text-blue-400" />
                      <h2 className="text-lg md:text-xl font-semibold text-white">Recent Bookmarks</h2>
                    </div>
                    <Link to="/bookmarks" className="text-sm md:text-base text-blue-400 hover:text-blue-300 transition-colors duration-300 flex items-center space-x-2 whitespace-nowrap">
                      <span>View All</span>
                      <ExternalLink className="w-4 h-4" />
                    </Link>
                  </div>
          
                  {recentBookmarks.length > 0 ? (
                    viewMode === 'grid' ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {recentBookmarks.map((bookmark) => (
                          <div key={bookmark.id} className="group bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl overflow-hidden hover:border-blue-500/30 transition-all duration-300 hover:transform hover:scale-[1.02]">
                            <div className="aspect-video bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center">
                              <Globe className="w-12 h-12 text-gray-600" />
                            </div>
                            
                            <div className="p-6">
                              <div className="flex items-start justify-between mb-3">
                                <h3 className="font-semibold text-white group-hover:text-blue-400 transition-colors duration-300 line-clamp-2 flex-1">
                                  {bookmark.title}
                                </h3>
                                <button className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex-shrink-0 ml-2">
                                  <Star className="w-5 h-5 text-gray-400 hover:text-yellow-500" />
                                </button>
                              </div>
                              
                              <p className="text-blue-400 text-sm mb-2 break-all">{bookmark.url}</p>
                              {bookmark.description && (
                                <p className="text-gray-400 text-sm mb-4 line-clamp-2">{bookmark.description}</p>
                              )}
                              
                              {bookmark.category && (
                                <div className="flex flex-wrap gap-2 mb-4">
                                  <span className="px-2 py-1 bg-blue-600/20 text-blue-400 text-xs rounded-lg">
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
                                  className="p-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded-lg transition-colors duration-300"
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
                          <div key={bookmark.id} className="flex items-center gap-4 p-4 bg-gradient-to-r from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-xl hover:border-blue-500/30 transition-all duration-300">
                            <div className="w-12 h-12 bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg flex items-center justify-center flex-shrink-0">
                              <Globe className="w-6 h-6 text-gray-600" />
                            </div>
                            
                            <div className="flex-1 min-w-0">
                              <h3 className="font-semibold text-white mb-1 truncate">{bookmark.title}</h3>
                              <p className="text-blue-400 text-sm mb-1 truncate">{bookmark.url}</p>
                              {bookmark.description && (
                                <p className="text-gray-400 text-sm line-clamp-1">{bookmark.description}</p>
                              )}
                              {bookmark.category && (
                                <span className="inline-block px-2 py-1 bg-blue-600/20 text-blue-400 text-xs rounded-lg mt-2">
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
                                <ExternalLink className="w-5 h-5 text-gray-400 hover:text-blue-400 transition-colors" />
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
                      <div className="p-4 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-full w-16 h-16 mx-auto mb-4">
                        <Bookmark className="w-8 h-8 text-blue-400 mx-auto mt-2" />
                      </div>
                      <h3 className="text-xl font-semibold text-white mb-2">No bookmarks yet</h3>
                      <p className="text-gray-400 mb-6">Start by adding your first bookmark using the Chrome extension or web form.</p>
                      <button 
                        onClick={handleSaveContent}
                        className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-blue-500/25 transition-all duration-300 transform hover:scale-105 flex items-center space-x-2 mx-auto"
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
                        <span className="px-2 py-1 bg-blue-600/20 text-blue-400 text-xs rounded-lg">
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
                        <div className="w-8 h-8 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-full flex items-center justify-center mt-1 flex-shrink-0">
                          <Bookmark className="w-4 h-4 text-blue-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-white">
                            <span className="text-blue-400">Saved</span> new bookmark
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
                          <div className="w-12 h-12 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-full flex items-center justify-center mx-auto mb-3">
                            <Sparkles className="w-6 h-6 text-blue-400" />
                          </div>
                          <h4 className="text-white font-semibold mb-2">No recent activity</h4>
                          <p className="text-gray-400 text-sm mb-4">Start by saving some content to see your activity here!</p>
                          <button 
                            onClick={handleSaveContent}
                            className="bg-gradient-to-r from-blue-600 to-purple-600 px-4 py-2 rounded-lg text-sm font-medium hover:shadow-lg hover:shadow-blue-500/25 transition-all duration-300"
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