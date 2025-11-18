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
  const [selectedEngine, setSelectedEngine] = useState('unified')
  const [error, setError] = useState(null)
  
  // Engine configurations - only unified engine
  const engines = [
    {
      id: 'unified',
      name: 'Swift Match',
      description: 'Fast & Reliable',
      color: 'from-blue-500 via-cyan-500 to-blue-600',
      hoverColor: 'from-blue-400 via-cyan-400 to-blue-500',
      glowColor: 'shadow-blue-500/50',
      icon: Zap
    }
  ]

  // Mouse tracking for animated background
  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY })
    }
    
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
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
          <div className="max-w-2xl mx-auto text-center">
            <div className="mb-8">
              <div className="flex items-center justify-center space-x-3 mb-4">
                <div className="relative">
                  <Sparkles className="w-12 h-12 text-purple-400" />
                  <div className="absolute inset-0 blur-lg bg-purple-400 opacity-50 animate-pulse" />
                </div>
                <span className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
                  AI Recommendations
                </span>
              </div>
              <p className="text-xl text-gray-300 mb-8">
                Discover personalized content suggestions powered by AI
              </p>
            </div>
            
            <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-8">
              <h2 className="text-2xl font-bold text-white mb-4">Authentication Required</h2>
              <p className="text-gray-300 mb-6">Please log in to view your personalized recommendations.</p>
              <button className="bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-purple-500/25 transition-all duration-300 transform hover:scale-105">
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
          <div className="w-full">
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
                  onClick={() => {
                    logout()
                    window.location.href = '/login'
                  }}
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
              
              {/* Header Section */}
              <div className="mt-8 mb-8 bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl rounded-2xl p-8 border border-gray-800 shadow-2xl overflow-visible">
                <div className="flex items-center justify-between min-w-0">
                  <div className="flex items-center space-x-4 flex-1 min-w-0">
                    <div className="relative flex-shrink-0">
                      <Sparkles className="w-8 h-8 text-purple-400" />
                      <div className="absolute inset-0 blur-lg bg-purple-400 opacity-50 animate-pulse" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h1 className="text-4xl font-bold break-words" style={{ 
                        wordBreak: 'break-word', 
                        overflowWrap: 'anywhere',
                        background: 'linear-gradient(to right, #a855f7, #ec4899)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text',
                        color: '#a855f7',
                        width: '100%',
                        maxWidth: '100%',
                        display: 'block'
                      }}>
                        AI Recommendations
                      </h1>
                      <p className="text-gray-300 text-xl mt-2 break-words" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere', width: '100%' }}>Discover content tailored to your interests and projects</p>
                    </div>
                  </div>
                  <button 
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-purple-500/25 transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
                    <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
                  </button>
                </div>
              </div>

              {/* Smart Context Selector Button */}
              <div className="mb-8">
                <button
                  onClick={() => setShowContextSelector(true)}
                  className="w-full px-6 py-4 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl font-semibold text-lg hover:shadow-lg hover:shadow-purple-500/50 transition-all duration-300 transform hover:scale-[1.02] flex items-center justify-center gap-3"
                >
                  <TargetIcon className="w-6 h-6" />
                  {selectedContext ? 
                    `Change Context: ${selectedContext.title}` : 
                    'Select Context for Recommendations'
                  }
                </button>
                
                {/* Selected Context Display */}
                {selectedContext && (
                  <div className="mt-4 flex items-center justify-between p-4 bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-xl border border-purple-500/30">
                    <div className="flex items-center gap-3">
                      {selectedContext.type === 'project' ? (
                        <FolderOpen className="w-5 h-5 text-purple-400" />
                      ) : selectedContext.type === 'task' ? (
                        <CheckSquare className="w-5 h-5 text-green-400" />
                      ) : selectedContext.type === 'subtask' ? (
                        <CheckSquare className="w-5 h-5 text-purple-400" />
                      ) : selectedContext.type === 'general' ? (
                        <Globe className="w-5 h-5 text-blue-400" />
                      ) : (
                        <Sparkles className="w-5 h-5 text-yellow-400" />
                      )}
                      <div>
                        <span className="text-white font-medium block">
                          {selectedContext.title}
                        </span>
                        {selectedContext.technologies && (
                          <span className="text-gray-400 text-sm">
                            {selectedContext.technologies}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => setSelectedContext(null)}
                      className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4 text-gray-400" />
                    </button>
                  </div>
                )}
              </div>

              {/* Engine Selection - Hidden since only one engine */}

              {/* Gemini Status Badge */}
              <div className="mb-8 flex justify-end">
                <div className="flex items-center space-x-3 bg-gradient-to-r from-yellow-600/20 to-orange-600/20 rounded-xl px-4 py-3 border border-yellow-500/30">
                  <Brain className="w-5 h-5 text-yellow-400" />
                  <span className="text-white font-medium">Engine:</span>
                  <div className={`w-2 h-2 rounded-full ${geminiAvailable ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
                  <span className={`text-sm ${geminiAvailable ? 'text-green-300' : 'text-red-300'}`}>
                    {geminiAvailable ? 'Ready' : 'Unavailable'}
                  </span>
                </div>
              </div>

              {/* Loading State */}
              {loading ? (
                <div className="text-center py-20">
                  <div className="relative mb-6">
                    <Sparkles className="w-12 h-12 text-purple-400 mx-auto animate-spin" />
                    <div className="absolute inset-0 blur-lg bg-purple-400 opacity-50 animate-pulse" />
                  </div>
                  <p className="text-xl text-gray-300">Finding the best content for you...</p>
                </div>
              ) : !selectedContext ? (
                /* No Context Selected State */
                <div className="text-center py-20 bg-gradient-to-br from-gray-900/30 to-black/30 rounded-2xl border border-gray-800">
                  <div className="relative mb-6">
                    <TargetIcon className="w-16 h-16 text-purple-400 mx-auto" />
                    <div className="absolute inset-0 blur-lg bg-purple-400 opacity-50 animate-pulse" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-4">Select a Context</h3>
                  <p className="text-gray-400 mb-8 max-w-md mx-auto">
                    Choose a context above to get personalized recommendations tailored to your needs.
                  </p>
                  <button 
                    onClick={() => setShowContextSelector(true)} 
                    className="bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-purple-500/25 transition-all duration-300 transform hover:scale-105 flex items-center space-x-2 mx-auto"
                  >
                    <TargetIcon className="w-5 h-5" />
                    <span>Select Context</span>
                  </button>
                </div>
              ) : recommendations.length > 0 ? (
                /* Recommendations Grid */
                <div className="grid grid-cols-1 gap-6">
                  {recommendations.map((rec) => (
                    <RecommendationCard 
                      key={rec.id} 
                      recommendation={rec} 
                      onFeedback={handleFeedback}
                    />
                  ))}
                </div>
              ) : (
                /* Empty State */
                <div className="text-center py-20 bg-gradient-to-br from-gray-900/30 to-black/30 rounded-2xl border border-gray-800">
                  <div className="relative mb-6">
                    <Sparkles className="w-16 h-16 text-purple-400 mx-auto" />
                    <div className="absolute inset-0 blur-lg bg-purple-400 opacity-50 animate-pulse" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-4">No recommendations found</h3>
                  <p className="text-gray-400 mb-8 max-w-md mx-auto">
                    We couldn't find recommendations for this context. Try refreshing or selecting a different context.
                  </p>
                  <div className="flex items-center justify-center space-x-4">
                    <button 
                      onClick={handleRefresh} 
                      className="bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-purple-500/25 transition-all duration-300 transform hover:scale-105 flex items-center space-x-2"
                    >
                      <RefreshCw className="w-5 h-5" />
                      <span>Refresh Recommendations</span>
                    </button>
                    <button 
                      onClick={() => setShowContextSelector(true)} 
                      className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-blue-500/25 transition-all duration-300 transform hover:scale-105 flex items-center space-x-2"
                    >
                      <TargetIcon className="w-5 h-5" />
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
      `}</style>
    </>
  )
}

const RecommendationCard = ({ recommendation, onFeedback }) => {
  const [isExpanded, setIsExpanded] = useState(false)

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

  return (
    <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl overflow-hidden hover:border-purple-500/30 transition-all duration-300 hover:transform hover:scale-[1.01]">
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              <div className="p-2 bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-lg">
                <Lightbulb className="w-5 h-5 text-purple-400" />
              </div>
              <h3 className="text-xl font-semibold text-white group-hover:text-purple-400 transition-colors duration-300">
                {recommendation.title}
              </h3>
            </div>
            <p className="text-blue-400 text-sm mb-3 break-all">{recommendation.url}</p>
            {recommendation.description && (
              <p className="text-gray-400 mb-4">{recommendation.description}</p>
            )}
            {recommendation.reason && (
              <div className="bg-gray-800/30 rounded-lg p-3 mb-4">
                <span className="text-purple-400 font-medium">Why recommended: </span>
                <span className="text-gray-300">{recommendation.reason}</span>
              </div>
            )}
          </div>
          
          <div className="flex items-center space-x-3 ml-4">
            {(recommendation.score || recommendation.match_score) && (
              <div className="flex flex-col items-center">
                <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                  isEnhancedRecommendation ? 'bg-gradient-to-r from-purple-600/20 to-pink-600/20 text-purple-400' :
                  isSmartRecommendation ? 'bg-gradient-to-r from-purple-600/20 to-pink-600/20 text-purple-400' :
                  isGeminiRecommendation ? 'bg-purple-600/20 text-purple-400' : 
                  'bg-blue-600/20 text-blue-400'
                }`}>
                  {Math.round(recommendation.match_score || recommendation.score)}%
                  {isEnhancedRecommendation && <TargetIcon className="w-3 h-3 inline ml-1" />}
                  {isSmartRecommendation && <TargetIcon className="w-3 h-3 inline ml-1" />}
                  {isGeminiRecommendation && <Brain className="w-3 h-3 inline ml-1" />}
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
                className="p-2 bg-gray-800/50 hover:bg-gray-700/50 rounded-lg transition-colors duration-300"
                title={isExpanded ? 'Collapse analysis' : 'Expand analysis'}
              >
                {isExpanded ? '▼' : '▶'}
              </button>
            )}
          </div>
        </div>
      </div>
      
      {isExpanded && recommendation.analysis && (
        <div className="border-t border-gray-800 bg-gray-900/30 p-6">
          <div className="flex items-center space-x-3 mb-6">
            <h4 className="text-lg font-semibold text-white">
              {isEnhancedRecommendation ? 'Enhanced AI Analysis' :
               isSmartRecommendation ? 'Smart AI Analysis' :
               isGeminiRecommendation ? 'Gemini AI Analysis' : 
               isSimpleRecommendation ? 'Similarity Analysis' : 'AI Analysis'}
            </h4>
            {isEnhancedRecommendation && (
              <div className="flex items-center space-x-2 bg-gradient-to-r from-purple-600/20 to-pink-600/20 px-3 py-1 rounded-full">
                <TargetIcon className="w-4 h-4 text-purple-400" />
                <span className="text-purple-400 text-sm font-medium">Phase 1+2</span>
              </div>
            )}
            {isSmartRecommendation && (
              <div className="flex items-center space-x-2 bg-gradient-to-r from-purple-600/20 to-pink-600/20 px-3 py-1 rounded-full">
                <TargetIcon className="w-4 h-4 text-purple-400" />
                <span className="text-purple-400 text-sm font-medium">Smart Enhanced</span>
              </div>
            )}
            {isGeminiRecommendation && !isSmartRecommendation && !isEnhancedRecommendation && (
              <div className="flex items-center space-x-2 bg-gradient-to-r from-purple-600/20 to-pink-600/20 px-3 py-1 rounded-full">
                <Star className="w-4 h-4 text-purple-400" />
                <span className="text-purple-400 text-sm font-medium">Gemini Enhanced</span>
              </div>
            )}
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {isSimpleRecommendation ? (
              // Simple recommendation analysis
              <>
                {recommendation.analysis.text_similarity !== undefined && (
                  <MetricBar 
                    label="Text Similarity" 
                    value={recommendation.analysis.text_similarity} 
                    color="from-blue-500 to-purple-500"
                    textColor="text-blue-400"
                  />
                )}
                {recommendation.analysis.tech_overlap !== undefined && (
                  <MetricBar 
                    label="Technology Overlap" 
                    value={recommendation.analysis.tech_overlap} 
                    color="from-green-500 to-emerald-500"
                    textColor="text-green-400"
                  />
                )}
                {recommendation.analysis.interest_similarity !== undefined && (
                  <MetricBar 
                    label="Interest Similarity" 
                    value={recommendation.analysis.interest_similarity} 
                    color="from-orange-500 to-red-500"
                    textColor="text-orange-400"
                  />
                )}
                {recommendation.analysis.diversity_score !== undefined && (
                  <MetricBar 
                    label="Diversity Score" 
                    value={recommendation.analysis.diversity_score} 
                    color="from-pink-500 to-purple-500"
                    textColor="text-pink-400"
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
                    color="from-purple-500 to-pink-500"
                    textColor="text-purple-400"
                  />
                )}
                {recommendation.project_applicability !== undefined && (
                  <MetricBar 
                    label="Project Applicability" 
                    value={recommendation.project_applicability * 100} 
                    color="from-green-500 to-emerald-500"
                    textColor="text-green-400"
                  />
                )}
                {recommendation.skill_development !== undefined && (
                  <MetricBar 
                    label="Skill Development" 
                    value={recommendation.skill_development * 100} 
                    color="from-blue-500 to-cyan-500"
                    textColor="text-blue-400"
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
                    color="from-purple-500 to-pink-500"
                    textColor="text-purple-400"
                  />
                )}
                {recommendation.quality_score !== undefined && (
                  <MetricBar 
                    label="Quality Score" 
                    value={(recommendation.quality_score / 10) * 100} 
                    color="from-green-500 to-emerald-500"
                    textColor="text-green-400"
                    displayValue={`${Math.round(recommendation.quality_score)}/10`}
                  />
                )}
                {recommendation.diversity_score !== undefined && (
                  <MetricBar 
                    label="Diversity Score" 
                    value={recommendation.diversity_score * 100} 
                    color="from-blue-500 to-cyan-500"
                    textColor="text-blue-400"
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
                    color="from-purple-500 to-pink-500"
                    textColor="text-purple-400"
                  />
                )}
                {recommendation.analysis.content_relevance !== undefined && (
                  <MetricBar 
                    label="Content Relevance" 
                    value={recommendation.analysis.content_relevance} 
                    color="from-blue-500 to-cyan-500"
                    textColor="text-blue-400"
                  />
                )}
                {recommendation.analysis.semantic_similarity !== undefined && (
                  <MetricBar 
                    label="Semantic Similarity" 
                    value={recommendation.analysis.semantic_similarity} 
                    color="from-green-500 to-emerald-500"
                    textColor="text-green-400"
                  />
                )}
                {recommendation.analysis.quality_indicators && (
                  <MetricBar 
                    label="Content Quality" 
                    value={recommendation.analysis.quality_indicators.completeness || 0} 
                    color="from-yellow-500 to-orange-500"
                    textColor="text-yellow-400"
                  />
                )}
              </>
            ) : null}
          </div>
          
          {/* Technologies */}
          {recommendation.analysis.technologies && (
            <div className="bg-gray-800/30 rounded-xl p-4 mb-4">
              <h5 className="text-white font-semibold mb-3 flex items-center space-x-2">
                <Settings className="w-4 h-4 text-blue-400" />
                <span>Technologies</span>
              </h5>
              <div className="flex flex-wrap gap-2">
                {recommendation.analysis.technologies.length > 0 ? (
                  recommendation.analysis.technologies.map((tech, index) => (
                    <span key={index} className="px-2 py-1 bg-blue-600/20 text-blue-400 text-xs rounded-lg">
                      {tech}
                    </span>
                  ))
                ) : (
                  <span className="text-gray-500 text-sm">None detected</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Action Buttons */}
      <div className="border-t border-gray-800 p-6 bg-gray-900/20">
        <div className="flex items-center justify-between">
          <a 
            href={recommendation.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white rounded-lg transition-all duration-300 transform hover:scale-105"
          >
            <ExternalLink className="w-4 h-4" />
            <span>Visit Link</span>
          </a>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onFeedback(recommendation.id, 'positive')}
              className="p-2 bg-gray-800/50 hover:bg-green-600/20 text-gray-400 hover:text-green-400 border border-gray-700 hover:border-green-500/50 rounded-lg transition-all duration-300"
              title="Like this recommendation"
            >
              <ThumbsUp className="w-4 h-4" />
            </button>
            <button
              onClick={() => onFeedback(recommendation.id, 'negative')}
              className="p-2 bg-gray-800/50 hover:bg-red-600/20 text-gray-400 hover:text-red-400 border border-gray-700 hover:border-red-500/50 rounded-lg transition-all duration-300"
              title="Dislike this recommendation"
            >
              <ThumbsDown className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Helper component for metric bars
const MetricBar = ({ label, value, color, textColor, displayValue }) => (
  <div className="bg-gray-800/30 rounded-xl p-4">
    <div className="flex justify-between items-center mb-2">
      <span className="text-gray-300">{label}</span>
      <span className={`${textColor} font-semibold`}>
        {displayValue || `${Math.round(value)}%`}
      </span>
    </div>
    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
      <div 
        className={`h-full bg-gradient-to-r ${color} transition-all duration-300`}
        style={{width: `${value}%`}}
      />
    </div>
  </div>
)

export default Recommendations
