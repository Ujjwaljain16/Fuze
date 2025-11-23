import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { Link } from 'react-router-dom'
import api, { refreshTokenIfNeeded } from '../services/api'
import logo1 from '../assets/logo1.svg'
import { 
  Sparkles, Lightbulb, ExternalLink, Bookmark, ThumbsUp, ThumbsDown, 
  RefreshCw, CheckCircle, Brain, Zap, Star, Globe, Clock, X, 
  FolderOpen, Target as TargetIcon, Settings, Code, BookOpen, CheckSquare, LogOut
} from 'lucide-react'
import './recommendations-styles.css'
import './gemini-recommendations-styles.css'
import SmartContextSelector from '../components/SmartContextSelector'
import Loader from '../components/Loader'

const Recommendations = () => {
  const { isAuthenticated, user, logout } = useAuth()
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [geminiAvailable, setGeminiAvailable] = useState(false)
  const [showContextSelector, setShowContextSelector] = useState(false)
  const [selectedContext, setSelectedContext] = useState(null)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [error, setError] = useState(null)
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)
  const [isSmallMobile, setIsSmallMobile] = useState(window.innerWidth <= 480)

  // Mouse tracking for animated background
  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY })
    }
    
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768)
      setIsSmallMobile(window.innerWidth <= 480)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Initial load - only check Gemini status, don't fetch recommendations
  useEffect(() => {
    if (isAuthenticated && user) {
      checkGeminiStatus()
      setLoading(false) // Set loading to false since we're not fetching
    }
  }, [isAuthenticated, user])

  // Periodic token refresh
  useEffect(() => {
    if (!isAuthenticated || !user) return
    
    const tokenRefreshInterval = setInterval(() => {
      refreshTokenIfNeeded()
    }, 5 * 60 * 1000) // Refresh every 5 minutes
    
    return () => clearInterval(tokenRefreshInterval)
  }, [isAuthenticated, user])

  const checkGeminiStatus = async () => {
    try {
      const response = await api.get('/api/recommendations/status')
      // Make Gemini available if unified orchestrator is available
      setGeminiAvailable(response.data.unified_orchestrator_available || false)
    } catch (error) {
      console.error('Error checking unified orchestrator status:', error)
      setGeminiAvailable(false)
    }
  }

  const fetchRecommendations = async () => {
    if (!isAuthenticated || !selectedContext) return
    
    setLoading(true)
    setError(null)
    
    try {
      await refreshTokenIfNeeded()
      
      // Default to unified orchestrator endpoint, but can be changed for task/subtask
      let endpoint = '/api/recommendations/unified-orchestrator'
      
      // Build request payload based on selected context
      let data = {}
      
      if (selectedContext.type === 'general') {
        data = {
          title: 'General Learning',
          description: 'I want to learn and improve my skills',
          technologies: '',
          max_recommendations: 10,
          engine_preference: 'auto',
          diversity_weight: 0.3,
          quality_threshold: 6,
          include_global_content: true,
          enhance_with_gemini: geminiAvailable
        }
      } else if (selectedContext.type === 'surprise') {
        data = {
          title: 'Surprise Me',
          description: 'Random quality learning content',
          technologies: '',
          max_recommendations: 10,
          engine_preference: 'auto',
          diversity_weight: 0.5,
          quality_threshold: 7,
          include_global_content: true,
          enhance_with_gemini: geminiAvailable
        }
      } else if (selectedContext.type === 'project') {
        data = {
          title: selectedContext.title,
          description: selectedContext.description || '',
          technologies: selectedContext.technologies || '',
          project_id: selectedContext.id,
          max_recommendations: 10,
          engine_preference: 'auto',
          diversity_weight: 0.3,
          quality_threshold: 6,
          include_global_content: true,
          enhance_with_gemini: geminiAvailable
        }
      } else if (selectedContext.type === 'task') {
        // Use unified orchestrator with task context for better recommendations
        data = {
          title: selectedContext.title,
          description: selectedContext.description || '',
          technologies: selectedContext.technologies || '',
          project_id: selectedContext.project_id,
          task_id: selectedContext.id,
          max_recommendations: 10,
          engine_preference: 'auto',
          diversity_weight: 0.3,
          quality_threshold: 6,
          include_global_content: true,
          enhance_with_gemini: geminiAvailable
        }
      } else if (selectedContext.type === 'subtask') {
        // Use unified orchestrator with subtask context for better recommendations
        data = {
          title: selectedContext.title,
          description: selectedContext.description || '',
          technologies: selectedContext.technologies || '',
          project_id: selectedContext.project_id,
          task_id: selectedContext.task_id,
          subtask_id: selectedContext.id,
          max_recommendations: 10,
          engine_preference: 'auto',
          diversity_weight: 0.3,
          quality_threshold: 6,
          include_global_content: true,
          enhance_with_gemini: geminiAvailable
        }
      }
      
      const response = await api.post(endpoint, data)
      
      if (response.data.recommendations) {
        setRecommendations(response.data.recommendations)
      } else {
        setRecommendations([])
      }
    } catch (error) {
      console.error('Error fetching recommendations:', error)
      setRecommendations([])
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    if (!selectedContext) {
      setError('Please select a context first')
      return
    }
    setRefreshing(true)
    await fetchRecommendations()
    setRefreshing(false)
  }

  const handleContextSelect = async (context) => {
    setSelectedContext(context)
    setShowContextSelector(false)
    // Fetch recommendations will be triggered by the context change
    await fetchRecommendations()
  }

  const handleFeedback = async (recommendationId, feedbackType) => {
    try {
      // Map feedback type to backend expected format
      const feedbackTypeMap = {
        'positive': 'positive',
        'negative': 'negative'
      }
      
      await api.post('/api/recommendations/feedback', {
        recommendation_id: recommendationId,
        feedback_type: feedbackTypeMap[feedbackType] || feedbackType,
        feedback_data: {
          timestamp: new Date().toISOString(),
          source: 'recommendations_page'
        }
      })
    } catch (error) {
      console.error('Error submitting feedback:', error)
    }
  }

  // Removed handleSaveRecommendation - recommendations are already from saved bookmarks

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
          <div className="max-w-2xl mx-auto text-center">
            <div className="mb-8">
              <div className={`flex items-center justify-center ${isSmallMobile ? 'gap-2' : 'space-x-3'} ${isMobile ? 'mb-3' : 'mb-4'}`}>
                <div className="relative">
                  <Sparkles className={`${isMobile ? 'w-8 h-8' : 'w-12 h-12'} text-cyan-400`} />
                  <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                </div>
                <span className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold bg-gradient-to-r from-cyan-400 via-teal-400 to-emerald-400 bg-clip-text text-transparent`}>
                  AI Recommendations
                </span>
              </div>
              <p className={`text-gray-300 ${isMobile ? 'mb-6 text-base' : 'mb-8 text-xl'}`}>
                Discover personalized content suggestions powered by AI
              </p>
            </div>
            
            <div className={`bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl ${isMobile ? 'p-6' : 'p-8'}`}>
              <h2 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold text-white ${isMobile ? 'mb-3' : 'mb-4'}`}>Authentication Required</h2>
              <p className={`text-gray-300 ${isMobile ? 'mb-4 text-sm' : 'mb-6'}`}>Please log in to view your personalized recommendations.</p>
              <button className={`bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105`}>
                Sign In
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      {error && <div className="error" style={{ color: 'red', marginBottom: '1em' }}>{error}</div>}
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

        <div className="relative z-10">
          <div className="w-full">
            <main className={`${isMobile ? 'p-4' : 'p-4 md:p-6 lg:p-8'} max-w-[1600px] mx-auto`} style={{ backgroundColor: '#0F0F1E' }}>
              {/* Header with Logo and Logout */}
              <div className={`flex items-center justify-between ${isMobile ? 'mb-6 pt-2' : 'mb-8 pt-6'} ${isSmallMobile ? 'flex-col gap-4' : ''} ${isMobile ? 'mt-12' : ''}`}>
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
                  onClick={() => {
                    logout()
                    window.location.href = '/login'
                  }}
                  className={`flex items-center gap-2.5 ${isMobile ? 'px-4 py-2' : 'px-5 py-3'} rounded-xl transition-all duration-300 group`}
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
                  <LogOut className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} group-hover:translate-x-1 transition-transform duration-300`} />
                  {!isSmallMobile && <span className={`${isMobile ? 'text-sm' : 'text-base'} font-medium`}>Logout</span>}
                </button>
              </div>
              
              {/* Header Section */}
              <div className={`${isMobile ? 'mt-0 mb-6 p-4' : 'mt-0 mb-8 p-6 md:p-8'} bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl rounded-2xl border border-gray-800 shadow-2xl`}>
                <div className={`flex ${isSmallMobile ? 'flex-col gap-3' : 'items-center justify-between'} min-w-0`}>
                  <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-4'} flex-1 min-w-0`}>
                    <div className="relative flex-shrink-0">
                      <Sparkles className={`${isMobile ? 'w-6 h-6' : 'w-8 h-8'} text-cyan-400`} />
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
                        color: '#4DD0E1',
                        width: '100%',
                        maxWidth: '100%',
                        display: 'block'
                      }}>
                        AI Recommendations
                      </h1>
                      <p className={`text-gray-300 ${isMobile ? 'text-base mt-1' : 'text-lg md:text-xl mt-2'} break-words`} style={{ wordBreak: 'break-word', overflowWrap: 'anywhere', width: '100%' }}>Discover content tailored to your interests and projects</p>
                    </div>
                  </div>
                  <button 
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className={`bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} ${isSmallMobile ? 'w-full' : ''} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center ${isSmallMobile ? 'justify-center' : 'space-x-2'}`}
                  >
                    <RefreshCw size={isMobile ? 14 : 16} className={refreshing ? 'animate-spin' : ''} />
                    <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
                  </button>
                </div>
              </div>

              {/* Smart Context Selector Button */}
              <div className={`${isMobile ? 'mb-6' : 'mb-8'}`}>
                <button
                  onClick={() => setShowContextSelector(true)}
                  className={`w-full ${isMobile ? 'px-4 py-3 text-base' : 'px-6 py-4 text-lg'} bg-gradient-to-r from-cyan-600 to-teal-600 rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/50 transition-all duration-300 transform hover:scale-[1.02] flex items-center justify-center ${isSmallMobile ? 'gap-2' : 'gap-3'}`}
                >
                  <TargetIcon className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'}`} />
                  {selectedContext ? 
                    (isSmallMobile ? `Change: ${selectedContext.title.length > 20 ? selectedContext.title.substring(0, 20) + '...' : selectedContext.title}` : `Change Context: ${selectedContext.title}`) : 
                    (isSmallMobile ? 'Select Context' : 'Select Context for Recommendations')
                  }
                </button>
                
                {/* Selected Context Display */}
                {selectedContext && (
                  <div className={`${isMobile ? 'mt-3 p-3' : 'mt-4 p-4'} flex items-center justify-between bg-gradient-to-r from-cyan-600/20 to-teal-600/20 rounded-xl border border-cyan-500/30`}>
                    <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'gap-3'} flex-1 min-w-0`}>
                      {selectedContext.type === 'project' ? (
                        <FolderOpen className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400 flex-shrink-0`} />
                      ) : selectedContext.type === 'task' ? (
                        <CheckSquare className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-teal-400 flex-shrink-0`} />
                      ) : selectedContext.type === 'subtask' ? (
                        <CheckSquare className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400 flex-shrink-0`} />
                      ) : selectedContext.type === 'general' ? (
                        <Globe className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400 flex-shrink-0`} />
                      ) : (
                        <Sparkles className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-yellow-400 flex-shrink-0`} />
                      )}
                      <div className="flex-1 min-w-0">
                        <span className={`text-white font-medium block ${isMobile ? 'text-sm' : ''} truncate`}>
                          {selectedContext.title}
                        </span>
                        {selectedContext.technologies && (
                          <span className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'} truncate block`}>
                            {selectedContext.technologies}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => setSelectedContext(null)}
                      className={`${isMobile ? 'p-1.5' : 'p-2'} hover:bg-white/10 rounded-lg transition-colors flex-shrink-0`}
                    >
                      <X className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} text-gray-400`} />
                    </button>
                  </div>
                )}
              </div>

              {/* Engine Selection - Hidden since only one engine */}

              {/* Gemini Status Badge */}
              <div className={`${isMobile ? 'mb-6' : 'mb-8'} flex ${isSmallMobile ? 'justify-center' : 'justify-end'}`}>
                <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-3'} bg-gradient-to-r from-yellow-600/20 to-orange-600/20 rounded-xl ${isMobile ? 'px-3 py-2' : 'px-4 py-3'} border border-yellow-500/30`}>
                  <Brain className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-yellow-400`} />
                  <span className={`text-white font-medium ${isMobile ? 'text-xs' : 'text-sm'}`}>Engine:</span>
                  <div className={`${isMobile ? 'w-1.5 h-1.5' : 'w-2 h-2'} rounded-full ${geminiAvailable ? 'bg-teal-400 animate-pulse' : 'bg-red-400'}`} />
                  <span className={`${isMobile ? 'text-xs' : 'text-sm'} ${geminiAvailable ? 'text-teal-300' : 'text-red-300'}`}>
                    {geminiAvailable ? 'Ready' : 'Unavailable'}
                  </span>
                </div>
              </div>

              {/* Loading State */}
              {loading ? (
                <div className={`text-center ${isMobile ? 'py-12' : 'py-20'}`}>
                  <div className="relative mb-6">
                    <Sparkles className={`${isMobile ? 'w-8 h-8' : 'w-12 h-12'} text-cyan-400 mx-auto animate-spin`} />
                    <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                  </div>
                  <p className={`text-gray-300 ${isMobile ? 'text-base' : 'text-xl'}`}>Finding the best content for you...</p>
                </div>
              ) : !selectedContext ? (
                /* No Context Selected State */
                <div className={`text-center ${isMobile ? 'py-12' : 'py-20'} bg-gradient-to-br from-gray-900/30 to-black/30 rounded-2xl border border-gray-800`}>
                  <div className="relative mb-6">
                    <TargetIcon className={`${isMobile ? 'w-12 h-12' : 'w-16 h-16'} text-cyan-400 mx-auto`} />
                    <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                  </div>
                  <h3 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold text-white ${isMobile ? 'mb-3' : 'mb-4'}`}>Select a Context</h3>
                  <p className={`text-gray-400 ${isMobile ? 'mb-6 text-sm' : 'mb-8'} max-w-md mx-auto`}>
                    Choose a context above to get personalized recommendations tailored to your needs.
                  </p>
                  <button 
                    onClick={() => setShowContextSelector(true)} 
                    className={`bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 flex items-center ${isSmallMobile ? 'justify-center w-full' : 'space-x-2'} mx-auto`}
                  >
                    <TargetIcon className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                    <span>Select Context</span>
                  </button>
                </div>
              ) : recommendations.length > 0 ? (
                /* Recommendations Grid */
                <div className={`grid grid-cols-1 ${isMobile ? 'gap-4' : 'gap-6'}`}>
                  {recommendations.map((rec) => (
                    <RecommendationCard 
                      key={rec.id} 
                      recommendation={rec} 
                      onFeedback={handleFeedback}
                      selectedContext={selectedContext}
                      isMobile={isMobile}
                      isSmallMobile={isSmallMobile}
                    />
                  ))}
                </div>
              ) : (
                /* Empty State */
                <div className={`text-center ${isMobile ? 'py-12' : 'py-20'} bg-gradient-to-br from-gray-900/30 to-black/30 rounded-2xl border border-gray-800`}>
                  <div className="relative mb-6">
                    <Sparkles className={`${isMobile ? 'w-12 h-12' : 'w-16 h-16'} text-cyan-400 mx-auto`} />
                    <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                  </div>
                  <h3 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold text-white ${isMobile ? 'mb-3' : 'mb-4'}`}>No recommendations found</h3>
                  <p className={`text-gray-400 ${isMobile ? 'mb-6 text-sm' : 'mb-8'} max-w-md mx-auto`}>
                    We couldn't find recommendations for this context. Try refreshing or selecting a different context.
                  </p>
                  <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-3' : 'justify-center space-x-4'}`}>
                    <button 
                      onClick={handleRefresh} 
                      className={`bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} ${isSmallMobile ? 'w-full' : ''} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 flex items-center ${isSmallMobile ? 'justify-center' : 'space-x-2'}`}
                    >
                      <RefreshCw className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                      <span>{isSmallMobile ? 'Refresh' : 'Refresh Recommendations'}</span>
                    </button>
                    <button 
                      onClick={() => setShowContextSelector(true)} 
                      className={`bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} ${isSmallMobile ? 'w-full' : ''} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 flex items-center ${isSmallMobile ? 'justify-center' : 'space-x-2'}`}
                    >
                      <TargetIcon className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                      <span>Change Context</span>
                    </button>
                  </div>
                </div>
              )}
            </main>
          </div>
        </div>
      </div>

      {/* Smart Context Selector Modal */}
      {showContextSelector && (
        <SmartContextSelector
          onSelect={handleContextSelect}
          onClose={() => setShowContextSelector(false)}
        />
      )}

      <style>{`
        .logo-container {
          width: auto;
          height: auto;
          max-width: 200px;
          max-height: 80px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: transparent;
          border: none;
          box-shadow: none;
          transition: transform 0.3s ease;
          padding: 0;
          position: relative;
        }
        
        .logo-container:hover {
          transform: scale(1.05) !important;
        }
        
        .logo-container img {
          width: auto;
          height: auto;
          max-width: 200px;
          max-height: 80px;
          object-fit: contain;
          mix-blend-mode: normal;
        }
        
        @media (max-width: 768px) {
          .logo-container {
            max-width: 150px;
            max-height: 60px;
            padding: 0;
          }
          
          .logo-container img {
            max-width: 150px;
            max-height: 60px;
          }
        }
        
        @media (max-width: 480px) {
          .logo-container {
            max-width: 120px;
            max-height: 50px;
            padding: 0;
          }
          
          .logo-container img {
            max-width: 120px;
            max-height: 50px;
          }
        }
      `}</style>

      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
    </>
  )
}

const RecommendationCard = ({ recommendation, onFeedback, selectedContext, isMobile = false, isSmallMobile = false }) => {
  const { success, error } = useToast()
  const [isExpanded, setIsExpanded] = useState(false)
  const [showContextSummary, setShowContextSummary] = useState(false)
  const [loadingContext, setLoadingContext] = useState(false)
  const [generatedContextSummary, setGeneratedContextSummary] = useState(recommendation.context_summary || null)
  const [contextStatus, setContextStatus] = useState(recommendation.context_summary ? 'done' : 'not_started') // 'not_started', 'doing', 'done'

  // Check recommendation type
  const isSimpleRecommendation = recommendation.analysis && 
    (recommendation.analysis.text_similarity !== undefined || 
     recommendation.analysis.interest_similarity !== undefined)
  
  const isGeminiRecommendation = recommendation.analysis && 
    (recommendation.analysis.gemini_technologies !== undefined || 
     recommendation.analysis.quality_indicators !== undefined)

  const isSmartRecommendation = recommendation.learning_path_fit !== undefined || 
    recommendation.project_applicability !== undefined || 
    recommendation.skill_development !== undefined

  const isEnhancedRecommendation = recommendation.algorithm_used !== undefined || 
    recommendation.confidence !== undefined ||
    (recommendation.analysis && recommendation.analysis.algorithm_used)

  // Check if there's any analysis data to show
  const hasAnalysis = recommendation.analysis && (
    isSimpleRecommendation || 
    isGeminiRecommendation || 
    isSmartRecommendation || 
    isEnhancedRecommendation ||
    recommendation.analysis.technologies
  )

  const handleGenerateContext = async () => {
    if (!selectedContext) {
      error('Please select a context first')
      return
    }

    setLoadingContext(true)
    setContextStatus('doing')
    
    try {
      // Prepare context data for API
      const contextData = {
        title: selectedContext.title || '',
        description: selectedContext.description || '',
        technologies: selectedContext.technologies || '',
        user_interests: '',
        project_id: selectedContext.project_id || null
      }

      // Prepare recommendation data
      const recommendationData = {
        id: recommendation.id,
        title: recommendation.title,
        url: recommendation.url,
        description: recommendation.description || '',
        technologies: recommendation.technologies || [],
        content_type: recommendation.content_type || 'article',
        difficulty: recommendation.difficulty || 'intermediate',
        basic_summary: recommendation.basic_summary || ''
      }

      const response = await api.post('/api/recommendations/generate-context', {
        recommendation_id: recommendation.id,
        recommendation: recommendationData,
        context: contextData
      })

      if (response.data.success && response.data.context_summary) {
        setGeneratedContextSummary(response.data.context_summary)
        setContextStatus('done')
        setShowContextSummary(true)
        success('Personalized context generated successfully!')
      } else {
        throw new Error('Failed to generate context')
      }
    } catch (err) {
      console.error('Error generating personalized context:', err)
      setContextStatus('not_started')
      error(err.response?.data?.error || 'Failed to generate personalized context. Please try again.')
    } finally {
      setLoadingContext(false)
    }
  }

  return (
    <div className={`bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl overflow-hidden hover:border-cyan-500/30 transition-all duration-300 hover:transform hover:scale-[1.01]`}>
      <div className={`${isMobile ? 'p-4' : 'p-6'}`}>
        <div className={`flex items-start justify-between ${isMobile ? 'mb-3' : 'mb-4'} ${isSmallMobile ? 'flex-col gap-3' : ''}`}>
          <div className="flex-1">
            <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-3'} ${isMobile ? 'mb-1.5' : 'mb-2'}`}>
              <div className={`${isMobile ? 'p-1.5' : 'p-2'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 rounded-lg flex-shrink-0`}>
                <Lightbulb className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400`} />
              </div>
              <h3 className={`${isMobile ? 'text-lg' : 'text-xl'} font-semibold text-white group-hover:text-cyan-400 transition-colors duration-300`}>
                {recommendation.title}
              </h3>
            </div>
            <p className={`text-cyan-400 ${isMobile ? 'text-xs mb-2' : 'text-sm mb-3'} break-all`}>{recommendation.url}</p>
            {recommendation.description && (
              <p className="text-gray-400 mb-4">{recommendation.description}</p>
            )}
            {recommendation.reason && (
              <div className={`bg-gray-800/30 rounded-lg ${isMobile ? 'p-2 mb-3' : 'p-3 mb-4'}`}>
                <span className={`text-cyan-400 font-medium ${isMobile ? 'text-xs' : 'text-sm'}`}>Why recommended: </span>
                <span className={`text-gray-300 ${isMobile ? 'text-xs' : 'text-sm'}`}>{recommendation.reason}</span>
              </div>
            )}

            {/* Basic Summary - Always visible */}
            {recommendation.basic_summary && (
              <div className={`bg-gradient-to-r from-cyan-600/10 to-teal-600/10 border border-cyan-500/20 rounded-lg ${isMobile ? 'p-3 mb-3' : 'p-4 mb-4'}`}>
                <div className={`flex items-start ${isSmallMobile ? 'gap-2' : 'space-x-3'}`}>
                  <BookOpen className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400 mt-0.5 flex-shrink-0`} />
                  <div className="flex-1">
                    <span className={`text-cyan-400 font-medium ${isMobile ? 'text-xs' : 'text-sm'} block ${isMobile ? 'mb-0.5' : 'mb-1'}`}>Summary</span>
                    <p className={`text-gray-300 ${isMobile ? 'text-xs' : 'text-sm'} leading-relaxed`}>{recommendation.basic_summary}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Personalized Context Section */}
            <div className={`${isMobile ? 'mb-3' : 'mb-4'}`}>
              {contextStatus === 'not_started' ? (
                <button
                  onClick={handleGenerateContext}
                  disabled={loadingContext || !selectedContext}
                  className={`flex items-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'} text-cyan-400 hover:text-cyan-300 transition-colors duration-200 group disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <div className={`flex items-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 border border-cyan-500/30 rounded-lg ${isMobile ? 'px-2 py-1.5' : 'px-3 py-2'} hover:border-cyan-400/50 transition-all duration-200`}>
                    <Brain className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`} />
                    <span className={`font-medium ${isMobile ? 'text-xs' : 'text-sm'}`}>{isSmallMobile ? 'Generate Context' : 'Generate Personalized Context'}</span>
                  </div>
                </button>
              ) : contextStatus === 'doing' ? (
                <div className={`flex items-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'} bg-gradient-to-r from-yellow-600/20 to-orange-600/20 border border-yellow-500/30 rounded-lg ${isMobile ? 'px-2 py-1.5' : 'px-3 py-2'}`}>
                  <RefreshCw className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} animate-spin text-yellow-400`} />
                  <span className={`font-medium ${isMobile ? 'text-xs' : 'text-sm'} text-yellow-400`}>{isSmallMobile ? 'Generating...' : 'Generating personalized context...'}</span>
                </div>
              ) : contextStatus === 'done' && generatedContextSummary ? (
                <>
                  <button
                    onClick={() => setShowContextSummary(!showContextSummary)}
                    className={`flex items-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'} text-cyan-400 hover:text-cyan-300 transition-colors duration-200 group`}
                  >
                    <div className={`flex items-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'} bg-gradient-to-r from-teal-600/20 to-emerald-600/20 border border-teal-500/30 rounded-lg ${isMobile ? 'px-2 py-1.5' : 'px-3 py-2'} hover:border-teal-400/50 transition-all duration-200`}>
                      <span className={`${isMobile ? 'text-xs' : 'text-sm'} transition-transform duration-200 ${showContextSummary ? 'rotate-90' : ''}`}>
                        ▶
                      </span>
                      <span className={`font-medium ${isMobile ? 'text-xs' : 'text-sm'}`}>
                        {showContextSummary ? 'Hide' : 'Show'} Personalized Context
                      </span>
                      <CheckCircle className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} text-teal-400`} />
                      <span className={`${isMobile ? 'text-xs' : 'text-xs'} text-teal-400`}>Done</span>
                    </div>
                  </button>

                  {showContextSummary && (
                    <div className={`mt-3 bg-gradient-to-r from-cyan-600/10 to-teal-600/10 border border-cyan-500/20 rounded-lg ${isMobile ? 'p-3' : 'p-4'} animate-fadeIn`}>
                      <div className={`flex items-start ${isSmallMobile ? 'gap-2' : 'space-x-3'}`}>
                        <TargetIcon className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400 mt-0.5 flex-shrink-0`} />
                        <div className="flex-1">
                          <span className={`text-cyan-400 font-medium ${isMobile ? 'text-xs' : 'text-sm'} block ${isMobile ? 'mb-0.5' : 'mb-1'}`}>Why This Fits Your Project</span>
                          <p className={`text-gray-300 ${isMobile ? 'text-xs' : 'text-sm'} leading-relaxed`}>{generatedContextSummary}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : null}
            </div>
          </div>
          
          <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-2' : 'space-x-3'} ${isSmallMobile ? '' : 'ml-4'}`}>
            {(recommendation.score || recommendation.match_score) && (
              <div className="flex flex-col items-center">
                <span className={`${isMobile ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'} rounded-full font-semibold ${
                  isEnhancedRecommendation ? 'bg-gradient-to-r from-cyan-600/20 to-teal-600/20 text-cyan-400' :
                  isSmartRecommendation ? 'bg-gradient-to-r from-cyan-600/20 to-teal-600/20 text-cyan-400' :
                  isGeminiRecommendation ? 'bg-cyan-600/20 text-cyan-400' : 
                  'bg-cyan-600/20 text-cyan-400'
                }`}>
                  {Math.round(recommendation.match_score || recommendation.score)}%
                  {isEnhancedRecommendation && <TargetIcon className={`${isMobile ? 'w-2.5 h-2.5' : 'w-3 h-3'} inline ml-1`} />}
                  {isSmartRecommendation && <TargetIcon className={`${isMobile ? 'w-2.5 h-2.5' : 'w-3 h-3'} inline ml-1`} />}
                  {isGeminiRecommendation && <Brain className={`${isMobile ? 'w-2.5 h-2.5' : 'w-3 h-3'} inline ml-1`} />}
                </span>
                {isEnhancedRecommendation && (
                  <span className="text-xs text-gray-500 mt-1">
                    {recommendation.algorithm_used || recommendation.analysis?.algorithm_used || 'Enhanced'}
                  </span>
                )}
                {isSmartRecommendation && (
                  <span className="text-xs text-gray-500 mt-1">
                    Smart Match
                  </span>
                )}
                {isGeminiRecommendation && recommendation.confidence && (
                  <span className="text-xs text-gray-500 mt-1">
                    {Math.round(recommendation.confidence)}% confidence
                  </span>
                )}
              </div>
            )}
            {hasAnalysis && (
              <button 
                onClick={() => setIsExpanded(!isExpanded)}
                className={`${isMobile ? 'p-1.5' : 'p-2'} bg-gray-800/50 hover:bg-gray-700/50 rounded-lg transition-colors duration-300`}
                title={isExpanded ? 'Collapse analysis' : 'Expand analysis'}
              >
                {isExpanded ? '▼' : '▶'}
              </button>
            )}
          </div>
        </div>
      </div>
      
      {isExpanded && recommendation.analysis && (
        <div className={`border-t border-gray-800 bg-gray-900/30 ${isMobile ? 'p-4' : 'p-6'}`}>
          <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-2 items-start' : 'space-x-3'} ${isMobile ? 'mb-4' : 'mb-6'}`}>
            <h4 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold text-white`}>
              {isEnhancedRecommendation ? 'Enhanced AI Analysis' :
               isSmartRecommendation ? 'Smart AI Analysis' :
               isGeminiRecommendation ? 'Gemini AI Analysis' : 
               isSimpleRecommendation ? 'Similarity Analysis' : 'AI Analysis'}
            </h4>
            {isEnhancedRecommendation && (
              <div className={`flex items-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 ${isMobile ? 'px-2 py-0.5' : 'px-3 py-1'} rounded-full`}>
                <TargetIcon className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} text-cyan-400`} />
                <span className={`text-cyan-400 ${isMobile ? 'text-xs' : 'text-sm'} font-medium`}>Phase 1+2</span>
              </div>
            )}
            {isSmartRecommendation && (
              <div className={`flex items-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 ${isMobile ? 'px-2 py-0.5' : 'px-3 py-1'} rounded-full`}>
                <TargetIcon className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} text-cyan-400`} />
                <span className={`text-cyan-400 ${isMobile ? 'text-xs' : 'text-sm'} font-medium`}>Smart Enhanced</span>
              </div>
            )}
            {isGeminiRecommendation && !isSmartRecommendation && !isEnhancedRecommendation && (
              <div className={`flex items-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 ${isMobile ? 'px-2 py-0.5' : 'px-3 py-1'} rounded-full`}>
                <Star className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} text-cyan-400`} />
                <span className={`text-cyan-400 ${isMobile ? 'text-xs' : 'text-sm'} font-medium`}>Gemini Enhanced</span>
              </div>
            )}
          </div>
          
          <div className={`grid grid-cols-1 ${isMobile ? 'gap-4' : 'md:grid-cols-2 gap-6'} ${isMobile ? 'mb-4' : 'mb-6'}`}>
            {isSimpleRecommendation ? (
              // Simple recommendation analysis
              <>
                {recommendation.analysis.text_similarity !== undefined && (
                  <MetricBar 
                    label="Text Similarity" 
                    value={recommendation.analysis.text_similarity} 
                    color="from-cyan-500 to-teal-500"
                    textColor="text-cyan-400"
                    isMobile={isMobile}
                  />
                )}
                {recommendation.analysis.tech_overlap !== undefined && (
                  <MetricBar 
                    label="Technology Overlap" 
                    value={recommendation.analysis.tech_overlap} 
                    color="from-teal-500 to-emerald-500"
                    textColor="text-teal-400"
                    isMobile={isMobile}
                  />
                )}
                {recommendation.analysis.interest_similarity !== undefined && (
                  <MetricBar 
                    label="Interest Similarity" 
                    value={recommendation.analysis.interest_similarity} 
                    color="from-orange-500 to-red-500"
                    textColor="text-orange-400"
                    isMobile={isMobile}
                  />
                )}
                {recommendation.analysis.diversity_score !== undefined && (
                  <MetricBar 
                    label="Diversity Score" 
                    value={recommendation.analysis.diversity_score} 
                    color="from-cyan-500 to-teal-500"
                    textColor="text-cyan-400"
                    isMobile={isMobile}
                  />
                )}
              </>
            ) : isSmartRecommendation ? (
              // Smart recommendation analysis
              <>
                {recommendation.learning_path_fit !== undefined && (
                  <MetricBar 
                    label="Learning Path Fit" 
                    value={recommendation.learning_path_fit * 100} 
                    color="from-cyan-500 to-teal-500"
                    textColor="text-cyan-400"
                    isMobile={isMobile}
                  />
                )}
                {recommendation.project_applicability !== undefined && (
                  <MetricBar 
                    label="Project Applicability" 
                    value={recommendation.project_applicability * 100} 
                    color="from-teal-500 to-emerald-500"
                    textColor="text-teal-400"
                    isMobile={isMobile}
                  />
                )}
                {recommendation.skill_development !== undefined && (
                  <MetricBar 
                    label="Skill Development" 
                    value={recommendation.skill_development * 100} 
                    color="from-cyan-500 to-teal-500"
                    textColor="text-cyan-400"
                    isMobile={isMobile}
                  />
                )}
              </>
            ) : isEnhancedRecommendation ? (
              // Enhanced recommendation analysis
              <>
                {recommendation.confidence !== undefined && (
                  <MetricBar 
                    label="Confidence Score" 
                    value={recommendation.confidence} 
                    color="from-cyan-500 to-teal-500"
                    textColor="text-cyan-400"
                    isMobile={isMobile}
                  />
                )}
                {recommendation.quality_score !== undefined && (
                  <MetricBar 
                    label="Quality Score" 
                    value={(recommendation.quality_score / 10) * 100} 
                    color="from-teal-500 to-emerald-500"
                    textColor="text-teal-400"
                    displayValue={`${Math.round(recommendation.quality_score)}/10`}
                    isMobile={isMobile}
                  />
                )}
                {recommendation.diversity_score !== undefined && (
                  <MetricBar 
                    label="Diversity Score" 
                    value={recommendation.diversity_score * 100} 
                    color="from-cyan-500 to-teal-500"
                    textColor="text-cyan-400"
                    isMobile={isMobile}
                  />
                )}
                {recommendation.novelty_score !== undefined && (
                  <MetricBar 
                    label="Novelty Score" 
                    value={recommendation.novelty_score * 100} 
                    color="from-orange-500 to-red-500"
                    textColor="text-orange-400"
                  />
                )}
              </>
            ) : isGeminiRecommendation ? (
              // Gemini-enhanced recommendation analysis
              <>
                {recommendation.analysis.technology_match !== undefined && (
                  <MetricBar 
                    label="Technology Match" 
                    value={recommendation.analysis.technology_match} 
                    color="from-cyan-500 to-teal-500"
                    textColor="text-cyan-400"
                    isMobile={isMobile}
                  />
                )}
                {recommendation.analysis.content_relevance !== undefined && (
                  <MetricBar 
                    label="Content Relevance" 
                    value={recommendation.analysis.content_relevance} 
                    color="from-cyan-500 to-teal-500"
                    textColor="text-cyan-400"
                    isMobile={isMobile}
                  />
                )}
                {recommendation.analysis.semantic_similarity !== undefined && (
                  <MetricBar 
                    label="Semantic Similarity" 
                    value={recommendation.analysis.semantic_similarity} 
                    color="from-teal-500 to-emerald-500"
                    textColor="text-teal-400"
                    isMobile={isMobile}
                  />
                )}
                {recommendation.analysis.quality_indicators && (
                  <MetricBar 
                    label="Content Quality" 
                    value={recommendation.analysis.quality_indicators.completeness || 0} 
                    color="from-yellow-500 to-orange-500"
                    textColor="text-yellow-400"
                    isMobile={isMobile}
                  />
                )}
              </>
            ) : null}
          </div>
          
          {/* Technologies */}
          {recommendation.analysis.technologies && (
            <div className={`bg-gray-800/30 rounded-xl ${isMobile ? 'p-3 mb-3' : 'p-4 mb-4'}`}>
              <h5 className={`text-white font-semibold ${isMobile ? 'mb-2 text-sm' : 'mb-3'} flex items-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'}`}>
                <Settings className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} text-cyan-400`} />
                <span>Technologies</span>
              </h5>
              <div className={`flex flex-wrap ${isMobile ? 'gap-1.5' : 'gap-2'}`}>
                {recommendation.analysis.technologies.length > 0 ? (
                  recommendation.analysis.technologies.map((tech, index) => (
                    <span key={index} className={`${isMobile ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-xs'} bg-cyan-600/20 text-cyan-400 rounded-lg`}>
                      {tech}
                    </span>
                  ))
                ) : (
                  <span className={`text-gray-500 ${isMobile ? 'text-xs' : 'text-sm'}`}>None detected</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Action Buttons */}
      <div className={`border-t border-gray-800 ${isMobile ? 'p-4' : 'p-6'} bg-gray-900/20`}>
        <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-3' : 'justify-between'}`}>
          <a 
            href={recommendation.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className={`flex items-center ${isSmallMobile ? 'justify-center w-full' : 'space-x-2'} ${isMobile ? 'px-3 py-1.5 text-sm' : 'px-4 py-2'} bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white rounded-lg transition-all duration-300 transform hover:scale-105`}
          >
            <ExternalLink className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`} />
            <span>Visit Link</span>
          </a>
          
          <div className={`flex items-center ${isSmallMobile ? 'w-full justify-center gap-3' : 'space-x-2'}`}>
            <button
              onClick={() => onFeedback(recommendation.id, 'positive')}
              className={`${isMobile ? 'p-1.5' : 'p-2'} bg-gray-800/50 hover:bg-green-600/20 text-gray-400 hover:text-green-400 border border-gray-700 hover:border-green-500/50 rounded-lg transition-all duration-300`}
              title="Like this recommendation"
            >
              <ThumbsUp className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`} />
            </button>
            <button
              onClick={() => onFeedback(recommendation.id, 'negative')}
              className={`${isMobile ? 'p-1.5' : 'p-2'} bg-gray-800/50 hover:bg-red-600/20 text-gray-400 hover:text-red-400 border border-gray-700 hover:border-red-500/50 rounded-lg transition-all duration-300`}
              title="Dislike this recommendation"
            >
              <ThumbsDown className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Helper component for metric bars
const MetricBar = ({ label, value, color, textColor, displayValue, isMobile = false }) => (
  <div className={`bg-gray-800/30 rounded-xl ${isMobile ? 'p-3' : 'p-4'}`}>
    <div className={`flex justify-between items-center ${isMobile ? 'mb-1.5' : 'mb-2'}`}>
      <span className={`text-gray-300 ${isMobile ? 'text-xs' : 'text-sm'}`}>{label}</span>
      <span className={`${textColor} font-semibold ${isMobile ? 'text-xs' : 'text-sm'}`}>
        {displayValue || `${Math.round(value)}%`}
      </span>
    </div>
    <div className={`w-full ${isMobile ? 'h-1.5' : 'h-2'} bg-gray-700 rounded-full overflow-hidden`}>
      <div 
        className={`h-full bg-gradient-to-r ${color} transition-all duration-300`}
        style={{width: `${value}%`}}
      />
    </div>
  </div>
)

export default Recommendations
