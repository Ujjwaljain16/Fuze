import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import api from '../services/api'
import logo1 from '../assets/logo1.svg'
import { 
  FolderOpen, 
  Sparkles, 
  ExternalLink, 
  Bookmark, 
  Plus, 
  Edit, 
  Trash2,
  RefreshCw,
  Lightbulb,
  Calendar,
  Tag,
  CheckSquare,
  Clock,
  Zap,
  Target,
  AlertCircle,
  LogOut
} from 'lucide-react'

const ProjectDetail = () => {
  const { id } = useParams()
  const { isAuthenticated, logout } = useAuth()
  const { success, error } = useToast()
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [project, setProject] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [projectBookmarks, setProjectBookmarks] = useState([])
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [tasksLoading, setTasksLoading] = useState(false)
  const [showAITaskModal, setShowAITaskModal] = useState(false)
  const [aiGenerating, setAiGenerating] = useState(false)
  const [skillLevel, setSkillLevel] = useState('intermediate')

  useEffect(() => {
    if (isAuthenticated && id) {
      fetchProjectData()
      fetchTasks()
    }
  }, [isAuthenticated, id])

  const fetchProjectData = async () => {
    try {
      setLoading(true)
      const projectRes = await api.get(`/api/projects/${id}`)
      setProject(projectRes.data.project)
      setProjectBookmarks(projectRes.data.bookmarks || [])
      
      // Get project-specific recommendations using unified orchestrator
      try {
        const recommendationsRes = await api.post('/api/recommendations/unified-orchestrator', {
          title: projectRes.data.project.title,
          description: projectRes.data.project.description,
          technologies: projectRes.data.project.technologies,
          user_interests: 'Project-specific learning and development',
          project_id: parseInt(id),
          max_recommendations: 10,
          engine_preference: 'auto',
          diversity_weight: 0.3,
          quality_threshold: 6,
          include_global_content: true,
          enhance_with_gemini: true
        })
        setRecommendations(recommendationsRes.data.recommendations || [])
      } catch (recError) {
        console.error('Error fetching project recommendations:', recError)
        setRecommendations([])
      }
    } catch (err) {
      console.error('Error fetching project data:', err)
      error('Failed to load project data')
    } finally {
      setLoading(false)
    }
  }

  const handleRefreshRecommendations = async () => {
    setRefreshing(true)
    try {
      const response = await api.post('/api/recommendations/unified-orchestrator', {
        title: project.title,
        description: project.description,
        technologies: project.technologies,
        user_interests: 'Project-specific learning and development',
        project_id: parseInt(id),
        max_recommendations: 10,
        engine_preference: 'auto',
        diversity_weight: 0.3,
        quality_threshold: 6,
        include_global_content: true,
        enhance_with_gemini: true
      })
      setRecommendations(response.data.recommendations || [])
      success('Recommendations refreshed!')
    } catch (err) {
      console.error('Error refreshing recommendations:', err)
      error('Failed to refresh recommendations')
    } finally {
      setRefreshing(false)
    }
  }

  const handleSaveRecommendation = async (recommendation) => {
    try {
      await api.post('/api/bookmarks', {
        url: recommendation.url,
        title: recommendation.title,
        description: recommendation.description || '',
        category: 'recommended',
        project_id: id
      })
      
      // Remove from recommendations and add to project bookmarks
      setRecommendations(prev => prev.filter(rec => rec.id !== recommendation.id))
      setProjectBookmarks(prev => [...prev, recommendation])
      success('Content saved to project!')
    } catch (err) {
      console.error('Error saving recommendation:', err)
      error('Failed to save content')
    }
  }

  const handleFeedback = async (recommendationId, feedbackType) => {
    try {
      await api.post('/api/recommendations/feedback', {
        content_id: recommendationId,
        feedback_type: feedbackType,
        project_id: id
      })
      // Optionally refresh recommendations after feedback
    } catch (err) {
      console.error('Error submitting feedback:', err)
    }
  }

  const fetchTasks = async () => {
    try {
      setTasksLoading(true)
      const response = await api.get(`/api/tasks/project/${id}`)
      setTasks(response.data.tasks || [])
    } catch (err) {
      console.error('Error fetching tasks:', err)
    } finally {
      setTasksLoading(false)
    }
  }

  const handleAIGenerateTasks = async () => {
    try {
      setAiGenerating(true)
      const response = await api.post('/api/tasks/ai-breakdown', {
        project_id: parseInt(id),
        project_description: project.description,
        skill_level: skillLevel
      })

      if (response.data.success) {
        success(`🤖 Generated ${response.data.tasks.length} AI-powered tasks!`)
        setShowAITaskModal(false)
        fetchTasks()
      } else {
        error('Failed to generate tasks')
      }
    } catch (err) {
      console.error('Error generating AI tasks:', err)
      error(err.response?.data?.error || 'Failed to generate AI tasks')
    } finally {
      setAiGenerating(false)
    }
  }

  const handleDeleteTask = async (taskId) => {
    if (!confirm('Delete this task?')) return

    try {
      await api.delete(`/api/tasks/${taskId}`)
      success('Task deleted')
      fetchTasks()
    } catch (err) {
      error('Failed to delete task')
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="container">
        <div className="auth-required">
          <h2>Authentication Required</h2>
          <p>Please log in to view project details.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="container">
        <div className="loading">
          <FolderOpen className="loading-icon" />
          <p>Loading project details...</p>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="container">
        <div className="error-state">
          <h2>Project Not Found</h2>
          <p>The project you're looking for doesn't exist or you don't have access to it.</p>
          <Link to="/projects" className="btn btn-primary">
            Back to Projects
          </Link>
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
            background: 'radial-gradient(circle, rgba(34, 197, 94, 0.3) 0%, transparent 70%)',
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
              className="border border-green-500/10 animate-pulse"
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
            {/* Project Header */}
            <div className="mt-8 mb-8 bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl rounded-2xl p-8 border border-gray-800 shadow-2xl overflow-visible">
              <div className="flex items-center justify-between mb-6 min-w-0">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-4 mb-4 min-w-0">
                    <div className="relative flex-shrink-0">
                      <FolderOpen className="w-8 h-8 text-green-400" />
                      <div className="absolute inset-0 blur-lg bg-green-400 opacity-50 animate-pulse" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h1 className="text-4xl font-bold break-words" style={{ 
                        wordBreak: 'break-word', 
                        overflowWrap: 'anywhere',
                        background: 'linear-gradient(to right, #4ade80, #10b981)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text',
                        color: '#4ade80',
                        width: '100%',
                        maxWidth: '100%',
                        display: 'block'
                      }}>{project.title}</h1>
                      {project.description && (
                        <p className="text-gray-300 text-xl mt-2 break-words" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere', width: '100%' }}>{project.description}</p>
                      )}
                    </div>
                  </div>
                  
                  {project.technologies && (
                    <div className="flex flex-wrap gap-2">
                      {project.technologies.split(',').map((tech, index) => (
                        <span key={index} className="px-2 py-1 bg-green-600/20 text-green-400 text-xs rounded-lg">
                          {tech.trim()}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-4">
                  <button className="px-4 py-2 border border-gray-700 rounded-xl hover:border-gray-500/50 hover:bg-gray-500/10 transition-all duration-300 flex items-center space-x-2">
                    <Edit size={16} />
                    <span>Edit Project</span>
                  </button>
                  <button className="px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 rounded-xl font-semibold hover:shadow-lg hover:shadow-green-500/25 transition-all duration-300 transform hover:scale-105 flex items-center space-x-2">
                    <Plus size={16} />
                    <span>Add Content</span>
                  </button>
                </div>
              </div>
            </div>

            <div className="space-y-8">
        {/* Project Bookmarks Section */}
        <div className="section">
          <div className="section-header">
            <h2>Saved Content for This Project</h2>
            <span className="bookmark-count">
              {projectBookmarks.length} items
            </span>
          </div>
          
          {projectBookmarks.length > 0 ? (
            <div className="bookmarks-grid">
              {projectBookmarks.map((bookmark) => (
                <div key={bookmark.id} className="bookmark-card">
                  <div className="bookmark-content">
                    <h4 className="bookmark-title">{bookmark.title}</h4>
                    <p className="bookmark-url">{bookmark.url}</p>
                    {bookmark.description && (
                      <p className="bookmark-description">{bookmark.description}</p>
                    )}
                    {bookmark.category && (
                      <span className="bookmark-category">{bookmark.category}</span>
                    )}
                  </div>
                  <div className="bookmark-actions">
                    <a 
                      href={bookmark.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="bookmark-link"
                    >
                      <ExternalLink size={16} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Bookmark className="empty-icon" />
              <h3>No content saved to this project yet</h3>
              <p>Start by adding content or saving recommendations below.</p>
            </div>
          )}
        </div>

        {/* Tasks Section */}
        <div className="section">
          <div className="section-header">
            <div className="section-title">
              <CheckSquare className="section-icon" />
              <h2>Project Tasks</h2>
            </div>
            <button 
              onClick={() => setShowAITaskModal(true)}
              className="btn btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Zap size={16} />
              AI Generate Tasks
            </button>
          </div>

          {tasksLoading ? (
            <div className="loading-state">
              <RefreshCw className="animate-spin" size={24} />
              <p>Loading tasks...</p>
            </div>
          ) : tasks.length > 0 ? (
            <div className="tasks-grid" style={{ display: 'grid', gap: '16px' }}>
              {tasks.map((task) => {
                let taskDetails = {}
                try {
                  taskDetails = typeof task.description === 'string' 
                    ? JSON.parse(task.description) 
                    : task.description
                } catch (e) {
                  taskDetails = { description: task.description }
                }

                return (
                  <div key={task.id} className="task-card" style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '12px',
                    padding: '16px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
                      <h4 style={{ color: '#fff', margin: 0, flex: 1 }}>{task.title}</h4>
                      <button 
                        onClick={() => handleDeleteTask(task.id)}
                        style={{
                          background: 'rgba(239,68,68,0.2)',
                          border: 'none',
                          borderRadius: '8px',
                          padding: '6px',
                          cursor: 'pointer',
                          color: '#f87171'
                        }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>

                    {taskDetails.description && (
                      <p style={{ color: '#d1d5db', fontSize: '14px', marginBottom: '12px' }}>
                        {taskDetails.description}
                      </p>
                    )}

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                      {taskDetails.estimated_time && (
                        <span style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '4px 8px',
                          background: 'rgba(59,130,246,0.2)',
                          color: '#60a5fa',
                          borderRadius: '6px',
                          fontSize: '12px'
                        }}>
                          <Clock size={12} />
                          {taskDetails.estimated_time}
                        </span>
                      )}
                      
                      {taskDetails.difficulty && (
                        <span style={{
                          padding: '4px 8px',
                          background: taskDetails.difficulty === 'beginner' ? 'rgba(34,197,94,0.2)' :
                                      taskDetails.difficulty === 'intermediate' ? 'rgba(251,146,60,0.2)' :
                                      'rgba(239,68,68,0.2)',
                          color: taskDetails.difficulty === 'beginner' ? '#4ade80' :
                                 taskDetails.difficulty === 'intermediate' ? '#fb923c' :
                                 '#f87171',
                          borderRadius: '6px',
                          fontSize: '12px'
                        }}>
                          {taskDetails.difficulty}
                        </span>
                      )}
                    </div>

                    {taskDetails.key_technologies && taskDetails.key_technologies.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
                        {taskDetails.key_technologies.map((tech, idx) => (
                          <span key={idx} style={{
                            padding: '2px 8px',
                            background: 'rgba(167,139,250,0.2)',
                            color: '#a78bfa',
                            borderRadius: '4px',
                            fontSize: '11px'
                          }}>
                            {tech}
                          </span>
                        ))}
                      </div>
                    )}

                    {taskDetails.success_criteria && (
                      <div style={{
                        marginTop: '12px',
                        padding: '8px',
                        background: 'rgba(34,197,94,0.1)',
                        borderLeft: '3px solid #4ade80',
                        borderRadius: '4px'
                      }}>
                        <p style={{ color: '#86efac', fontSize: '12px', margin: 0, display: 'flex', alignItems: 'start', gap: '6px' }}>
                          <Target size={12} style={{ marginTop: '2px', flexShrink: 0 }} />
                          <span>{taskDetails.success_criteria}</span>
                        </p>
                      </div>
                    )}

                    {taskDetails.prerequisites && taskDetails.prerequisites.length > 0 && (
                      <div style={{
                        marginTop: '8px',
                        padding: '8px',
                        background: 'rgba(251,146,60,0.1)',
                        borderLeft: '3px solid #fb923c',
                        borderRadius: '4px'
                      }}>
                        <p style={{ color: '#fdba74', fontSize: '11px', margin: 0, fontWeight: 'bold' }}>
                          Prerequisites:
                        </p>
                        <ul style={{ margin: '4px 0 0 0', paddingLeft: '20px', color: '#fed7aa', fontSize: '11px' }}>
                          {taskDetails.prerequisites.map((prereq, idx) => (
                            <li key={idx}>{prereq}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="empty-state">
              <CheckSquare className="empty-icon" size={48} style={{ color: '#9ca3af' }} />
              <h3 style={{ color: '#fff' }}>No tasks yet</h3>
              <p style={{ color: '#d1d5db' }}>Use AI to generate a complete task breakdown for this project!</p>
              <button 
                onClick={() => setShowAITaskModal(true)}
                className="btn btn-primary"
                style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <Zap size={16} />
                Generate Tasks with AI
              </button>
            </div>
          )}
        </div>

        {/* AI Task Generation Modal */}
        {showAITaskModal && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}>
            <div style={{
              background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
              borderRadius: '16px',
              padding: '32px',
              maxWidth: '500px',
              width: '90%',
              border: '1px solid rgba(255,255,255,0.1)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
                <div style={{
                  background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                  padding: '12px',
                  borderRadius: '12px'
                }}>
                  <Sparkles size={24} style={{ color: '#fff' }} />
                </div>
                <div>
                  <h2 style={{ color: '#fff', margin: 0, fontSize: '24px' }}>AI Task Generation</h2>
                  <p style={{ color: '#9ca3af', margin: '4px 0 0 0', fontSize: '14px' }}>
                    Generate intelligent task breakdown with Gemini AI
                  </p>
                </div>
              </div>

              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', color: '#d1d5db', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
                  Your Skill Level
                </label>
                <select
                  value={skillLevel}
                  onChange={(e) => setSkillLevel(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '14px'
                  }}
                >
                  <option value="beginner">Beginner - I'm new to this</option>
                  <option value="intermediate">Intermediate - I have some experience</option>
                  <option value="advanced">Advanced - I'm experienced</option>
                </select>
              </div>

              <div style={{
                background: 'rgba(59,130,246,0.1)',
                border: '1px solid rgba(59,130,246,0.3)',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '24px'
              }}>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'start' }}>
                  <AlertCircle size={16} style={{ color: '#60a5fa', marginTop: '2px', flexShrink: 0 }} />
                  <p style={{ color: '#93c5fd', fontSize: '13px', margin: 0 }}>
                    AI will analyze your project and create 5-8 detailed tasks with time estimates, 
                    technologies, and success criteria based on your skill level.
                  </p>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  onClick={() => setShowAITaskModal(false)}
                  disabled={aiGenerating}
                  style={{
                    flex: 1,
                    padding: '12px',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: '#d1d5db',
                    fontSize: '14px',
                    fontWeight: '500',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleAIGenerateTasks}
                  disabled={aiGenerating}
                  style={{
                    flex: 1,
                    padding: '12px',
                    background: aiGenerating ? 'rgba(99,102,241,0.5)' : 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '14px',
                    fontWeight: '500',
                    cursor: aiGenerating ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  {aiGenerating ? (
                    <>
                      <RefreshCw size={16} className="animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Zap size={16} />
                      Generate Tasks
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* AI Recommendations Section */}
        <div className="section recommendations-section">
          <div className="section-header">
            <div className="section-title">
              <Sparkles className="section-icon" />
              <h2>Intelligent Recommendations for This Project</h2>
            </div>
            <div className="section-actions">
              <button 
                onClick={handleRefreshRecommendations}
                disabled={refreshing}
                className="btn btn-secondary btn-sm"
              >
                <RefreshCw size={16} className={refreshing ? 'spinning' : ''} />
                {refreshing ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
          
          <div className="recommendations-explanation">
            <Lightbulb size={16} />
            <p>
              These recommendations are powered by AI, finding content semantically 
              similar to your project's description and technologies.
            </p>
          </div>

          {recommendations.length > 0 ? (
            <div className="recommendations-grid">
              {recommendations.map((rec) => (
                <div key={rec.id} className="recommendation-card">
                  <div className="recommendation-header">
                    <div className="recommendation-meta">
                      <Lightbulb className="recommendation-icon" />
                      <span className="recommendation-score">
                        Match: {rec.score || 'High'}%
                      </span>
                    </div>
                    <div className="recommendation-actions">
                      <button 
                        onClick={() => handleFeedback(rec.id, 'relevant')}
                        className="feedback-button positive"
                        title="This is relevant"
                      >
                        👍
                      </button>
                      <button 
                        onClick={() => handleFeedback(rec.id, 'not_relevant')}
                        className="feedback-button negative"
                        title="This is not relevant"
                      >
                        👎
                      </button>
                    </div>
                  </div>
                  
                  <h4 className="recommendation-title">{rec.title}</h4>
                  <p className="recommendation-url">{rec.url}</p>
                  
                  {rec.description && (
                    <p className="recommendation-description">{rec.description}</p>
                  )}
                  
                  {rec.reason && (
                    <div className="recommendation-reason">
                      <strong>Why recommended:</strong> {rec.reason}
                    </div>
                  )}
                  
                  <div className="recommendation-footer">
                    <a 
                      href={rec.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="recommendation-link"
                    >
                      <ExternalLink size={16} />
                      View Content
                    </a>
                    <button 
                      onClick={() => handleSaveRecommendation(rec)}
                      className="save-recommendation-btn"
                    >
                      <Bookmark size={16} />
                      Save to Project
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Sparkles className="empty-icon" />
              <h3>No recommendations available</h3>
              <p>
                Add more content to your project or update your project description 
                to get personalized recommendations.
              </p>
              <button 
                onClick={handleRefreshRecommendations}
                className="btn btn-primary"
              >
                <RefreshCw size={16} />
                Refresh Recommendations
              </button>
            </div>
          )}
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
      `}</style>
    </div>
  )
}

export default ProjectDetail 