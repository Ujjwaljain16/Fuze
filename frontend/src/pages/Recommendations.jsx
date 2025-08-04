import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { 
  Sparkles, Lightbulb, ExternalLink, Bookmark, ThumbsUp, ThumbsDown, 
  Filter, RefreshCw, Target, CheckCircle, Brain, Zap, Star, Plus,
  Globe, Clock, TrendingUp, BarChart3, Settings, Search, BookOpen,
  Code, GraduationCap, Briefcase, Users, Award, Target as TargetIcon
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
  const [emptyMessage, setEmptyMessage] = useState('')
  const [taskAnalysis, setTaskAnalysis] = useState(null)
  const [geminiAvailable, setGeminiAvailable] = useState(false)
  const [useGemini, setUseGemini] = useState(false) // Default to FAST recommendations
  const [contextAnalysis, setContextAnalysis] = useState(null)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [filterOptions, setFilterOptions] = useState([
    { value: 'all', label: 'All Recommendations' },
    { value: 'general', label: 'General' }
  ])
  
  // New state for smart recommendations
  const [recommendationMode, setRecommendationMode] = useState('smart') // 'smart', 'learning', 'project'
  const [smartRecommendationForm, setSmartRecommendationForm] = useState({
    project_title: '',
    project_description: '',
    technologies: '',
    learning_goals: ''
  })
  const [learningPathForm, setLearningPathForm] = useState({
    target_skill: '',
    current_level: 'beginner'
  })
  const [projectRecommendationForm, setProjectRecommendationForm] = useState({
    project_type: 'web-app',
    technologies: '',
    complexity: 'moderate'
  })
  const [showSmartForm, setShowSmartForm] = useState(false)
  const [showLearningPathForm, setShowLearningPathForm] = useState(false)
  const [showProjectForm, setShowProjectForm] = useState(false)
  const [enhancedFeatures, setEnhancedFeatures] = useState([])
  const [enhancedEngineAvailable, setEnhancedEngineAvailable] = useState(false)
  const [useEnhancedEngine, setUseEnhancedEngine] = useState(false)
  const [enhancedEngineStatus, setEnhancedEngineStatus] = useState(null)
  const [performanceMetrics, setPerformanceMetrics] = useState(null)
  const [phase3Available, setPhase3Available] = useState(false)
  const [usePhase3, setUsePhase3] = useState(false)
  const [learningInsights, setLearningInsights] = useState(null)
  const [contextualInfo, setContextualInfo] = useState(null)

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      fetchProjects()
      checkGeminiStatus()
      checkEnhancedEngineStatus()
      fetchRecommendations()
    }
  }, [isAuthenticated])

  useEffect(() => {
    if (isAuthenticated && filter) {
      fetchRecommendations()
    }
  }, [filter, useGemini, useEnhancedEngine, usePhase3])

  const checkGeminiStatus = async () => {
    try {
      console.log('Checking Gemini status...')
      const response = await api.get('/api/recommendations/gemini-status')
      console.log('Gemini status response:', response.data)
      setGeminiAvailable(response.data.gemini_available)
      if (!response.data.gemini_available) {
        setUseGemini(false) // Fallback to regular recommendations
      }
    } catch (error) {
      console.error('Error checking Gemini status:', error)
      // Don't let this error block other functionality
      setGeminiAvailable(false)
      setUseGemini(false)
    }
  }

  const checkEnhancedEngineStatus = async () => {
    try {
      console.log('Checking enhanced engine status...')
      const response = await api.get('/api/recommendations/enhanced-status')
      console.log('Enhanced engine status response:', response.data)
      setEnhancedEngineAvailable(response.data.enhanced_engine_available)
      setEnhancedEngineStatus(response.data)
      setPhase3Available(response.data.phase_3_complete)
      if (response.data.enhanced_engine_available) {
        setUseEnhancedEngine(true) // Default to enhanced engine if available
      }
      if (response.data.phase_3_complete) {
        setUsePhase3(true) // Default to Phase 3 if available
      }
    } catch (error) {
      console.error('Error checking enhanced engine status:', error)
      setEnhancedEngineAvailable(false)
      setUseEnhancedEngine(false)
      setPhase3Available(false)
      setUsePhase3(false)
    }
  }

  const fetchPerformanceMetrics = async () => {
    try {
      if (!enhancedEngineAvailable) return
      
      const response = await api.get('/api/recommendations/performance-metrics')
      setPerformanceMetrics(response.data)
    } catch (error) {
      console.error('Error fetching performance metrics:', error)
    }
  }

  const fetchLearningInsights = async () => {
    try {
      if (!phase3Available) return
      
      const response = await api.get('/api/recommendations/phase3/insights')
      setLearningInsights(response.data)
    } catch (error) {
      console.error('Error fetching learning insights:', error)
    }
  }

  const fetchProjects = async () => {
    try {
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
      
      setFilterOptions([
        { value: 'all', label: 'All Recommendations' },
        { value: 'general', label: 'General' },
        ...projectOptions,
        ...taskOptions
      ])
    } catch (error) {
      console.error('Error fetching projects:', error)
    }
  }

  const fetchRecommendations = async () => {
    try {
      setLoading(true)
      let endpoint
      let method = 'GET'
      let data = null
      
      // Prioritize Phase 3 if available
      if (usePhase3 && phase3Available) {
        endpoint = '/api/recommendations/phase3/recommendations'
        method = 'POST'
        data = {
          project_title: selectedProject ? selectedProject.title : 'Personalized Learning',
          project_description: selectedProject ? selectedProject.description : 'Based on my projects and interests',
          technologies: selectedProject ? selectedProject.technologies : projects.map(p => p.technologies).filter(tech => tech && tech.trim()).join(', '),
          learning_goals: 'Master relevant technologies and improve skills',
          content_type: filter === 'all' ? 'all' : filter,
          difficulty: 'all',
          max_recommendations: 10
        }
      }
      // Fallback to enhanced engine if available
      else if (useEnhancedEngine && enhancedEngineAvailable) {
        if (filter === 'all' || filter === 'general') {
          endpoint = '/api/recommendations/enhanced'
          method = 'POST'
          data = {
            project_title: 'Personalized Learning Recommendations',
            project_description: 'Based on my projects and interests, I want to discover relevant learning resources and tutorials',
            technologies: projects.map(p => p.technologies).filter(tech => tech && tech.trim()).join(', '),
            learning_goals: 'Master relevant technologies and improve skills',
            content_type: 'all',
            difficulty: 'all',
            max_recommendations: 10
          }
        } else {
          endpoint = `/api/recommendations/${filter}`
          method = 'POST'
          data = {
            project_title: selectedProject ? selectedProject.title : `${filter.charAt(0).toUpperCase() + filter.slice(1)} Project`,
            project_description: selectedProject ? selectedProject.description : `Building a ${filter} application`,
            technologies: selectedProject ? selectedProject.technologies : projects.map(p => p.technologies).filter(tech => tech && tech.trim()).join(', '),
            learning_goals: `Master ${filter} development`,
            content_type: 'all',
            difficulty: 'all',
            max_recommendations: 10
          }
        }
      }
      // Fallback to Gemini if available
      else if (useGemini && geminiAvailable) {
        endpoint = '/api/recommendations/gemini'
        method = 'POST'
        data = {
          project_title: selectedProject ? selectedProject.title : 'Learning Project',
          project_description: selectedProject ? selectedProject.description : 'I want to learn and improve my skills',
          technologies: selectedProject ? selectedProject.technologies : projects.map(p => p.technologies).filter(tech => tech && tech.trim()).join(', '),
          learning_goals: 'Master relevant technologies and improve skills',
          content_type: filter === 'all' ? 'all' : filter,
          difficulty: 'all',
          max_recommendations: 10
        }
      }
      // Fallback to regular recommendations
      else {
        endpoint = `/api/recommendations/${filter}`
        method = 'GET'
      }
      
      const response = method === 'GET' ? 
        await api.get(endpoint) : 
        await api.post(endpoint, data)
      
      if (response.data.recommendations) {
        setRecommendations(response.data.recommendations)
        setEnhancedFeatures(response.data.enhanced_features || [])
        
        // Extract contextual information from Phase 3
        if (response.data.contextual_info) {
          setContextualInfo(response.data.contextual_info)
        }
        
        // Extract learning insights from Phase 3
        if (response.data.learning_insights) {
          setLearningInsights(response.data.learning_insights)
        }
      } else {
        setRecommendations([])
        setEnhancedFeatures([])
      }
    } catch (error) {
      console.error('Error fetching recommendations:', error)
      setRecommendations([])
      setEnhancedFeatures([])
    } finally {
      setLoading(false)
    }
  }

  // New function for smart recommendations
  const fetchSmartRecommendations = async (formData) => {
    try {
      setLoading(true)
      const response = await api.post('/api/recommendations/smart-recommendations', formData)
      
      const recommendations = response.data.recommendations || []
      setRecommendations(recommendations)
      setEnhancedFeatures(response.data.enhanced_features || [])
      
      if (recommendations.length === 0) {
        setEmptyMessage('No smart recommendations found')
      } else {
        setEmptyMessage('')
      }
    } catch (error) {
      console.error('Error fetching smart recommendations:', error)
      setEmptyMessage('Failed to load smart recommendations')
    } finally {
      setLoading(false)
    }
  }

  // New function for learning path recommendations
  const fetchLearningPathRecommendations = async (formData) => {
    try {
      setLoading(true)
      const response = await api.post('/api/recommendations/learning-path-recommendations', formData)
      
      const recommendations = response.data.recommendations || []
      setRecommendations(recommendations)
      
      if (recommendations.length === 0) {
        setEmptyMessage('No learning path recommendations found')
      } else {
        setEmptyMessage('')
      }
    } catch (error) {
      console.error('Error fetching learning path recommendations:', error)
      setEmptyMessage('Failed to load learning path recommendations')
    } finally {
      setLoading(false)
    }
  }

  // New function for project recommendations
  const fetchProjectRecommendations = async (formData) => {
    try {
      setLoading(true)
      const response = await api.post('/api/recommendations/project-recommendations', formData)
      
      const recommendations = response.data.recommendations || []
      setRecommendations(recommendations)
      
      if (recommendations.length === 0) {
        setEmptyMessage('No project recommendations found')
      } else {
        setEmptyMessage('')
      }
    } catch (error) {
      console.error('Error fetching project recommendations:', error)
      setEmptyMessage('Failed to load project recommendations')
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

            {/* Controls Section */}
            <div className="mb-8 bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl rounded-2xl p-6 border border-gray-800">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
                {/* Filter Controls */}
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-3">
                    <Filter className="w-5 h-5 text-blue-400" />
                    <span className="text-white font-medium">Filter by:</span>
                  </div>
                  <div className="filter-container" style={{ minWidth: 200, position: 'relative', zIndex: 1000 }}>
                    <Select
                      classNamePrefix="react-select"
                      value={filterOptions.find(opt => opt.value === filter)}
                      onChange={option => setFilter(option.value)}
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
                  </div>
                </div>
                
                {/* Gemini Controls */}
                <div className="flex items-center space-x-4">
                  {geminiAvailable ? (
                    <div className="flex items-center space-x-3 bg-gray-800/50 rounded-xl p-3">
                      <Brain className="w-5 h-5 text-blue-400" />
                      <span className="text-white font-medium">Gemini AI:</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={useGemini}
                          onChange={(e) => setUseGemini(e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300/25 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gradient-to-r peer-checked:from-blue-600 peer-checked:to-purple-600"></div>
                        <span className="ml-3 text-sm font-medium text-gray-300">
                          {useGemini ? 'Enhanced' : 'Standard'}
                        </span>
                      </label>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-3 bg-gray-800/30 rounded-xl p-3">
                      <Brain className="w-5 h-5 text-gray-500" />
                      <span className="text-gray-500">Gemini AI Unavailable</span>
                    </div>
                  )}
                </div>
                
                {/* Enhanced Engine Controls */}
                <div className="flex items-center space-x-4">
                  {enhancedEngineAvailable ? (
                    <div className="flex items-center space-x-3 bg-gray-800/50 rounded-xl p-3">
                      <Zap className="w-5 h-5 text-yellow-400" />
                      <span className="text-white font-medium">Enhanced Engine:</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={useEnhancedEngine}
                          onChange={(e) => setUseEnhancedEngine(e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                  ) : null}
                </div>

                {/* Phase 3 Controls */}
                <div className="flex items-center space-x-4">
                  {phase3Available ? (
                    <div className="flex items-center space-x-3 bg-gradient-to-r from-purple-800/50 to-pink-800/50 rounded-xl p-3 border border-purple-500/30">
                      <Brain className="w-5 h-5 text-purple-400" />
                      <span className="text-white font-medium">Phase 3 AI:</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={usePhase3}
                          onChange={(e) => setUsePhase3(e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                      </label>
                      <span className="text-purple-300 text-sm">Contextual + Learning</span>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>

            {/* Smart Recommendation Controls */}
            <div className="mb-8 bg-gradient-to-br from-purple-900/20 to-pink-900/20 backdrop-blur-xl rounded-2xl p-6 border border-purple-500/30">
              <div className="flex items-center space-x-3 mb-6">
                <div className="relative">
                  <TargetIcon className="w-6 h-6 text-purple-400" />
                  <div className="absolute inset-0 blur-lg bg-purple-400 opacity-50 animate-pulse" />
                </div>
                <h3 className="text-xl font-semibold text-white">AI-Enhanced Recommendations</h3>
                <div className="flex items-center space-x-2 bg-gradient-to-r from-purple-600/20 to-pink-600/20 px-3 py-1 rounded-full">
                  <Award className="w-4 h-4 text-purple-400" />
                  <span className="text-purple-400 text-sm font-medium">Smart Matching</span>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Smart Recommendations */}
                <button
                  onClick={() => setShowSmartForm(!showSmartForm)}
                  className={`flex items-center space-x-3 p-4 rounded-xl transition-all duration-300 ${
                    showSmartForm 
                      ? 'bg-gradient-to-r from-purple-600/20 to-pink-600/20 border border-purple-500/50' 
                      : 'bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700'
                  }`}
                >
                  <Brain className="w-5 h-5 text-purple-400" />
                  <div className="text-left">
                    <div className="text-white font-medium">Smart Recommendations</div>
                    <div className="text-gray-400 text-sm">AI-powered content matching</div>
                  </div>
                </button>

                {/* Learning Path */}
                <button
                  onClick={() => setShowLearningPathForm(!showLearningPathForm)}
                  className={`flex items-center space-x-3 p-4 rounded-xl transition-all duration-300 ${
                    showLearningPathForm 
                      ? 'bg-gradient-to-r from-blue-600/20 to-cyan-600/20 border border-blue-500/50' 
                      : 'bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700'
                  }`}
                >
                  <GraduationCap className="w-5 h-5 text-blue-400" />
                  <div className="text-left">
                    <div className="text-white font-medium">Learning Path</div>
                    <div className="text-gray-400 text-sm">Skill-based progression</div>
                  </div>
                </button>

                {/* Project Recommendations */}
                <button
                  onClick={() => setShowProjectForm(!showProjectForm)}
                  className={`flex items-center space-x-3 p-4 rounded-xl transition-all duration-300 ${
                    showProjectForm 
                      ? 'bg-gradient-to-r from-green-600/20 to-emerald-600/20 border border-green-500/50' 
                      : 'bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700'
                  }`}
                >
                  <Briefcase className="w-5 h-5 text-green-400" />
                  <div className="text-left">
                    <div className="text-white font-medium">Project Focus</div>
                    <div className="text-gray-400 text-sm">Implementation-ready content</div>
                  </div>
                </button>
              </div>

              {/* Smart Recommendation Form */}
              {showSmartForm && (
                <div className="mt-6 p-6 bg-gray-800/30 rounded-xl border border-purple-500/30">
                  <h4 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                    <Brain className="w-5 h-5 text-purple-400" />
                    <span>Smart Recommendation Request</span>
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-2">Project Title</label>
                      <input
                        type="text"
                        value={smartRecommendationForm.project_title}
                        onChange={(e) => setSmartRecommendationForm(prev => ({ ...prev, project_title: e.target.value }))}
                        placeholder="e.g., React Learning Project"
                        className="w-full px-4 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
                      />
                    </div>
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-2">Technologies</label>
                      <input
                        type="text"
                        value={smartRecommendationForm.technologies}
                        onChange={(e) => setSmartRecommendationForm(prev => ({ ...prev, technologies: e.target.value }))}
                        placeholder="e.g., JavaScript, React, Node.js"
                        className="w-full px-4 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
                      />
                    </div>
                  </div>
                  <div className="mb-4">
                    <label className="block text-gray-300 text-sm font-medium mb-2">Project Description</label>
                    <textarea
                      value={smartRecommendationForm.project_description}
                      onChange={(e) => setSmartRecommendationForm(prev => ({ ...prev, project_description: e.target.value }))}
                      placeholder="Describe your project goals and what you want to learn..."
                      rows="3"
                      className="w-full px-4 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
                    />
                  </div>
                  <div className="mb-4">
                    <label className="block text-gray-300 text-sm font-medium mb-2">Learning Goals</label>
                    <input
                      type="text"
                      value={smartRecommendationForm.learning_goals}
                      onChange={(e) => setSmartRecommendationForm(prev => ({ ...prev, learning_goals: e.target.value }))}
                      placeholder="e.g., Master React hooks and state management"
                      className="w-full px-4 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
                    />
                  </div>
                  <button
                    onClick={() => fetchSmartRecommendations(smartRecommendationForm)}
                    disabled={loading}
                    className="bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-purple-500/25 transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Getting Recommendations...' : 'Get Smart Recommendations'}
                  </button>
                </div>
              )}

              {/* Learning Path Form */}
              {showLearningPathForm && (
                <div className="mt-6 p-6 bg-gray-800/30 rounded-xl border border-blue-500/30">
                  <h4 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                    <GraduationCap className="w-5 h-5 text-blue-400" />
                    <span>Learning Path Request</span>
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-2">Target Skill</label>
                      <input
                        type="text"
                        value={learningPathForm.target_skill}
                        onChange={(e) => setLearningPathForm(prev => ({ ...prev, target_skill: e.target.value }))}
                        placeholder="e.g., React, Python, Machine Learning"
                        className="w-full px-4 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-2">Current Level</label>
                      <select
                        value={learningPathForm.current_level}
                        onChange={(e) => setLearningPathForm(prev => ({ ...prev, current_level: e.target.value }))}
                        className="w-full px-4 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                      >
                        <option value="beginner">Beginner</option>
                        <option value="intermediate">Intermediate</option>
                        <option value="advanced">Advanced</option>
                      </select>
                    </div>
                  </div>
                  <button
                    onClick={() => fetchLearningPathRecommendations(learningPathForm)}
                    disabled={loading}
                    className="bg-gradient-to-r from-blue-600 to-cyan-600 px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-blue-500/25 transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Getting Learning Path...' : 'Get Learning Path'}
                  </button>
                </div>
              )}

              {/* Project Recommendations Form */}
              {showProjectForm && (
                <div className="mt-6 p-6 bg-gray-800/30 rounded-xl border border-green-500/30">
                  <h4 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                    <Briefcase className="w-5 h-5 text-green-400" />
                    <span>Project Recommendation Request</span>
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-2">Project Type</label>
                      <select
                        value={projectRecommendationForm.project_type}
                        onChange={(e) => setProjectRecommendationForm(prev => ({ ...prev, project_type: e.target.value }))}
                        className="w-full px-4 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-green-500"
                      >
                        <option value="web-app">Web Application</option>
                        <option value="mobile-app">Mobile App</option>
                        <option value="api">API/Backend</option>
                        <option value="data-science">Data Science</option>
                        <option value="game">Game Development</option>
                        <option value="ai-ml">AI/Machine Learning</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-2">Technologies</label>
                      <input
                        type="text"
                        value={projectRecommendationForm.technologies}
                        onChange={(e) => setProjectRecommendationForm(prev => ({ ...prev, technologies: e.target.value }))}
                        placeholder="e.g., React, Node.js, MongoDB"
                        className="w-full px-4 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                      />
                    </div>
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-2">Complexity</label>
                      <select
                        value={projectRecommendationForm.complexity}
                        onChange={(e) => setProjectRecommendationForm(prev => ({ ...prev, complexity: e.target.value }))}
                        className="w-full px-4 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-green-500"
                      >
                        <option value="simple">Simple</option>
                        <option value="moderate">Moderate</option>
                        <option value="complex">Complex</option>
                      </select>
                    </div>
                  </div>
                  <button
                    onClick={() => fetchProjectRecommendations(projectRecommendationForm)}
                    disabled={loading}
                    className="bg-gradient-to-r from-green-600 to-emerald-600 px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-green-500/25 transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Getting Project Recommendations...' : 'Get Project Recommendations'}
                  </button>
                </div>
              )}
            </div>

            {/* Enhanced Features Display */}
            {enhancedFeatures && enhancedFeatures.length > 0 && (
              <div className="mb-8 bg-gradient-to-br from-purple-900/20 to-pink-900/20 backdrop-blur-xl rounded-2xl p-6 border border-purple-500/30">
                <div className="flex items-center space-x-3 mb-6">
                  <div className="relative">
                    <Award className="w-6 h-6 text-purple-400" />
                    <div className="absolute inset-0 blur-lg bg-purple-400 opacity-50 animate-pulse" />
                  </div>
                  <h3 className="text-xl font-semibold text-white">Smart AI Features</h3>
                  <div className="flex items-center space-x-2 bg-gradient-to-r from-purple-600/20 to-pink-600/20 px-3 py-1 rounded-full">
                    <TargetIcon className="w-4 h-4 text-purple-400" />
                    <span className="text-purple-300 text-sm font-medium">Phase 1+2</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {enhancedFeatures.map((feature, index) => (
                    <div key={index} className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" />
                        <span className="text-gray-300 text-sm font-medium">{feature.replace(/_/g, ' ')}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Learning Insights Display */}
            {learningInsights && (
              <div className="mb-8 bg-gradient-to-br from-blue-900/20 to-cyan-900/20 backdrop-blur-xl rounded-2xl p-6 border border-blue-500/30">
                <div className="flex items-center space-x-3 mb-6">
                  <div className="relative">
                    <Brain className="w-6 h-6 text-blue-400" />
                    <div className="absolute inset-0 blur-lg bg-blue-400 opacity-50 animate-pulse" />
                  </div>
                  <h3 className="text-xl font-semibold text-white">Learning Insights</h3>
                  <div className="flex items-center space-x-2 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 px-3 py-1 rounded-full">
                    <TargetIcon className="w-4 h-4 text-blue-400" />
                    <span className="text-blue-300 text-sm font-medium">Phase 3</span>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {/* Engagement Score */}
                  <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-300 text-sm">Engagement</span>
                      <span className="text-blue-400 font-semibold">
                        {Math.round(learningInsights.engagement_score * 100)}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
                        style={{ width: `${learningInsights.engagement_score * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Content Effectiveness */}
                  <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-300 text-sm">Effectiveness</span>
                      <span className="text-green-400 font-semibold">
                        {Math.round(learningInsights.content_effectiveness * 100)}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all duration-500"
                        style={{ width: `${learningInsights.content_effectiveness * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Learning Progress */}
                  <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-300 text-sm">Progress</span>
                      <span className="text-yellow-400 font-semibold">
                        {Math.round(learningInsights.learning_progress * 100)}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-yellow-500 to-orange-500 transition-all duration-500"
                        style={{ width: `${learningInsights.learning_progress * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* User Satisfaction */}
                  <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-300 text-sm">Satisfaction</span>
                      <span className="text-purple-400 font-semibold">
                        {Math.round(learningInsights.user_satisfaction * 100)}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500"
                        style={{ width: `${learningInsights.user_satisfaction * 100}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Contextual Information */}
                {contextualInfo && (
                  <div className="mt-6 p-4 bg-gray-800/20 rounded-xl border border-gray-700/30">
                    <h4 className="text-lg font-semibold text-white mb-3">Contextual Analysis</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center">
                        <span className="text-gray-400 text-sm">Device</span>
                        <p className="text-blue-300 font-medium">{contextualInfo.device_optimized}</p>
                      </div>
                      <div className="text-center">
                        <span className="text-gray-400 text-sm">Time</span>
                        <p className="text-green-300 font-medium">{contextualInfo.time_appropriate}</p>
                      </div>
                      <div className="text-center">
                        <span className="text-gray-400 text-sm">Session</span>
                        <p className="text-yellow-300 font-medium">
                          {contextualInfo.session_context ? 'Active' : 'New'}
                        </p>
                      </div>
                      <div className="text-center">
                        <span className="text-gray-400 text-sm">Day</span>
                        <p className="text-purple-300 font-medium">{contextualInfo.day_of_week}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Performance Metrics Display */}
            {useEnhancedEngine && enhancedEngineAvailable && (
              <div className="mb-8 bg-gradient-to-br from-green-900/20 to-emerald-900/20 backdrop-blur-xl rounded-2xl p-6 border border-green-500/30">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-3">
                    <div className="relative">
                      <BarChart3 className="w-6 h-6 text-green-400" />
                      <div className="absolute inset-0 blur-lg bg-green-400 opacity-50 animate-pulse" />
                    </div>
                    <h3 className="text-xl font-semibold text-white">Enhanced Engine Performance</h3>
                    <div className="flex items-center space-x-2 bg-gradient-to-r from-green-600/20 to-emerald-600/20 px-3 py-1 rounded-full">
                      <TrendingUp className="w-4 h-4 text-green-400" />
                      <span className="text-green-400 text-sm font-medium">Phase 1+2 Active</span>
                    </div>
                  </div>
                  <button
                    onClick={fetchPerformanceMetrics}
                    className="bg-gradient-to-r from-green-600 to-emerald-600 px-4 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-green-500/25 transition-all duration-300 transform hover:scale-105"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
                
                {performanceMetrics ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-gray-800/30 rounded-xl p-4 text-center">
                      <div className="text-green-400 font-semibold mb-2">Response Time</div>
                      <div className="text-gray-300 text-sm">
                        {performanceMetrics.performance_metrics?.response_time_ms?.toFixed(2) || 'N/A'} ms
                      </div>
                    </div>
                    <div className="bg-gray-800/30 rounded-xl p-4 text-center">
                      <div className="text-green-400 font-semibold mb-2">Cache Hit Rate</div>
                      <div className="text-gray-300 text-sm">
                        {(performanceMetrics.performance_metrics?.cache_hit_rate * 100)?.toFixed(1) || 'N/A'}%
                      </div>
                    </div>
                    <div className="bg-gray-800/30 rounded-xl p-4 text-center">
                      <div className="text-green-400 font-semibold mb-2">Error Rate</div>
                      <div className="text-gray-300 text-sm">
                        {(performanceMetrics.performance_metrics?.error_rate * 100)?.toFixed(2) || 'N/A'}%
                      </div>
                    </div>
                    <div className="bg-gray-800/30 rounded-xl p-4 text-center">
                      <div className="text-green-400 font-semibold mb-2">Throughput</div>
                      <div className="text-gray-300 text-sm">
                        {performanceMetrics.performance_metrics?.throughput || 'N/A'} req/min
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-gray-400">Click refresh to load performance metrics</p>
                  </div>
                )}
              </div>
            )}

            {/* Context Analysis Display (Gemini Enhanced) */}
            {contextAnalysis && (
              <div className="mb-8 bg-gradient-to-br from-blue-900/20 to-purple-900/20 backdrop-blur-xl rounded-2xl p-6 border border-blue-500/30">
                <div className="flex items-center space-x-3 mb-6">
                  <div className="relative">
                    <Zap className="w-6 h-6 text-blue-400" />
                    <div className="absolute inset-0 blur-lg bg-blue-400 opacity-50 animate-pulse" />
                  </div>
                  <h3 className="text-xl font-semibold text-white">AI Context Analysis</h3>
                  {useGemini && (
                    <div className="flex items-center space-x-2 bg-gradient-to-r from-blue-600/20 to-purple-600/20 px-3 py-1 rounded-full">
                      <Star className="w-4 h-4 text-blue-400" />
                      <span className="text-blue-400 text-sm font-medium">Enhanced with Gemini AI</span>
                    </div>
                  )}
                </div>
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {contextAnalysis.input_analysis && (
                    <div className="bg-gray-800/30 rounded-xl p-4">
                      <h4 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                        <BarChart3 className="w-5 h-5 text-green-400" />
                        <span>Input Analysis</span>
                      </h4>
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-gray-300">Technologies:</span>
                          <span className="text-blue-400">
                            {contextAnalysis.input_analysis.technologies?.length > 0 
                              ? contextAnalysis.input_analysis.technologies.join(', ') 
                              : 'None detected'
                            }
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-300">Content Type:</span>
                          <span className="text-blue-400">{contextAnalysis.input_analysis.content_type || 'Unknown'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-300">Difficulty:</span>
                          <span className="text-blue-400">{contextAnalysis.input_analysis.difficulty || 'Unknown'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-300">Complexity Score:</span>
                          <div className="flex items-center space-x-2">
                            <div className="w-20 h-2 bg-gray-700 rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-gradient-to-r from-green-500 to-blue-500 transition-all duration-300"
                                style={{ width: `${contextAnalysis.input_analysis.complexity_score || 0}%` }}
                              />
                            </div>
                            <span className="text-blue-400 text-sm">{contextAnalysis.input_analysis.complexity_score || 0}%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {contextAnalysis.gemini_insights && (
                    <div className="bg-gray-800/30 rounded-xl p-4">
                      <h4 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                        <Brain className="w-5 h-5 text-purple-400" />
                        <span>Gemini Insights</span>
                      </h4>
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-gray-300">Project Type:</span>
                          <span className="text-purple-400">{contextAnalysis.gemini_insights.project_type || 'Unknown'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-300">Complexity Level:</span>
                          <span className="text-purple-400">{contextAnalysis.gemini_insights.complexity_level || 'Unknown'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-300">Development Stage:</span>
                          <span className="text-purple-400">{contextAnalysis.gemini_insights.development_stage || 'Unknown'}</span>
                        </div>
                        {contextAnalysis.gemini_insights.learning_needs?.length > 0 && (
                          <div>
                            <span className="text-gray-300">Learning Needs:</span>
                            <div className="flex flex-wrap gap-2 mt-2">
                              {contextAnalysis.gemini_insights.learning_needs.map((need, index) => (
                                <span key={index} className="px-2 py-1 bg-purple-600/20 text-purple-400 text-xs rounded-lg">
                                  {need}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {contextAnalysis.gemini_insights.project_summary && (
                          <div className="col-span-2">
                            <span className="text-gray-300">Project Summary:</span>
                            <p className="text-purple-400 text-sm mt-1">{contextAnalysis.gemini_insights.project_summary}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
                
                {contextAnalysis.processing_stats && (
                  <div className="mt-6 bg-gray-800/30 rounded-xl p-4">
                    <h4 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
                      <TrendingUp className="w-5 h-5 text-orange-400" />
                      <span>Processing Stats</span>
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-orange-400">{contextAnalysis.processing_stats.total_bookmarks_analyzed || 0}</div>
                        <div className="text-gray-400 text-sm">Bookmarks Analyzed</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-orange-400">{contextAnalysis.processing_stats.relevant_bookmarks_found || 0}</div>
                        <div className="text-gray-400 text-sm">Relevant Found</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-orange-400">{contextAnalysis.processing_stats.gemini_enhanced ? 'Yes' : 'No'}</div>
                        <div className="text-gray-400 text-sm">Gemini Enhanced</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Task Analysis Display */}
            {taskAnalysis && (
              <div className="mb-8 bg-gradient-to-br from-green-900/20 to-emerald-900/20 backdrop-blur-xl rounded-2xl p-6 border border-green-500/30">
                <div className="flex items-center space-x-3 mb-6">
                  <div className="relative">
                    <Target className="w-6 h-6 text-green-400" />
                    <div className="absolute inset-0 blur-lg bg-green-400 opacity-50 animate-pulse" />
                  </div>
                  <h3 className="text-xl font-semibold text-white">Task Analysis</h3>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-gray-800/30 rounded-xl p-4 text-center">
                    <div className="text-green-400 font-semibold mb-2">Technologies</div>
                    <div className="text-gray-300 text-sm">
                      {taskAnalysis.technologies.length > 0 
                        ? taskAnalysis.technologies.join(', ') 
                        : 'None detected'
                      }
                    </div>
                  </div>
                  <div className="bg-gray-800/30 rounded-xl p-4 text-center">
                    <div className="text-green-400 font-semibold mb-2">Task Type</div>
                    <div className="text-gray-300 text-sm">{taskAnalysis.task_type}</div>
                  </div>
                  <div className="bg-gray-800/30 rounded-xl p-4 text-center">
                    <div className="text-green-400 font-semibold mb-2">Complexity</div>
                    <div className="text-gray-300 text-sm">{taskAnalysis.complexity}</div>
                  </div>
                  <div className="bg-gray-800/30 rounded-xl p-4 text-center">
                    <div className="text-green-400 font-semibold mb-2">Requirements</div>
                    <div className="text-gray-300 text-sm">
                      {taskAnalysis.requirements.length > 0 
                        ? taskAnalysis.requirements.join(', ') 
                        : 'None detected'
                      }
                    </div>
                  </div>
                </div>
              </div>
            )}

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