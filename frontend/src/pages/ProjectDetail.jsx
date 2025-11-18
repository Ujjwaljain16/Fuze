import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import api from '../services/api'
import logo1 from '../assets/logo1.svg'
import { 
  FolderOpen, 
  ExternalLink, 
  Bookmark, 
  Plus, 
  Edit, 
  Trash2,
  RefreshCw,
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
  const [projectBookmarks, setProjectBookmarks] = useState([])
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [tasksLoading, setTasksLoading] = useState(false)
  const [showAITaskModal, setShowAITaskModal] = useState(false)
  const [aiGenerating, setAiGenerating] = useState(false)
  const [skillLevel, setSkillLevel] = useState('intermediate')
  const [expandedTasks, setExpandedTasks] = useState(new Set())
  const [editingSubtask, setEditingSubtask] = useState(null)
  const [newSubtaskTitle, setNewSubtaskTitle] = useState('')
  const [newSubtaskDescription, setNewSubtaskDescription] = useState('')
  const [addingSubtaskTo, setAddingSubtaskTo] = useState(null)
  const [showCreateTaskModal, setShowCreateTaskModal] = useState(false)
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskDescription, setNewTaskDescription] = useState('')

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
      
      // Backend returns project directly in response.data, not in response.data.project
      if (!projectRes.data || !projectRes.data.id) {
        console.error('Project not found in response:', projectRes.data)
        setProject(null)
        error('Project not found')
        return
      }
      
      // The project data is directly in projectRes.data
      setProject(projectRes.data)
      setProjectBookmarks(projectRes.data.bookmarks || [])
    } catch (err) {
      console.error('Error fetching project data:', err)
      setProject(null)
      if (err.response?.status === 404) {
        error('Project not found')
      } else if (err.response?.status === 403) {
        error('You do not have access to this project')
      } else {
        error('Failed to load project data')
      }
    } finally {
      setLoading(false)
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

  const handleCreateTask = async () => {
    if (!newTaskTitle.trim()) {
      error('Task title is required')
      return
    }

    try {
      await api.post('/api/tasks', {
        project_id: parseInt(id),
        title: newTaskTitle,
        description: newTaskDescription
      })
      success('Task created successfully')
      setNewTaskTitle('')
      setNewTaskDescription('')
      setShowCreateTaskModal(false)

      // Clear context cache since we added a new task
      if (window.clearContextCache) {
        window.clearContextCache()
      }
      // Also clear server-side context caches
      try {
        api.post('/api/recommendations/cache/clear-context')
      } catch (err) {
        console.warn('Failed to clear server context cache:', err)
      }

      fetchTasks()
    } catch (err) {
      error('Failed to create task')
    }
  }

  const handleDeleteTask = async (taskId) => {
    if (!confirm('Delete this task?')) return

    try {
      await api.delete(`/api/tasks/${taskId}`)
      success('Task deleted')

      // Clear context cache since we deleted a task
      if (window.clearContextCache) {
        window.clearContextCache()
      }
      // Also clear server-side context caches
      try {
        api.post('/api/recommendations/cache/clear-context')
      } catch (err) {
        console.warn('Failed to clear server context cache:', err)
      }

      fetchTasks()
    } catch (err) {
      error('Failed to delete task')
    }
  }

  const toggleTaskExpanded = (taskId) => {
    const newExpanded = new Set(expandedTasks)
    if (newExpanded.has(taskId)) {
      newExpanded.delete(taskId)
    } else {
      newExpanded.add(taskId)
    }
    setExpandedTasks(newExpanded)
  }

  const handleCreateSubtask = async (taskId) => {
    if (!newSubtaskTitle.trim()) {
      error('Subtask title is required')
      return
    }

    try {
      await api.post(`/api/tasks/${taskId}/subtasks`, {
        title: newSubtaskTitle,
        description: newSubtaskDescription
      })
      success('Subtask created')
      setNewSubtaskTitle('')
      setNewSubtaskDescription('')
      setAddingSubtaskTo(null)

      // Clear context cache since we added a new subtask
      if (window.clearContextCache) {
        window.clearContextCache()
      }
      // Also clear server-side context caches
      try {
        api.post('/api/recommendations/cache/clear-context')
      } catch (err) {
        console.warn('Failed to clear server context cache:', err)
      }

      fetchTasks()
    } catch (err) {
      error('Failed to create subtask')
    }
  }

  const handleUpdateSubtask = async (subtaskId, taskId, completed) => {
    try {
      await api.put(`/api/tasks/subtasks/${subtaskId}`, {
        completed: completed
      })
      fetchTasks()
    } catch (err) {
      error('Failed to update subtask')
    }
  }

  const handleDeleteSubtask = async (subtaskId) => {
    if (!confirm('Delete this subtask?')) return

    try {
      await api.delete(`/api/tasks/subtasks/${subtaskId}`)
      success('Subtask deleted')

      // Clear context cache since we deleted a subtask
      if (window.clearContextCache) {
        window.clearContextCache()
      }
      // Also clear server-side context caches
      try {
        api.post('/api/recommendations/cache/clear-context')
      } catch (err) {
        console.warn('Failed to clear server context cache:', err)
      }

      fetchTasks()
    } catch (err) {
      error('Failed to delete subtask')
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-black text-white relative overflow-hidden flex items-center justify-center">
        <div className="text-center relative z-10 max-w-md mx-auto p-8">
          <h2 className="text-3xl font-bold text-white mb-4">Authentication Required</h2>
          <p className="text-gray-400 mb-8">Please log in to view project details.</p>
          <Link 
            to="/login" 
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 rounded-xl font-semibold hover:shadow-lg hover:shadow-green-500/25 transition-all duration-300 transform hover:scale-105"
          >
            Go to Login
          </Link>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white relative overflow-hidden flex items-center justify-center">
        <div className="text-center relative z-10">
          <FolderOpen className="w-16 h-16 text-green-400 mx-auto mb-4 animate-pulse" />
          <p className="text-xl text-gray-300">Loading project details...</p>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-black text-white relative overflow-hidden flex items-center justify-center">
        <div className="text-center relative z-10 max-w-md mx-auto p-8">
          <div className="mb-6">
            <FolderOpen className="w-16 h-16 text-red-400 mx-auto mb-4" />
            <h2 className="text-3xl font-bold text-white mb-4">Project Not Found</h2>
            <p className="text-gray-400 mb-8">
              The project you're looking for doesn't exist or you don't have access to it.
            </p>
            <Link 
              to="/projects" 
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 rounded-xl font-semibold hover:shadow-lg hover:shadow-green-500/25 transition-all duration-300 transform hover:scale-105"
            >
              <FolderOpen className="w-5 h-5" />
              Back to Projects
            </Link>
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
            <div className="text-center py-16 bg-gradient-to-br from-gray-900/30 to-black/30 rounded-2xl border border-gray-800">
              <div className="p-6 bg-gradient-to-r from-green-600/20 to-emerald-600/20 rounded-full w-24 h-24 mx-auto mb-6">
                <Bookmark className="w-12 h-12 text-green-400 mx-auto mt-3" />
              </div>
              <h3 className="text-2xl font-semibold text-white mb-4">No content saved to this project yet</h3>
              <p className="text-gray-400 mb-8 max-w-md mx-auto">Start by adding content to your project to organize your bookmarks and resources.</p>
            </div>
          )}
        </div>

        {/* Tasks Section */}
        <div className="bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-gradient-to-r from-green-600/20 to-emerald-600/20 rounded-lg">
                <CheckSquare className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">Project Tasks</h2>
                <p className="text-gray-400 text-sm mt-1">{tasks.length} {tasks.length === 1 ? 'task' : 'tasks'}</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <button 
                onClick={() => setShowCreateTaskModal(true)}
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '8px',
                  padding: '10px 20px',
                  background: 'linear-gradient(135deg, #5C6BC0 0%, #9C27B0 100%)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '12px',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.3s',
                  boxShadow: '0 4px 12px rgba(156, 39, 176, 0.3)'
                }}
                onMouseEnter={(e) => {
                  e.target.style.transform = 'translateY(-2px)'
                  e.target.style.boxShadow = '0 6px 16px rgba(156, 39, 176, 0.4)'
                }}
                onMouseLeave={(e) => {
                  e.target.style.transform = 'translateY(0)'
                  e.target.style.boxShadow = '0 4px 12px rgba(156, 39, 176, 0.3)'
                }}
              >
                <Plus size={16} />
                Add Task
              </button>
              <button 
                onClick={() => setShowAITaskModal(true)}
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '8px',
                  padding: '10px 20px',
                  background: 'linear-gradient(135deg, #4DD0E1 0%, #5C6BC0 50%, #9C27B0 100%)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '12px',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.3s',
                  boxShadow: '0 4px 12px rgba(77, 208, 225, 0.3)'
                }}
                onMouseEnter={(e) => {
                  e.target.style.transform = 'translateY(-2px)'
                  e.target.style.boxShadow = '0 6px 16px rgba(77, 208, 225, 0.4)'
                }}
                onMouseLeave={(e) => {
                  e.target.style.transform = 'translateY(0)'
                  e.target.style.boxShadow = '0 4px 12px rgba(77, 208, 225, 0.3)'
                }}
              >
                <Zap size={16} />
                AI Generate Tasks
              </button>
            </div>
          </div>

          {tasksLoading ? (
            <div className="flex items-center justify-center py-16">
              <div className="text-center">
                <RefreshCw className="w-8 h-8 text-green-400 mx-auto mb-4 animate-spin" />
                <p className="text-gray-300">Loading tasks...</p>
              </div>
            </div>
          ) : tasks.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
                  <div key={task.id} className="group bg-gradient-to-br from-gray-800/50 to-black/50 backdrop-blur-xl border border-gray-700 rounded-xl p-6 hover:border-green-500/30 transition-all duration-300">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-xl font-semibold text-white group-hover:text-green-400 transition-colors duration-300 mb-2">
                          {task.title}
                        </h4>
                      </div>
                      <button 
                        onClick={() => handleDeleteTask(task.id)}
                        className="p-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition-colors duration-300 flex-shrink-0"
                        title="Delete task"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    {taskDetails.description && (
                      <p className="text-gray-400 mb-4 line-clamp-3">
                        {taskDetails.description}
                      </p>
                    )}

                    <div className="flex flex-wrap gap-2 mb-4">
                      {taskDetails.estimated_time && (
                        <span className="flex items-center gap-1 px-2 py-1 bg-blue-600/20 text-blue-400 text-xs rounded-lg">
                          <Clock className="w-3 h-3" />
                          {taskDetails.estimated_time}
                        </span>
                      )}
                      
                      {taskDetails.difficulty && (
                        <span className={`px-2 py-1 text-xs rounded-lg ${
                          taskDetails.difficulty === 'beginner' ? 'bg-green-600/20 text-green-400' :
                          taskDetails.difficulty === 'intermediate' ? 'bg-orange-600/20 text-orange-400' :
                          'bg-red-600/20 text-red-400'
                        }`}>
                          {taskDetails.difficulty}
                        </span>
                      )}
                    </div>

                    {taskDetails.key_technologies && taskDetails.key_technologies.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-4">
                        {taskDetails.key_technologies.map((tech, idx) => (
                          <span key={idx} className="px-2 py-1 bg-purple-600/20 text-purple-400 text-xs rounded-lg">
                            {tech}
                          </span>
                        ))}
                      </div>
                    )}

                    {taskDetails.success_criteria && (
                      <div className="mt-4 p-3 bg-green-600/10 border-l-3 border-green-500 rounded-lg">
                        <p className="text-green-400 text-xs flex items-start gap-2">
                          <Target className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          <span>{taskDetails.success_criteria}</span>
                        </p>
                      </div>
                    )}

                    {taskDetails.prerequisites && taskDetails.prerequisites.length > 0 && (
                      <div className="mt-4 p-3 bg-orange-600/10 border-l-3 border-orange-500 rounded-lg">
                        <p className="text-orange-400 text-xs font-semibold mb-2">
                          Prerequisites:
                        </p>
                        <ul className="text-orange-300 text-xs list-disc list-inside space-y-1">
                          {taskDetails.prerequisites.map((prereq, idx) => (
                            <li key={idx}>{prereq}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Subtasks Section */}
                    <div className="mt-4 pt-4 border-t border-gray-700">
                      <div className="flex items-center justify-between mb-3">
                        <button
                          onClick={() => toggleTaskExpanded(task.id)}
                          className="text-gray-400 hover:text-white transition-colors duration-300 text-sm flex items-center gap-2"
                        >
                          <CheckSquare className="w-4 h-4" />
                          <span>Subtasks ({task.subtasks?.length || 0})</span>
                          <span>
                            {expandedTasks.has(task.id) ? '▼' : '▶'}
                          </span>
                        </button>
                        <button
                          onClick={() => setAddingSubtaskTo(addingSubtaskTo === task.id ? null : task.id)}
                          className="px-3 py-1.5 bg-green-600/20 hover:bg-green-600/30 text-green-400 rounded-lg transition-colors duration-300 text-sm flex items-center gap-2"
                        >
                          <Plus className="w-3 h-3" />
                          Add Subtask
                        </button>
                      </div>

                      {expandedTasks.has(task.id) && (
                        <div className="mt-3">
                          {addingSubtaskTo === task.id && (
                            <div className="bg-green-600/10 border border-green-500/30 rounded-lg p-4 mb-4">
                              <input
                                type="text"
                                placeholder="Subtask title"
                                value={newSubtaskTitle}
                                onChange={(e) => setNewSubtaskTitle(e.target.value)}
                                className="w-full px-3 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 transition-all duration-300 text-sm mb-3"
                              />
                              <textarea
                                placeholder="Subtask description (optional)"
                                value={newSubtaskDescription}
                                onChange={(e) => setNewSubtaskDescription(e.target.value)}
                                rows="3"
                                className="w-full px-3 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 transition-all duration-300 text-sm resize-none mb-3"
                              />
                              <div className="flex gap-2">
                                <button
                                  onClick={() => handleCreateSubtask(task.id)}
                                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors duration-300 text-sm font-medium"
                                >
                                  Create
                                </button>
                                <button
                                  onClick={() => {
                                    setAddingSubtaskTo(null)
                                    setNewSubtaskTitle('')
                                    setNewSubtaskDescription('')
                                  }}
                                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors duration-300 text-sm font-medium"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          )}

                          {task.subtasks && task.subtasks.length > 0 ? (
                            <div className="space-y-2">
                              {task.subtasks.map((subtask) => (
                                <div
                                  key={subtask.id}
                                  className="flex items-start gap-3 p-3 bg-gray-800/30 border border-gray-700 rounded-lg hover:border-gray-600 transition-colors duration-300"
                                >
                                  <input
                                    type="checkbox"
                                    checked={subtask.completed}
                                    onChange={(e) => handleUpdateSubtask(subtask.id, task.id, e.target.checked)}
                                    className="mt-1 cursor-pointer w-4 h-4"
                                  />
                                  <div className="flex-1 min-w-0">
                                    <p className={`text-sm ${subtask.completed ? 'text-gray-500 line-through' : 'text-white'}`}>
                                      {subtask.title}
                                    </p>
                                    {subtask.description && (
                                      <p className={`text-xs mt-1 ${subtask.completed ? 'text-gray-600 line-through' : 'text-gray-400'}`}>
                                        {subtask.description}
                                      </p>
                                    )}
                                  </div>
                                  <button
                                    onClick={() => handleDeleteSubtask(subtask.id)}
                                    className="p-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition-colors duration-300 flex-shrink-0"
                                    title="Delete subtask"
                                  >
                                    <Trash2 className="w-3 h-3" />
                                  </button>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-gray-500 text-sm italic text-center py-4">
                              No subtasks yet. Click "Add Subtask" to create one.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-16 bg-gradient-to-br from-gray-900/30 to-black/30 rounded-2xl border border-gray-800">
              <div className="p-6 bg-gradient-to-r from-green-600/20 to-emerald-600/20 rounded-full w-24 h-24 mx-auto mb-6">
                <CheckSquare className="w-12 h-12 text-green-400 mx-auto mt-3" />
              </div>
              <h3 className="text-2xl font-semibold text-white mb-4">No tasks yet</h3>
              <p className="text-gray-400 mb-8 max-w-md mx-auto">Create tasks manually or use AI to generate a complete task breakdown for this project.</p>
              <div className="flex items-center justify-center gap-3">
                <button 
                  onClick={() => setShowCreateTaskModal(true)}
                  className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 rounded-xl font-semibold hover:shadow-lg hover:shadow-green-500/25 transition-all duration-300 transform hover:scale-105 flex items-center space-x-2"
                >
                  <Plus className="w-5 h-5" />
                  <span>Add Task</span>
                </button>
                <button 
                  onClick={() => setShowAITaskModal(true)}
                  className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-xl font-semibold hover:shadow-lg hover:shadow-purple-500/25 transition-all duration-300 transform hover:scale-105 flex items-center space-x-2"
                >
                  <Zap className="w-5 h-5" />
                  <span>AI Generate</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Manual Task Creation Modal */}
        {showCreateTaskModal && (
          <div 
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0,0,0,0.8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 9999,
              backdropFilter: 'blur(4px)'
            }}
            onClick={(e) => {
              if (e.target === e.currentTarget) {
                setShowCreateTaskModal(false)
                setNewTaskTitle('')
                setNewTaskDescription('')
              }
            }}
          >
            <div 
              style={{
                background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                borderRadius: '16px',
                padding: '32px',
                maxWidth: '500px',
                width: '90%',
                border: '1px solid rgba(255,255,255,0.1)',
                boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
                position: 'relative',
                zIndex: 10000
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
                <div style={{
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  padding: '12px',
                  borderRadius: '12px'
                }}>
                  <Plus size={24} style={{ color: '#fff' }} />
                </div>
                <div>
                  <h2 style={{ color: '#fff', margin: 0, fontSize: '24px' }}>Create New Task</h2>
                  <p style={{ color: '#9ca3af', margin: '4px 0 0 0', fontSize: '14px' }}>
                    Add a manual task to your project
                  </p>
                </div>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', color: '#d1d5db', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
                  Task Title *
                </label>
                <input
                  type="text"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  placeholder="e.g., Set up development environment"
                  style={{
                    width: '100%',
                    padding: '12px',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '14px'
                  }}
                />
              </div>

              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', color: '#d1d5db', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
                  Task Description (Optional)
                </label>
                <textarea
                  value={newTaskDescription}
                  onChange={(e) => setNewTaskDescription(e.target.value)}
                  placeholder="Describe what needs to be done in this task..."
                  rows="4"
                  style={{
                    width: '100%',
                    padding: '12px',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '14px',
                    resize: 'vertical'
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  onClick={() => {
                    setShowCreateTaskModal(false)
                    setNewTaskTitle('')
                    setNewTaskDescription('')
                  }}
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
                  onClick={handleCreateTask}
                  disabled={!newTaskTitle.trim()}
                  style={{
                    flex: 1,
                    padding: '12px',
                    background: !newTaskTitle.trim() ? 'rgba(16,185,129,0.5)' : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '14px',
                    fontWeight: '500',
                    cursor: !newTaskTitle.trim() ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  <Plus size={16} />
                  Create Task
                </button>
              </div>
            </div>
          </div>
        )}

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
                  <Zap size={24} style={{ color: '#fff' }} />
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