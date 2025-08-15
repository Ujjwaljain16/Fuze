import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import api, { refreshTokenIfNeeded } from '../services/api'
import { 
  Sparkles, Lightbulb, ExternalLink, Bookmark, ThumbsUp, ThumbsDown, 
  Filter, RefreshCw, Target, CheckCircle, Brain, Zap, Star, Plus,
  Globe, Clock, Settings, Search, BookOpen,
  Code, GraduationCap, Briefcase, Users, Target as TargetIcon
} from 'lucide-react'
import './recommendations-styles.css'
import './gemini-recommendations-styles.css'
import Select from 'react-select'

const Recommendations = () => {
  const { isAuthenticated, user } = useAuth()
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [refreshing, setRefreshing] = useState(false)
  const [projects, setProjects] = useState([])
  const [tasks, setTasks] = useState([])
  const [projectsLoading, setProjectsLoading] = useState(false)
  const [emptyMessage, setEmptyMessage] = useState('')
  const [taskAnalysis, setTaskAnalysis] = useState(null)
  const [geminiAvailable, setGeminiAvailable] = useState(false)

  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [filterOptions, setFilterOptions] = useState([
    { value: 'all', label: 'All Recommendations' },
    { value: 'general', label: 'General' }
  ])
  

  
  // Recommendation form
  const [recommendationForm, setRecommendationForm] = useState({
    project_title: '',
    project_description: '',
    technologies: '',
    learning_goals: ''
  })
  const [showRecommendationForm, setShowRecommendationForm] = useState(false)


  const [selectedProject, setSelectedProject] = useState(null)
  
  // Engine selection state
  const [selectedEngine, setSelectedEngine] = useState('unified') // Default to unified
  
  // Engine configurations with better names and icons
  const engines = [
    {
      id: 'unified',
      name: 'Swift Match',
      description: 'Fast & Reliable',
      color: 'from-blue-500 via-cyan-500 to-blue-600',
      hoverColor: 'from-blue-400 via-cyan-400 to-blue-500',
      glowColor: 'shadow-blue-500/50',
      icon: Zap
    },
    {
      id: 'ensemble',
      name: 'Smart Fusion',
      description: 'Balanced Intelligence',
      color: 'from-purple-500 via-pink-500 to-purple-600',
      hoverColor: 'from-purple-400 via-pink-400 to-purple-500',
      glowColor: 'shadow-purple-500/50',
      icon: Brain
    },
    {
      id: 'quality',
      name: 'Bestest Match',
      description: 'Fast Quality',
      color: 'from-emerald-500 via-teal-500 to-emerald-600',
      hoverColor: 'from-emerald-400 via-teal-400 to-emerald-500',
      glowColor: 'shadow-emerald-500/50',
      icon: Star
    }
  ]

  const [error, setError] = useState(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    if (isAuthenticated && user) {
      fetchProjects()
      checkGeminiStatus()
      fetchRecommendations()
    }
  }, [isAuthenticated, user])

  // Separate useEffect for fetching recommendations when filter or engine changes
  useEffect(() => {
    if (isAuthenticated && user && filter && selectedEngine) {
      fetchRecommendations()
    }
  }, [filter, selectedProject, selectedEngine])

  // Periodic token refresh to prevent expiration
  useEffect(() => {
    if (!isAuthenticated || !user) return
    
    const tokenRefreshInterval = setInterval(() => {
      refreshTokenIfNeeded()
    }, 5 * 60 * 1000) // Refresh every 5 minutes
    
    return () => clearInterval(tokenRefreshInterval)
  }, [isAuthenticated, user])

  // Ensure projects are fetched when user becomes available
  useEffect(() => {
    if (isAuthenticated && user && projects.length === 0) {
      console.log('🔍 Fetching projects - User authenticated:', !!user, 'Projects count:', projects.length)
      fetchProjects()
    }
  }, [isAuthenticated, user, projects.length])

  // Debug logging for authentication state
  useEffect(() => {
    console.log('🔐 Auth state changed:', { 
      isAuthenticated, 
      hasUser: !!user, 
      projectsCount: projects.length,
      filterOptionsCount: filterOptions.length 
    })
  }, [isAuthenticated, user, projects.length, filterOptions.length])

  const checkGeminiStatus = async () => {
    try {
      console.log('Checking unified orchestrator status...')
      const response = await api.get('/api/recommendations/status')
      console.log('Status response:', response.data)
      
      // Check if unified orchestrator is available
      if (response.data.unified_orchestrator_available) {
        setGeminiAvailable(response.data.fast_gemini_available || false)
      } else {
        setGeminiAvailable(false)
      }
    } catch (error) {
      console.error('Error checking unified orchestrator status:', error)
      setGeminiAvailable(false)
    }
  }





  const fetchProjects = async () => {
    try {
      setProjectsLoading(true)
      console.log('Fetching projects...')
      const response = await api.get('/api/projects')
      const userProjects = response.data.projects || []
      console.log('Projects loaded:', userProjects)
      setProjects(userProjects)
      
      // Fetch tasks for each project
      const allTasks = []
      for (const project of userProjects) {
        try {
          const tasksResponse = await api.get(`/api/projects/${project.id}/tasks`)
          const projectTasks = tasksResponse.data.tasks || []
          allTasks.push(...projectTasks.map(task => ({
            ...task,
            projectTitle: project.title
          })))
        } catch (error) {
          console.error(`Error fetching tasks for project ${project.id}:`, error)
        }
      }
      console.log('Tasks loaded:', allTasks)
      setTasks(allTasks)
      
      // Update filter options to include projects and tasks
      const projectOptions = userProjects.map(project => ({
        value: `project_${project.id}`,
        label: `Project: ${project.title}`
      }))
      
      const taskOptions = allTasks.map(task => ({
        value: `task_${task.id}`,
        label: `Task: ${task.title} (${task.projectTitle})`
      }))
      
      const newFilterOptions = [
        { value: 'all', label: 'All Recommendations' },
        { value: 'general', label: 'General' }
      ]
      
      // Only add project and task options if they exist
      if (projectOptions.length > 0) {
        newFilterOptions.push(...projectOptions)
      }
      if (taskOptions.length > 0) {
        newFilterOptions.push(...taskOptions)
      }
      
      setFilterOptions(newFilterOptions)
      
      // If no projects exist, show a helpful message
      if (userProjects.length === 0) {
        console.log('No projects found for user')
      }
      
    } catch (error) {
      console.error('Error fetching projects:', error)
      // Set empty arrays and basic filter options on error
      setProjects([])
      setTasks([])
      setFilterOptions([
        { value: 'all', label: 'All Recommendations' },
        { value: 'general', label: 'General' }
      ])
    } finally {
      setProjectsLoading(false)
    }
  }

  const fetchRecommendations = async () => {
    if (!isAuthenticated) return
    
    setLoading(true)
    setError(null)
    
    try {
      // Proactively refresh token if needed before making request
      await refreshTokenIfNeeded()
      
      console.log('Fetching recommendations with engine:', selectedEngine)
      console.log('Filter:', filter)
      console.log('Selected project:', selectedProject)
      
      // Determine endpoint based on selected engine
      let endpoint
      switch (selectedEngine) {
        case 'unified':
          endpoint = '/api/recommendations/unified-orchestrator'
          break
        case 'ensemble':
          endpoint = '/api/recommendations/ensemble'
          break
        case 'quality':
          endpoint = '/api/recommendations/ensemble/quality'
          break
        case 'gemini':
          endpoint = '/api/recommendations/gemini'
          break
        default:
          endpoint = '/api/recommendations/unified-orchestrator'
      }
      
      let data = {
        title: selectedProject ? selectedProject.title : 'Learning Project',
        description: selectedProject ? selectedProject.description : 'I want to learn and improve my skills',
        technologies: selectedProject ? selectedProject.technologies : projects.map(p => p.technologies).filter(tech => tech && tech.trim()).join(', '),
        user_interests: 'Master relevant technologies and improve skills',
        max_recommendations: 10,
        engine_preference: 'auto',
        diversity_weight: 0.3,
        quality_threshold: 6,
        include_global_content: true,
        enhance_with_gemini: geminiAvailable
      }
      
      // Add engine-specific payload
      if (selectedEngine === 'ensemble') {
        data.engines = ['unified']  // Use only reliable unified engine
        data.ensemble_method = 'weighted_voting'
        console.log('Using ensemble with reliable engines:', data.engines)
      }
      
      // Handle project-specific recommendations
      if (filter.startsWith('project_')) {
        const projectId = filter.replace('project_', '')
        data.project_id = parseInt(projectId)
      } else if (filter.startsWith('task_')) {
        const taskId = filter.replace('task_', '')
        endpoint = `/api/recommendations/task/${taskId}`
        data = null
      }
      
      console.log(`Fetching recommendations from: ${endpoint}`)
      console.log('Request data:', data)
      console.log('Active features:', {
        gemini: geminiAvailable,
        engine_preference: data.engine_preference
      })
      
      const response = data ? 
        await api.post(endpoint, data) : 
        await api.get(endpoint)
      
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
    setRefreshing(true)
    await fetchRecommendations()
    setRefreshing(false)
  }

  const handleFeedback = async (recommendationId, feedbackType) => {
    try {
      await api.post('/api/recommendations/feedback', {
        content_id: recommendationId,
        feedback_type: feedbackType
      })
      // Optionally refresh recommendations after feedback
      // fetchRecommendations()
    } catch (error) {
      console.error('Error submitting feedback:', error)
    }
  }

  const handleSaveRecommendation = async (recommendation) => {
    try {
      await api.post('/api/bookmarks', {
        url: recommendation.url,
        title: recommendation.title,
        description: recommendation.description || '',
        category: 'recommended'
      })
      // Remove from recommendations list
      setRecommendations(prev => prev.filter(rec => rec.id !== recommendation.id))
    } catch (error) {
      console.error('Error saving recommendation:', error)
    }
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
          {/* Main Content */}
          <div className="w-full">
            <main className="ml-12 md:ml-16 lg:ml-20 p-4 md:p-6 lg:p-8">
              {/* Header Section */}
              <div className="mt-8 mb-8 bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl rounded-2xl p-8 border border-gray-800 shadow-2xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="relative">
                      <Sparkles className="w-8 h-8 text-purple-400" />
                      <div className="absolute inset-0 blur-lg bg-purple-400 opacity-50 animate-pulse" />
                    </div>
                    <div>
                      <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
                        AI Recommendations
                      </h1>
                      <p className="text-gray-300 text-xl mt-2">Discover content tailored to your interests and projects</p>
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

              {/* Engine Selection */}
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-gray-200 mb-4">Choose Your Engine</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {engines.map((engine) => {
                    const IconComponent = engine.icon
                    const isSelected = selectedEngine === engine.id
                    return (
                      <button
                        key={engine.id}
                        onClick={() => setSelectedEngine(engine.id)}
                        className={`relative p-4 rounded-xl border-2 transition-all duration-300 transform hover:scale-105 ${
                          isSelected
                            ? `border-transparent bg-gradient-to-r ${engine.color} shadow-lg ${engine.glowColor}`
                            : 'border-gray-600 bg-gray-800/50 hover:border-gray-500'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <IconComponent className={`w-6 h-6 ${isSelected ? 'text-white' : 'text-gray-400'}`} />
                          <div className="text-left">
                            <div className={`font-semibold ${isSelected ? 'text-white' : 'text-gray-200'}`}>
                              {engine.name}
                            </div>
                            <div className={`text-sm ${isSelected ? 'text-blue-100' : 'text-gray-400'}`}>
                              {engine.description}
                            </div>
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>



              {/* Filter Controls */}
              <div className="mb-8 bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl rounded-2xl p-8 border border-gray-800">
                <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between space-y-6 xl:space-y-0 xl:space-x-8">
                  {/* Filter Controls */}
                  <div className="flex flex-col sm:flex-row sm:items-center space-y-4 sm:space-y-0 sm:space-x-6">
                    <div className="flex items-center space-x-3">
                      <Filter className="w-5 h-5 text-blue-400" />
                      <span className="text-white font-medium">Filter by:</span>
                    </div>
                    <div className="filter-container" style={{ minWidth: 200, position: 'relative', zIndex: 1000 }}>
                      {projectsLoading ? (
                        <div className="flex items-center space-x-2 px-4 py-3 bg-gray-800/50 rounded-xl border border-gray-700">
                          <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
                          <span className="text-gray-300">Loading projects...</span>
                        </div>
                      ) : (
                        <Select
                          classNamePrefix="react-select"
                          value={filterOptions.find(opt => opt.value === filter)}
                          onChange={option => {
                            console.log('Filter changed to:', option.value)
                            setFilter(option.value)
                            // Update selectedProject when a project is selected
                            if (option.value.startsWith('project_')) {
                              const projectId = option.value.replace('project_', '')
                              const project = projects.find(p => p.id.toString() === projectId)
                              console.log('Selected project:', project)
                              setSelectedProject(project || null)
                            } else {
                              console.log('No project selected')
                              setSelectedProject(null)
                            }
                          }}
                          options={filterOptions}
                          isSearchable={false}
                          styles={{
                            control: (base, state) => ({
                              ...base,
                              background: 'rgba(30,32,48,0.9)',
                              borderColor: state.isFocused ? '#a855f7' : 'rgba(255,255,255,0.1)',
                              color: '#fff',
                              borderRadius: 12,
                              minHeight: 44,
                              boxShadow: state.isFocused ? '0 0 0 3px rgba(168,85,247,0.1)' : 'none',
                              fontWeight: 500,
                              fontSize: 14,
                              cursor: 'pointer',
                            }),
                            singleValue: base => ({ ...base, color: '#fff' }),
                            menu: base => ({ 
                              ...base, 
                              background: '#1f1f23', 
                              color: '#fff', 
                              borderRadius: 12, 
                              zIndex: 9999,
                              border: '1px solid rgba(255,255,255,0.1)',
                              position: 'absolute',
                              top: '100%',
                              left: 0,
                              right: 0,
                              marginTop: '4px'
                            }),
                            option: (base, state) => ({
                              ...base,
                              background: state.isFocused ? 'rgba(168,85,247,0.15)' : 'transparent',
                              color: '#fff',
                              cursor: 'pointer',
                              padding: '12px 16px',
                            }),
                            dropdownIndicator: base => ({ ...base, color: '#a855f7' }),
                            indicatorSeparator: base => ({ ...base, display: 'none' }),
                            input: base => ({ ...base, color: '#fff' }),
                          }}
                        />
                      )}
                    </div>
                    
                    {/* Selected Project Indicator */}
                    {selectedProject && (
                      <div className="flex items-center space-x-2 bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-xl p-3 border border-purple-500/30">
                        <Target className="w-5 h-5 text-purple-400" />
                        <span className="text-white font-medium">Project:</span>
                        <span className="text-purple-300 font-semibold">{selectedProject.title}</span>
                        <span className="text-gray-400 text-sm">({selectedProject.technologies})</span>
                      </div>
                    )}
                    
                    {/* No Projects Message */}
                    {!projectsLoading && projects.length === 0 && (
                      <div className="flex items-center space-x-2 bg-gradient-to-r from-yellow-600/20 to-orange-600/20 rounded-xl p-3 border border-yellow-500/30">
                        <BookOpen className="w-5 h-5 text-yellow-400" />
                        <span className="text-white font-medium">No projects found.</span>
                        <a 
                          href="/projects" 
                          className="text-yellow-300 hover:text-yellow-200 underline"
                        >
                          Create your first project
                        </a>
                      </div>
                    )}
                  </div>
                  
                  {/* Engine Selection */}
                  {/* The Engine Selection block is now moved outside the filter section */}
                  
                  {/* Gemini Status */}
                  <div className="flex items-center space-x-3 bg-gradient-to-r from-yellow-600/20 to-orange-600/20 rounded-xl p-3 border border-yellow-500/30">
                    <Brain className="w-5 h-5 text-yellow-400" />
                    <span className="text-white font-medium">Gemini:</span>
                    <div className={`w-2 h-2 rounded-full ${geminiAvailable ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
                    <span className={`text-sm ${geminiAvailable ? 'text-green-300' : 'text-red-300'}`}>
                      {geminiAvailable ? 'Ready' : 'Unavailable'}
                    </span>
                  </div>
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
              ) : recommendations.length > 0 ? (
                /* Recommendations Grid */
                <div className="grid grid-cols-1 gap-6">
                  {recommendations.map((rec) => (
                    <RecommendationCard 
                      key={rec.id} 
                      recommendation={rec} 
                      isTaskRecommendation={filter.startsWith('task_')}
                      onSave={() => handleSaveRecommendation(rec)}
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
                  <h3 className="text-2xl font-bold text-white mb-4">No recommendations yet</h3>
                  <p className="text-gray-400 mb-8 max-w-md mx-auto">
                    {emptyMessage || (
                      filter === 'all' 
                        ? 'Start by adding some bookmarks and projects to get personalized recommendations.'
                        : 'No recommendations found for this filter. Try refreshing or changing the filter.'
                    )}
                  </p>
                  <div className="flex items-center justify-center space-x-4">
                    <button 
                      onClick={handleRefresh} 
                      className="bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-purple-500/25 transition-all duration-300 transform hover:scale-105 flex items-center space-x-2"
                    >
                      <RefreshCw className="w-5 h-5" />
                      <span>Refresh Recommendations</span>
                    </button>
                    {emptyMessage && emptyMessage.includes('No bookmarks found') && (
                      <a 
                        href="/save-content" 
                        className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-3 rounded-xl font-semibold hover:shadow-lg hover:shadow-blue-500/25 transition-all duration-300 transform hover:scale-105 flex items-center space-x-2"
                      >
                        <Bookmark className="w-5 h-5" />
                        <span>Add Your First Bookmark</span>
                      </a>
                    )}
                  </div>
                </div>
              )}
            </main>
          </div>
        </div>
      </div>
    </>
  )
}

const RecommendationCard = ({ recommendation, isTaskRecommendation, onSave }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Check if this is a simple recommendation (new format)
  const isSimpleRecommendation = recommendation.analysis && 
    (recommendation.analysis.text_similarity !== undefined || 
     recommendation.analysis.interest_similarity !== undefined);
  
  // Check if this is a Gemini-enhanced recommendation
  const isGeminiRecommendation = recommendation.analysis && 
    (recommendation.analysis.gemini_technologies !== undefined || 
     recommendation.analysis.quality_indicators !== undefined);

  // Check if this is a smart recommendation (new enhanced format)
  const isSmartRecommendation = recommendation.learning_path_fit !== undefined || 
    recommendation.project_applicability !== undefined || 
    recommendation.skill_development !== undefined;

  // Check if this is an enhanced recommendation (Phase 1+2 format)
  const isEnhancedRecommendation = recommendation.algorithm_used !== undefined || 
    recommendation.confidence !== undefined ||
    (recommendation.analysis && recommendation.analysis.algorithm_used);

  return (
    <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl overflow-hidden hover:border-purple-500/30 transition-all duration-300 hover:transform hover:scale-[1.01]">
      <div 
        className="p-6 cursor-pointer" 
        onClick={() => setIsExpanded(!isExpanded)}
      >
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
                  isTaskRecommendation ? 'bg-green-600/20 text-green-400' :
                  isGeminiRecommendation ? 'bg-purple-600/20 text-purple-400' : 
                  'bg-blue-600/20 text-blue-400'
                }`}>
                  {Math.round(recommendation.match_score || recommendation.score)}%
                  {isEnhancedRecommendation && <TargetIcon className="w-3 h-3 inline ml-1" />}
                  {isSmartRecommendation && <TargetIcon className="w-3 h-3 inline ml-1" />}
                  {isTaskRecommendation && (recommendation.score || recommendation.match_score) >= 70 && (
                    <CheckCircle className="w-3 h-3 inline ml-1" />
                  )}
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
            <button className="p-2 bg-gray-800/50 hover:bg-gray-700/50 rounded-lg transition-colors duration-300">
              {isExpanded ? '▼' : '▶'}
            </button>
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
               isSimpleRecommendation ? 'Similarity Analysis' : 
               (isTaskRecommendation ? 'Precision Analysis' : 'AI Analysis')}
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
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Text Similarity</span>
                      <span className="text-blue-400 font-semibold">{Math.round(recommendation.analysis.text_similarity)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300"
                        style={{width: `${recommendation.analysis.text_similarity}%`}}
                      />
                    </div>
                  </div>
                )}
                {recommendation.analysis.tech_overlap !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Technology Overlap</span>
                      <span className="text-green-400 font-semibold">{Math.round(recommendation.analysis.tech_overlap)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all duration-300"
                        style={{width: `${recommendation.analysis.tech_overlap}%`}}
                      />
                    </div>
                  </div>
                )}
                {recommendation.analysis.interest_similarity !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Interest Similarity</span>
                      <span className="text-orange-400 font-semibold">{Math.round(recommendation.analysis.interest_similarity)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-orange-500 to-red-500 transition-all duration-300"
                        style={{width: `${recommendation.analysis.interest_similarity}%`}}
                      />
                    </div>
                  </div>
                )}
                {recommendation.analysis.diversity_score !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Diversity Score</span>
                      <span className="text-pink-400 font-semibold">{Math.round(recommendation.analysis.diversity_score)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-pink-500 to-purple-500 transition-all duration-300"
                        style={{width: `${recommendation.analysis.diversity_score}%`}}
                      />
                    </div>
                  </div>
                )}
              </>
            ) : isSmartRecommendation ? (
              // Smart recommendation analysis
              <>
                {recommendation.learning_path_fit !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Learning Path Fit</span>
                      <span className="text-purple-400 font-semibold">{Math.round(recommendation.learning_path_fit * 100)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300"
                        style={{width: `${recommendation.learning_path_fit * 100}%`}}
                      />
                    </div>
                  </div>
                )}
                {recommendation.project_applicability !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Project Applicability</span>
                      <span className="text-green-400 font-semibold">{Math.round(recommendation.project_applicability * 100)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all duration-300"
                        style={{width: `${recommendation.project_applicability * 100}%`}}
                      />
                    </div>
                  </div>
                )}
                {recommendation.skill_development !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Skill Development</span>
                      <span className="text-blue-400 font-semibold">{Math.round(recommendation.skill_development * 100)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-300"
                        style={{width: `${recommendation.skill_development * 100}%`}}
                      />
                    </div>
                  </div>
                )}
              </>
            ) : isEnhancedRecommendation ? (
              // Enhanced recommendation analysis (Phase 1+2)
              <>
                {recommendation.confidence !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Confidence Score</span>
                      <span className="text-purple-400 font-semibold">{Math.round(recommendation.confidence)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300"
                        style={{width: `${recommendation.confidence}%`}}
                      />
                    </div>
                  </div>
                )}
                {recommendation.quality_score !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Quality Score</span>
                      <span className="text-green-400 font-semibold">{Math.round(recommendation.quality_score)}/10</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all duration-300"
                        style={{width: `${(recommendation.quality_score / 10) * 100}%`}}
                      />
                    </div>
                  </div>
                )}
                {recommendation.diversity_score !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Diversity Score</span>
                      <span className="text-blue-400 font-semibold">{Math.round(recommendation.diversity_score * 100)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-300"
                        style={{width: `${recommendation.diversity_score * 100}%`}}
                      />
                    </div>
                  </div>
                )}
                {recommendation.novelty_score !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Novelty Score</span>
                      <span className="text-orange-400 font-semibold">{Math.round(recommendation.novelty_score * 100)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-orange-500 to-red-500 transition-all duration-300"
                        style={{width: `${recommendation.novelty_score * 100}%`}}
                      />
                    </div>
                  </div>
                )}
              </>
            ) : isGeminiRecommendation ? (
              // Gemini-enhanced recommendation analysis
              <>
                {recommendation.analysis.technology_match !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Technology Match</span>
                      <span className="text-purple-400 font-semibold">{Math.round(recommendation.analysis.technology_match)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300"
                        style={{width: `${recommendation.analysis.technology_match}%`}}
                      />
                    </div>
                  </div>
                )}
                {recommendation.analysis.content_relevance !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Content Relevance</span>
                      <span className="text-blue-400 font-semibold">{Math.round(recommendation.analysis.content_relevance)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-300"
                        style={{width: `${recommendation.analysis.content_relevance}%`}}
                      />
                    </div>
                  </div>
                )}
                {recommendation.analysis.semantic_similarity !== undefined && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Semantic Similarity</span>
                      <span className="text-green-400 font-semibold">{Math.round(recommendation.analysis.semantic_similarity)}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all duration-300"
                        style={{width: `${recommendation.analysis.semantic_similarity}%`}}
                      />
                    </div>
                  </div>
                )}
                {recommendation.analysis.quality_indicators && (
                  <div className="bg-gray-800/30 rounded-xl p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-300">Content Quality</span>
                      <span className="text-yellow-400 font-semibold">{recommendation.analysis.quality_indicators.completeness || 0}%</span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-yellow-500 to-orange-500 transition-all duration-300"
                        style={{width: `${recommendation.analysis.quality_indicators.completeness || 0}%`}}
                      />
                    </div>
                  </div>
                )}
              </>
            ) : isTaskRecommendation ? (
              // Task recommendation analysis (old format)
              <>
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-300">Technology Match</span>
                    <span className="text-green-400 font-semibold">{Math.round(recommendation.analysis.tech_score)}/40</span>
                  </div>
                  <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all duration-300"
                      style={{width: `${(recommendation.analysis.tech_score/40)*100}%`}}
                    />
                  </div>
                </div>
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-300">Task Type Alignment</span>
                    <span className="text-blue-400 font-semibold">{Math.round(recommendation.analysis.task_type_score)}/25</span>
                  </div>
                  <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-300"
                      style={{width: `${(recommendation.analysis.task_type_score/25)*100}%`}}
                    />
                  </div>
                </div>
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-300">Requirements Match</span>
                    <span className="text-purple-400 font-semibold">{Math.round(recommendation.analysis.requirements_score)}/20</span>
                  </div>
                  <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300"
                      style={{width: `${(recommendation.analysis.requirements_score/20)*100}%`}}
                    />
                  </div>
                </div>
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-300">Semantic Similarity</span>
                    <span className="text-orange-400 font-semibold">{Math.round(recommendation.analysis.semantic_score)}/15</span>
                  </div>
                  <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-orange-500 to-red-500 transition-all duration-300"
                      style={{width: `${(recommendation.analysis.semantic_score/15)*100}%`}}
                    />
                  </div>
                </div>
              </>
            ) : (
              // General recommendation analysis (old format)
              <>
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-300">Technology Match</span>
                    <span className="text-green-400 font-semibold">{Math.round(recommendation.analysis.tech_score)}/30</span>
                  </div>
                  <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all duration-300"
                      style={{width: `${(recommendation.analysis.tech_score/30)*100}%`}}
                    />
                  </div>
                </div>
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-300">Content Relevance</span>
                    <span className="text-blue-400 font-semibold">{Math.round(recommendation.analysis.content_score)}/20</span>
                  </div>
                  <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-300"
                      style={{width: `${(recommendation.analysis.content_score/20)*100}%`}}
                    />
                  </div>
                </div>
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-300">Difficulty Match</span>
                    <span className="text-purple-400 font-semibold">{Math.round(recommendation.analysis.difficulty_score)}/15</span>
                  </div>
                  <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300"
                      style={{width: `${(recommendation.analysis.difficulty_score/15)*100}%`}}
                    />
                  </div>
                </div>
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-300">Intent Alignment</span>
                    <span className="text-orange-400 font-semibold">{Math.round(recommendation.analysis.intent_score)}/15</span>
                  </div>
                  <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-orange-500 to-red-500 transition-all duration-300"
                      style={{width: `${(recommendation.analysis.intent_score/15)*100}%`}}
                    />
                  </div>
                </div>
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-300">Semantic Similarity</span>
                    <span className="text-yellow-400 font-semibold">{Math.round(recommendation.analysis.semantic_score)}/20</span>
                  </div>
                  <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-yellow-500 to-orange-500 transition-all duration-300"
                      style={{width: `${(recommendation.analysis.semantic_score/20)*100}%`}}
                    />
                  </div>
                </div>
              </>
            )}
          </div>
          
          {/* Content Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="bg-gray-800/30 rounded-xl p-4">
              <h5 className="text-white font-semibold mb-3 flex items-center space-x-2">
                <Settings className="w-4 h-4 text-blue-400" />
                <span>Technologies</span>
              </h5>
              <div className="flex flex-wrap gap-2">
                {recommendation.analysis.technologies && recommendation.analysis.technologies.length > 0 ? (
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
            
            {!isSimpleRecommendation && (
              <div className="bg-gray-800/30 rounded-xl p-4">
                <h5 className="text-white font-semibold mb-3">Content Details</h5>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Type:</span>
                    <span className="text-gray-300">{recommendation.analysis.content_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Difficulty:</span>
                    <span className="text-gray-300">{recommendation.analysis.complexity}</span>
                  </div>
                  {!isTaskRecommendation && (
                    <div className="flex justify-between">
                      <span className="text-gray-400">Intent:</span>
                      <span className="text-gray-300">{recommendation.analysis.intent}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {/* Additional Details for Different Types */}
          {isSimpleRecommendation && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {recommendation.analysis.bookmark_technologies && (
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <h5 className="text-white font-semibold mb-3">Bookmark Technologies</h5>
                  <div className="flex flex-wrap gap-2">
                    {recommendation.analysis.bookmark_technologies.length > 0 ? (
                      recommendation.analysis.bookmark_technologies.map((tech, index) => (
                        <span key={index} className="px-2 py-1 bg-green-600/20 text-green-400 text-xs rounded-lg">
                          {tech}
                        </span>
                      ))
                    ) : (
                      <span className="text-gray-500 text-sm">None detected</span>
                    )}
                  </div>
                </div>
              )}
              
              {recommendation.analysis.project_technologies && (
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <h5 className="text-white font-semibold mb-3">Project Technologies</h5>
                  <div className="flex flex-wrap gap-2">
                    {recommendation.analysis.project_technologies.length > 0 ? (
                      recommendation.analysis.project_technologies.map((tech, index) => (
                        <span key={index} className="px-2 py-1 bg-purple-600/20 text-purple-400 text-xs rounded-lg">
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
          
          {isSmartRecommendation && (
            <div className="grid grid-cols-1 gap-4 mb-6">
              {recommendation.technologies && recommendation.technologies.length > 0 && (
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <h5 className="text-white font-semibold mb-3 flex items-center space-x-2">
                    <Code className="w-4 h-4 text-purple-400" />
                    <span>Technologies</span>
                  </h5>
                  <div className="flex flex-wrap gap-2">
                    {recommendation.technologies.map((tech, index) => (
                      <span key={index} className="px-2 py-1 bg-purple-600/20 text-purple-400 text-xs rounded-lg">
                        {tech}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {recommendation.key_concepts && recommendation.key_concepts.length > 0 && (
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <h5 className="text-white font-semibold mb-3 flex items-center space-x-2">
                    <BookOpen className="w-4 h-4 text-blue-400" />
                    <span>Key Concepts</span>
                  </h5>
                  <div className="flex flex-wrap gap-2">
                    {recommendation.key_concepts.map((concept, index) => (
                      <span key={index} className="px-2 py-1 bg-blue-600/20 text-blue-400 text-xs rounded-lg">
                        {concept}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="bg-gray-800/30 rounded-xl p-4">
                <h5 className="text-white font-semibold mb-3 flex items-center space-x-2">
                  <TargetIcon className="w-4 h-4 text-purple-400" />
                  <span>Content Details</span>
                </h5>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Type:</span>
                    <span className="text-gray-300">{recommendation.content_type || 'Article'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Difficulty:</span>
                    <span className="text-gray-300">{recommendation.difficulty || 'Intermediate'}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {isGeminiRecommendation && (
            <div className="grid grid-cols-1 gap-4 mb-6">
              {recommendation.analysis.gemini_technologies && (
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <h5 className="text-white font-semibold mb-3 flex items-center space-x-2">
                    <Brain className="w-4 h-4 text-purple-400" />
                    <span>Gemini Technologies</span>
                  </h5>
                  <div className="flex flex-wrap gap-2">
                    {recommendation.analysis.gemini_technologies.length > 0 ? (
                      recommendation.analysis.gemini_technologies.map((tech, index) => (
                        <span key={index} className="px-2 py-1 bg-purple-600/20 text-purple-400 text-xs rounded-lg">
                          {tech}
                        </span>
                      ))
                    ) : (
                      <span className="text-gray-500 text-sm">None detected</span>
                    )}
                  </div>
                </div>
              )}
              
              {recommendation.analysis.gemini_summary && (
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <h5 className="text-white font-semibold mb-3">Gemini Summary</h5>
                  <p className="text-gray-300 text-sm">{recommendation.analysis.gemini_summary}</p>
                </div>
              )}
              
              {recommendation.analysis.learning_objectives && (
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <h5 className="text-white font-semibold mb-3">Learning Objectives</h5>
                  <div className="flex flex-wrap gap-2">
                    {recommendation.analysis.learning_objectives.length > 0 ? (
                      recommendation.analysis.learning_objectives.map((objective, index) => (
                        <span key={index} className="px-2 py-1 bg-blue-600/20 text-blue-400 text-xs rounded-lg">
                          {objective}
                        </span>
                      ))
                    ) : (
                      <span className="text-gray-500 text-sm">None detected</span>
                    )}
                  </div>
                </div>
              )}
              
              {recommendation.analysis.target_audience && (
                <div className="bg-gray-800/30 rounded-xl p-4">
                  <h5 className="text-white font-semibold mb-3">Target Audience</h5>
                  <p className="text-gray-300 text-sm">{recommendation.analysis.target_audience}</p>
                </div>
              )}
            </div>
          )}
          
          {isTaskRecommendation && recommendation.analysis.requirements && (
            <div className="bg-gray-800/30 rounded-xl p-4 mb-6">
              <h5 className="text-white font-semibold mb-3">Requirements</h5>
              <div className="flex flex-wrap gap-2">
                {recommendation.analysis.requirements.length > 0 ? (
                  recommendation.analysis.requirements.map((req, index) => (
                    <span key={index} className="px-2 py-1 bg-orange-600/20 text-orange-400 text-xs rounded-lg">
                      {req}
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
          <div className="flex items-center space-x-3">
            <a 
              href={recommendation.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white rounded-lg transition-all duration-300 transform hover:scale-105"
            >
              <ExternalLink className="w-4 h-4" />
              <span>Visit Link</span>
            </a>
            <button 
              onClick={onSave}
              className="flex items-center space-x-2 px-4 py-2 bg-gray-800/50 hover:bg-purple-600/20 text-gray-300 hover:text-purple-400 border border-gray-700 hover:border-purple-500/50 rounded-lg transition-all duration-300"
            >
              <Bookmark className="w-4 h-4" />
              <span>Save</span>
            </button>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleFeedback(recommendation.id, 'positive')}
              className="p-2 bg-gray-800/50 hover:bg-green-600/20 text-gray-400 hover:text-green-400 border border-gray-700 hover:border-green-500/50 rounded-lg transition-all duration-300"
              title="Like this recommendation"
            >
              <ThumbsUp className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleFeedback(recommendation.id, 'negative')}
              className="p-2 bg-gray-800/50 hover:bg-red-600/20 text-gray-400 hover:text-red-400 border border-gray-700 hover:border-red-500/50 rounded-lg transition-all duration-300"
              title="Dislike this recommendation"
            >
              <ThumbsDown className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        {recommendation.notes && (
          <div className="mt-4 pt-4 border-t border-gray-800">
            <div className="bg-gray-800/30 rounded-lg p-3">
              <span className="text-gray-400 font-medium">Notes: </span>
              <span className="text-gray-300">{recommendation.notes}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Recommendations