import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { Link } from 'react-router-dom'
import api from '../services/api'
import logo1 from '../assets/logo1.svg'
import { 
  FolderOpen, Plus, Edit, Trash2, Calendar, Zap, ExternalLink,
  Settings, Grid3X3, List, Star, Clock, TrendingUp, 
  BarChart3, Globe, MoreHorizontal, Tag, Sparkles, LogOut, CheckSquare, Loader2
} from 'lucide-react'

const Projects = () => {
  const { isAuthenticated, logout } = useAuth()
  const { success, error } = useToast()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [showEditForm, setShowEditForm] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [editingProject, setEditingProject] = useState(null)
  const [deletingProject, setDeletingProject] = useState(null)
  const [viewMode, setViewMode] = useState('grid')
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    technologies: ''
  })
  const [tasks, setTasks] = useState([])
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskDescription, setNewTaskDescription] = useState('')
  const [showTasksSection, setShowTasksSection] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [isUpdating, setIsUpdating] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)
  const [isSmallMobile, setIsSmallMobile] = useState(window.innerWidth <= 480)

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768)
      setIsSmallMobile(window.innerWidth <= 480)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      fetchProjects()
    }
  }, [isAuthenticated])

  const fetchProjects = async () => {
    try {
      setLoading(true)
      const response = await api.get('/api/projects')
      setProjects(response.data.projects || [])
    } catch (error) {
      console.error('Error fetching projects:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateProject = async (e) => {
    e.preventDefault()
    setIsCreating(true)
    try {
      const response = await api.post('/api/projects', formData)
      const projectId = response.data.project_id || response.data.project.id
      
      // Create tasks if any were added
      let tasksCreated = 0
      if (tasks.length > 0 && projectId) {
        for (const task of tasks) {
          try {
            await api.post('/api/tasks', {
              project_id: projectId,
              title: task.title,
              description: task.description || ''
            })
            tasksCreated++
          } catch (taskError) {
            console.error('Error creating task:', taskError)
          }
        }
      }
      
      setFormData({ title: '', description: '', technologies: '' })
      setTasks([])
      setNewTaskTitle('')
      setNewTaskDescription('')
      setShowTasksSection(false)
      setShowCreateForm(false)

      // Clear context cache since we added a new project
      if (window.clearContextCache) {
        window.clearContextCache()
      }
      // Also clear server-side context caches
      try {
        api.post('/api/recommendations/cache/clear-context')
      } catch (err) {
        console.warn('Failed to clear server context cache:', err)
      }

      await fetchProjects()
      
      if (tasksCreated > 0) {
        success(`Project created successfully with ${tasksCreated} task${tasksCreated > 1 ? 's' : ''}!`)
      } else {
        success('Project created successfully!')
      }
    } catch (err) {
      console.error('Error creating project:', err)
      error(err.response?.data?.error || 'Failed to create project. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  const handleEditProject = async (e) => {
    e.preventDefault()
    setIsUpdating(true)
    try {
      await api.put(`/api/projects/${editingProject.id}`, formData)
      
      // Create tasks if any were added
      let tasksCreated = 0
      if (tasks.length > 0 && editingProject.id) {
        for (const task of tasks) {
          try {
            await api.post('/api/tasks', {
              project_id: editingProject.id,
              title: task.title,
              description: task.description || ''
            })
            tasksCreated++
          } catch (taskError) {
            console.error('Error creating task:', taskError)
          }
        }
      }
      
      setFormData({ title: '', description: '', technologies: '' })
      setTasks([])
      setNewTaskTitle('')
      setNewTaskDescription('')
      setShowTasksSection(false)
      setShowEditForm(false)
      setEditingProject(null)

      // Clear context cache since we updated a project
      if (window.clearContextCache) {
        window.clearContextCache()
      }
      // Also clear server-side context caches
      try {
        api.post('/api/recommendations/cache/clear-context')
      } catch (err) {
        console.warn('Failed to clear server context cache:', err)
      }

      await fetchProjects()
      
      if (tasksCreated > 0) {
        success(`Project updated successfully with ${tasksCreated} new task${tasksCreated > 1 ? 's' : ''}!`)
      } else {
        success('Project updated successfully!')
      }
    } catch (err) {
      console.error('Error updating project:', err)
      error(err.response?.data?.error || 'Failed to update project. Please try again.')
    } finally {
      setIsUpdating(false)
    }
  }

  const handleDeleteProject = async () => {
    setIsDeleting(true)
    try {
      await api.delete(`/api/projects/${deletingProject.id}`)
      setShowDeleteModal(false)
      const deletedTitle = deletingProject.title
      setDeletingProject(null)

      // Clear context cache since we deleted a project
      if (window.clearContextCache) {
        window.clearContextCache()
      }
      // Also clear server-side context caches
      try {
        api.post('/api/recommendations/cache/clear-context')
      } catch (err) {
        console.warn('Failed to clear server context cache:', err)
      }

      await fetchProjects()
      success(`Project "${deletedTitle}" deleted successfully!`)
    } catch (err) {
      console.error('Error deleting project:', err)
      error(err.response?.data?.error || 'Failed to delete project. Please try again.')
    } finally {
      setIsDeleting(false)
    }
  }

  const openEditForm = (project) => {
    setEditingProject(project)
    setFormData({
      title: project.title,
      description: project.description || '',
      technologies: project.technologies || ''
    })
    setShowEditForm(true)
  }

  const openDeleteModal = (project) => {
    setDeletingProject(project)
    setShowDeleteModal(true)
  }

  const closeForms = () => {
    setShowCreateForm(false)
    setShowEditForm(false)
    setShowDeleteModal(false)
    setEditingProject(null)
    setDeletingProject(null)
    setFormData({ title: '', description: '', technologies: '' })
    setTasks([])
    setNewTaskTitle('')
    setNewTaskDescription('')
    setShowTasksSection(false)
  }

  const addTask = () => {
    if (newTaskTitle.trim()) {
      setTasks([...tasks, { title: newTaskTitle, description: newTaskDescription }])
      setNewTaskTitle('')
      setNewTaskDescription('')
    }
  }

  const removeTask = (index) => {
    setTasks(tasks.filter((_, i) => i !== index))
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
          <div className="max-w-md mx-auto text-center">
            <div className="mb-8">
              <div className="flex items-center justify-center space-x-3 mb-4">
                <div className="relative">
                  <FolderOpen className="w-12 h-12 text-cyan-400" />
                  <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                </div>
              </div>
              <h2 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 via-teal-400 to-emerald-400 bg-clip-text text-transparent mb-4">
                Authentication Required
              </h2>
              <p className="text-xl text-gray-300">
                Please log in to view and manage your projects.
              </p>
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
            <FolderOpen className="w-12 h-12 text-cyan-400 mx-auto animate-spin" />
            <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
          </div>
          <p className="text-xl text-gray-300">Loading your projects...</p>
        </div>
      </div>
    )
  }

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

      <div className="relative z-10">
        {/* Main Content */}
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
              <div className={`flex ${isSmallMobile ? 'flex-col gap-4' : 'items-center justify-between'} min-w-0 flex-wrap gap-4`}>
                <div className="flex-1 min-w-0">
                  <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-4'} ${isMobile ? 'mb-3' : 'mb-4'} min-w-0`}>
                    <div className="relative flex-shrink-0">
                      <FolderOpen className={`${isMobile ? 'w-6 h-6' : 'w-8 h-8'} text-cyan-400`} />
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
                        My Projects
                      </h1>
                      <p className={`text-gray-300 ${isMobile ? 'text-base mt-1' : 'text-xl mt-2'} break-words`} style={{ wordBreak: 'break-word', overflowWrap: 'anywhere', color: '#d1d5db', width: '100%' }}>Organize and manage your development projects and ideas.</p>
                    </div>
                  </div>
                </div>
                
                <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-3 w-full' : 'space-x-4'}`}>
                  <button 
                    onClick={() => setShowCreateForm(true)}
                    className={`bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} ${isSmallMobile ? 'w-full' : ''} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 flex items-center ${isSmallMobile ? 'justify-center' : 'space-x-2'} group relative overflow-hidden`}
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 to-teal-400 opacity-0 group-hover:opacity-20 transition-opacity duration-300"></div>
                    <Plus className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} group-hover:rotate-90 transition-transform duration-300`} />
                    <span>{isSmallMobile ? 'New' : 'New Project'}</span>
                  </button>
                  
                  <div className={`flex items-center ${isSmallMobile ? 'w-full justify-center' : 'space-x-2'} bg-gray-800/50 rounded-xl p-1`}>
                    <button
                      onClick={() => setViewMode('grid')}
                      className={`p-2 rounded-lg transition-all duration-300 ${viewMode === 'grid' ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-500/25' : 'text-gray-400 hover:text-white hover:bg-gray-700/50'}`}
                    >
                      <Grid3X3 className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                    </button>
                    <button
                      onClick={() => setViewMode('list')}
                      className={`p-2 rounded-lg transition-all duration-300 ${viewMode === 'list' ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-500/25' : 'text-gray-400 hover:text-white hover:bg-gray-700/50'}`}
                    >
                      <List className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Projects Content */}
            {projects.length > 0 ? (
              viewMode === 'grid' ? (
                <div className={`grid grid-cols-1 ${isMobile ? 'sm:grid-cols-2' : 'md:grid-cols-2 lg:grid-cols-3'} ${isMobile ? 'gap-4' : 'gap-6'}`}>
                  {projects.map((project) => (
                    <Link 
                      key={project.id} 
                      to={`/projects/${project.id}`}
                      className={`group bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl ${isMobile ? 'p-4' : 'p-6'} hover:border-cyan-500/30 transition-all duration-300 transform hover:scale-[1.02] block cursor-pointer`}
                    >
                      <div className={`flex items-start justify-between ${isMobile ? 'mb-3' : 'mb-4'}`}>
                        <div className="flex-1">
                          <h3 className={`${isMobile ? 'text-lg' : 'text-xl'} font-semibold text-white group-hover:text-cyan-400 transition-colors duration-300 ${isMobile ? 'mb-1' : 'mb-2'}`}>
                            {project.title}
                          </h3>
                          {project.description && (
                            <p className={`text-gray-400 ${isMobile ? 'mb-3 text-sm' : 'mb-4'} line-clamp-3`}>{project.description}</p>
                          )}
                        </div>
                        <button 
                          className="opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                          }}
                        >
                          <Star className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 hover:text-yellow-500`} />
                        </button>
                      </div>
                      
                      {project.technologies && (
                        <div className={`flex flex-wrap ${isMobile ? 'gap-1.5 mb-3' : 'gap-2 mb-4'}`}>
                          {project.technologies.split(',').map((tech, index) => (
                            <span key={index} className={`${isMobile ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-xs'} bg-cyan-600/20 text-cyan-400 rounded-lg`}>
                              {tech.trim()}
                            </span>
                          ))}
                        </div>
                      )}
                      
                      <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-2' : 'justify-between'}`}>
                        <div className={`flex items-center ${isSmallMobile ? 'gap-1' : 'space-x-2'} ${isMobile ? 'text-xs' : 'text-xs'} text-gray-500`}>
                          <Calendar className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`} />
                          <span>{new Date(project.created_at).toLocaleDateString()}</span>
                        </div>
                        <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-2'}`} onClick={(e) => e.stopPropagation()}>
                          <button 
                            onClick={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                              openEditForm(project)
                            }}
                            className={`${isMobile ? 'p-1.5' : 'p-2'} bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 rounded-lg transition-colors duration-300`}
                            title="Edit project"
                          >
                            <Edit className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`} />
                          </button>
                          <button 
                            onClick={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                              openDeleteModal(project)
                            }}
                            className={`${isMobile ? 'p-1.5' : 'p-2'} bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition-colors duration-300`}
                            title="Delete project"
                          >
                            <Trash2 className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`} />
                          </button>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className={`${isMobile ? 'space-y-3' : 'space-y-4'}`}>
                  {projects.map((project) => (
                    <Link 
                      key={project.id} 
                      to={`/projects/${project.id}`}
                      className={`flex items-center ${isSmallMobile ? 'flex-col gap-3' : 'space-x-4'} ${isMobile ? 'p-4' : 'p-6'} bg-gradient-to-r from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-xl hover:border-cyan-500/30 transition-all duration-300 block cursor-pointer`}
                    >
                      <div className={`${isMobile ? 'w-10 h-10' : 'w-12 h-12'} ${isSmallMobile ? 'w-full' : ''} bg-gradient-to-br from-cyan-600/20 to-teal-600/20 rounded-lg flex items-center justify-center`}>
                        <FolderOpen className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} text-cyan-400`} />
                      </div>
                      
                      <div className={`flex-1 ${isSmallMobile ? 'w-full' : ''}`}>
                        <h3 className={`font-semibold text-white ${isMobile ? 'text-sm mb-1' : 'mb-1'}`}>{project.title}</h3>
                        {project.description && (
                          <p className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'} line-clamp-1 ${isMobile ? 'mb-1' : 'mb-2'}`}>{project.description}</p>
                        )}
                        <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-1 items-start' : 'space-x-4'}`}>
                          {project.technologies && (
                            <div className="flex flex-wrap gap-1">
                              {project.technologies.split(',').slice(0, 3).map((tech, index) => (
                                <span key={index} className={`${isMobile ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-xs'} bg-cyan-600/20 text-cyan-400 rounded-lg`}>
                                  {tech.trim()}
                                </span>
                              ))}
                              {project.technologies.split(',').length > 3 && (
                                <span className={`${isMobile ? 'text-xs' : 'text-xs'} text-gray-500`}>+{project.technologies.split(',').length - 3} more</span>
                              )}
                            </div>
                          )}
                          <div className={`flex items-center ${isSmallMobile ? 'gap-1' : 'space-x-1'} ${isMobile ? 'text-xs' : 'text-xs'} text-gray-500`}>
                            <Calendar className={`${isMobile ? 'w-3 h-3' : 'w-3 h-3'}`} />
                            <span>{new Date(project.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className={`flex items-center ${isSmallMobile ? 'w-full justify-center gap-3' : 'space-x-2'}`} onClick={(e) => e.stopPropagation()}>
                        <button 
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                          }}
                        >
                          <Star className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 hover:text-yellow-500`} />
                        </button>
                        <button 
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            openEditForm(project)
                          }}
                        >
                          <Edit className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 hover:text-cyan-400`} />
                        </button>
                        <button 
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            openDeleteModal(project)
                          }}
                        >
                          <Trash2 className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 hover:text-red-400`} />
                        </button>
                        <button 
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                          }}
                        >
                          <MoreHorizontal className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 hover:text-white`} />
                        </button>
                      </div>
                    </Link>
                  ))}
                </div>
              )
            ) : (
              <div className={`text-center ${isMobile ? 'py-12' : 'py-16'} bg-gradient-to-br from-gray-900/30 to-black/30 rounded-2xl border border-gray-800`}>
                <div className={`${isMobile ? 'p-4' : 'p-6'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 rounded-full ${isMobile ? 'w-16 h-16' : 'w-24 h-24'} mx-auto ${isMobile ? 'mb-4' : 'mb-6'}`}>
                  <FolderOpen className={`${isMobile ? 'w-8 h-8' : 'w-12 h-12'} text-cyan-400 mx-auto ${isMobile ? 'mt-2' : 'mt-3'}`} />
                </div>
                <h3 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-semibold text-white ${isMobile ? 'mb-3' : 'mb-4'}`}>No projects yet</h3>
                <p className={`text-gray-400 ${isMobile ? 'mb-6 text-base' : 'mb-8'} max-w-md mx-auto`}>Create your first project to start organizing your bookmarks and development tasks efficiently.</p>
                <button 
                  onClick={() => setShowCreateForm(true)}
                  className={`bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-6 py-3 text-sm' : 'px-8 py-4'} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 flex items-center ${isSmallMobile ? 'justify-center w-full' : 'space-x-3'} mx-auto`}
                >
                  <Plus className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'}`} />
                  <span>{isSmallMobile ? 'Create Project' : 'Create Your First Project'}</span>
                </button>
              </div>
            )}
          </main>
        </div>
      </div>

      {/* Create Project Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50" onClick={closeForms}>
          <div className={`bg-gradient-to-br from-gray-900/90 to-black/90 backdrop-blur-xl border border-gray-700 rounded-2xl ${isMobile ? 'p-4 max-w-sm' : 'p-8 max-w-md'} w-full shadow-2xl`} onClick={(e) => e.stopPropagation()}>
            <div className={`flex items-center justify-between ${isMobile ? 'mb-4' : 'mb-6'}`}>
              <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-3'}`}>
                <div className={`${isMobile ? 'p-1.5' : 'p-2'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 rounded-lg`}>
                  <Plus className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} text-cyan-400`} />
                </div>
                <h2 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold text-white`}>Create New Project</h2>
              </div>
              <button 
                onClick={closeForms}
                className="text-gray-400 hover:text-white transition-colors duration-300 p-2 hover:bg-gray-800 rounded-lg"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <form onSubmit={handleCreateProject} className={`${isMobile ? 'space-y-4' : 'space-y-6'}`}>
              <div>
                <label htmlFor="create-title" className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-medium text-gray-300 ${isMobile ? 'mb-1' : 'mb-2'}`}>Project Title</label>
                <input
                  type="text"
                  id="create-title"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  required
                  placeholder="Enter project title"
                  className={`w-full ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300`}
                />
              </div>
              
              <div>
                <label htmlFor="create-description" className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-medium text-gray-300 ${isMobile ? 'mb-1' : 'mb-2'}`}>Description</label>
                <textarea
                  id="create-description"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  required
                  placeholder="Describe your project"
                  rows="3"
                  className={`w-full ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300 resize-none`}
                />
              </div>
              
              <div>
                <label htmlFor="create-technologies" className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-medium text-gray-300 ${isMobile ? 'mb-1' : 'mb-2'}`}>Technologies</label>
                <input
                  type="text"
                  id="create-technologies"
                  value={formData.technologies}
                  onChange={(e) => setFormData({...formData, technologies: e.target.value})}
                  placeholder="e.g., React, Python, PostgreSQL"
                  className={`w-full ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300`}
                />
              </div>

              {/* Tasks Section */}
              <div className={`border-t border-gray-700 ${isMobile ? 'pt-4' : 'pt-6'}`}>
                <div className={`flex items-center justify-between ${isMobile ? 'mb-3' : 'mb-4'}`}>
                  <h3 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold text-white flex items-center ${isSmallMobile ? 'gap-1' : 'gap-2'}`}>
                    <CheckSquare className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400`} />
                    Tasks (Optional)
                  </h3>
                  <button
                    type="button"
                    onClick={() => setShowTasksSection(!showTasksSection)}
                    className={`text-cyan-400 hover:text-cyan-300 ${isMobile ? 'text-xs' : 'text-sm'} font-medium`}
                  >
                    {showTasksSection ? 'Hide' : 'Add Tasks'}
                  </button>
                </div>

                {showTasksSection && (
                  <div className={`${isMobile ? 'space-y-3' : 'space-y-4'}`}>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newTaskTitle}
                        onChange={(e) => setNewTaskTitle(e.target.value)}
                        placeholder="Task title"
                        className={`flex-1 ${isMobile ? 'px-3 py-1.5 text-sm' : 'px-4 py-2'} bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300`}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault()
                            addTask()
                          }
                        }}
                      />
                      <button
                        type="button"
                        onClick={addTask}
                        className={`${isMobile ? 'px-3 py-1.5' : 'px-4 py-2'} bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg transition-colors duration-300`}
                      >
                        <Plus className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                      </button>
                    </div>
                    {newTaskDescription && (
                      <textarea
                        value={newTaskDescription}
                        onChange={(e) => setNewTaskDescription(e.target.value)}
                        placeholder="Task description (optional)"
                        rows="2"
                        className={`w-full ${isMobile ? 'px-3 py-1.5 text-sm' : 'px-4 py-2'} bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300 resize-none`}
                      />
                    )}

                    {tasks.length > 0 && (
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {tasks.map((task, index) => (
                          <div key={index} className="flex items-start gap-2 p-3 bg-gray-800/30 rounded-lg border border-gray-700">
                            <div className="flex-1">
                              <p className="text-white font-medium text-sm">{task.title}</p>
                              {task.description && (
                                <p className="text-gray-400 text-xs mt-1">{task.description}</p>
                              )}
                            </div>
                            <button
                              type="button"
                              onClick={() => removeTask(index)}
                              className="p-1 text-red-400 hover:text-red-300 transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-2' : 'space-x-4'} ${isMobile ? 'pt-3' : 'pt-4'}`}>
                <button 
                  type="button" 
                  onClick={closeForms}
                  disabled={isCreating}
                  className={`flex-1 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} border border-gray-600 rounded-xl hover:border-gray-500 hover:bg-gray-800/50 transition-all duration-300 text-gray-300 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={isCreating}
                  className={`flex-1 bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center ${isSmallMobile ? 'gap-1' : 'gap-2'}`}
                >
                  {isCreating ? (
                    <>
                      <Loader2 className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} animate-spin`} />
                      Creating...
                    </>
                  ) : (
                    'Create Project'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Project Modal */}
      {showEditForm && editingProject && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50" onClick={closeForms}>
          <div className={`bg-gradient-to-br from-gray-900/90 to-black/90 backdrop-blur-xl border border-gray-700 rounded-2xl ${isMobile ? 'p-4 max-w-sm' : 'p-8 max-w-md'} w-full shadow-2xl`} onClick={(e) => e.stopPropagation()}>
            <div className={`flex items-center justify-between ${isMobile ? 'mb-4' : 'mb-6'}`}>
              <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-3'}`}>
                <div className={`${isMobile ? 'p-1.5' : 'p-2'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 rounded-lg`}>
                  <Edit className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} text-cyan-400`} />
                </div>
                <h2 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold text-white`}>Edit Project</h2>
              </div>
              <button 
                onClick={closeForms}
                className="text-gray-400 hover:text-white transition-colors duration-300 p-2 hover:bg-gray-800 rounded-lg"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <form onSubmit={handleEditProject} className="space-y-6">
              <div>
                <label htmlFor="edit-title" className="block text-sm font-medium text-gray-300 mb-2">Project Title</label>
                <input
                  type="text"
                  id="edit-title"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  required
                  placeholder="Enter project title"
                  className={`w-full ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300`}
                />
              </div>
              
              <div>
                <label htmlFor="edit-description" className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-medium text-gray-300 ${isMobile ? 'mb-1' : 'mb-2'}`}>Description</label>
                <textarea
                  id="edit-description"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  required
                  placeholder="Describe your project"
                  rows="3"
                  className={`w-full ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300 resize-none`}
                />
              </div>
              
              <div>
                <label htmlFor="edit-technologies" className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-medium text-gray-300 ${isMobile ? 'mb-1' : 'mb-2'}`}>Technologies</label>
                <input
                  type="text"
                  id="edit-technologies"
                  value={formData.technologies}
                  onChange={(e) => setFormData({...formData, technologies: e.target.value})}
                  placeholder="e.g., React, Python, PostgreSQL"
                  className={`w-full ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300`}
                />
              </div>

              {/* Tasks Section */}
              <div className={`border-t border-gray-700 ${isMobile ? 'pt-4' : 'pt-6'}`}>
                <div className={`flex items-center justify-between ${isMobile ? 'mb-3' : 'mb-4'}`}>
                  <h3 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold text-white flex items-center ${isSmallMobile ? 'gap-1' : 'gap-2'}`}>
                    <CheckSquare className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400`} />
                    Tasks (Optional)
                  </h3>
                  <button
                    type="button"
                    onClick={() => setShowTasksSection(!showTasksSection)}
                    className={`text-cyan-400 hover:text-cyan-300 ${isMobile ? 'text-xs' : 'text-sm'} font-medium`}
                  >
                    {showTasksSection ? 'Hide' : 'Add Tasks'}
                  </button>
                </div>

                {showTasksSection && (
                  <div className={`${isMobile ? 'space-y-3' : 'space-y-4'}`}>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newTaskTitle}
                        onChange={(e) => setNewTaskTitle(e.target.value)}
                        placeholder="Task title"
                        className={`flex-1 ${isMobile ? 'px-3 py-1.5 text-sm' : 'px-4 py-2'} bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300`}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault()
                            addTask()
                          }
                        }}
                      />
                      <button
                        type="button"
                        onClick={addTask}
                        className={`${isMobile ? 'px-3 py-1.5' : 'px-4 py-2'} bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg transition-colors duration-300`}
                      >
                        <Plus className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                      </button>
                    </div>
                    {newTaskDescription && (
                      <textarea
                        value={newTaskDescription}
                        onChange={(e) => setNewTaskDescription(e.target.value)}
                        placeholder="Task description (optional)"
                        rows="2"
                        className={`w-full ${isMobile ? 'px-3 py-1.5 text-sm' : 'px-4 py-2'} bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300 resize-none`}
                      />
                    )}

                    {tasks.length > 0 && (
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {tasks.map((task, index) => (
                          <div key={index} className="flex items-start gap-2 p-3 bg-gray-800/30 rounded-lg border border-gray-700">
                            <div className="flex-1">
                              <p className="text-white font-medium text-sm">{task.title}</p>
                              {task.description && (
                                <p className="text-gray-400 text-xs mt-1">{task.description}</p>
                              )}
                            </div>
                            <button
                              type="button"
                              onClick={() => removeTask(index)}
                              className="p-1 text-red-400 hover:text-red-300 transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-2' : 'space-x-4'} ${isMobile ? 'pt-3' : 'pt-4'}`}>
                <button 
                  type="button" 
                  onClick={closeForms}
                  disabled={isUpdating}
                  className={`flex-1 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} border border-gray-600 rounded-xl hover:border-gray-500 hover:bg-gray-800/50 transition-all duration-300 text-gray-300 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={isUpdating}
                  className={`flex-1 bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center ${isSmallMobile ? 'gap-1' : 'gap-2'}`}
                >
                  {isUpdating ? (
                    <>
                      <Loader2 className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} animate-spin`} />
                      Updating...
                    </>
                  ) : (
                    'Update Project'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && deletingProject && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50" onClick={closeForms}>
          <div className={`bg-gradient-to-br from-gray-900/90 to-black/90 backdrop-blur-xl border border-gray-700 rounded-2xl ${isMobile ? 'p-4 max-w-sm' : 'p-8 max-w-md'} w-full shadow-2xl`} onClick={(e) => e.stopPropagation()}>
            <div className="text-center">
              <div className={`${isMobile ? 'p-3' : 'p-4'} bg-gradient-to-r from-red-600/20 to-orange-600/20 rounded-full ${isMobile ? 'w-16 h-16' : 'w-20 h-20'} mx-auto ${isMobile ? 'mb-4' : 'mb-6'}`}>
                <Trash2 className={`${isMobile ? 'w-8 h-8' : 'w-12 h-12'} text-red-400 mx-auto ${isMobile ? 'mt-1.5' : 'mt-2'}`} />
              </div>
              
              <h2 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold text-white ${isMobile ? 'mb-3' : 'mb-4'}`}>Delete Project</h2>
              <h3 className={`${isMobile ? 'text-lg' : 'text-xl'} font-semibold text-gray-300 ${isMobile ? 'mb-1' : 'mb-2'}`}>Are you sure you want to delete this project?</h3>
              <p className={`text-red-400 font-medium ${isMobile ? 'text-base mb-3' : 'text-lg mb-4'}`}>"{deletingProject.title}"</p>
              <p className={`text-gray-400 ${isMobile ? 'mb-6 text-sm' : 'mb-8'}`}>
                This action cannot be undone. All project data will be permanently removed from your account.
              </p>
              
              <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-2' : 'space-x-4'}`}>
                <button 
                  type="button" 
                  onClick={closeForms}
                  className={`flex-1 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} border border-gray-600 rounded-xl hover:border-gray-500 hover:bg-gray-800/50 transition-all duration-300 text-gray-300 hover:text-white`}
                >
                  Cancel
                </button>
                <button 
                  type="button" 
                  onClick={handleDeleteProject}
                  disabled={isDeleting}
                  className={`flex-1 bg-gradient-to-r from-red-600 to-orange-600 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} rounded-xl font-semibold hover:shadow-lg hover:shadow-red-500/25 transition-all duration-300 transform hover:scale-105 text-white disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center ${isSmallMobile ? 'gap-1' : 'gap-2'}`}
                >
                  {isDeleting ? (
                    <>
                      <Loader2 className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} animate-spin`} />
                      Deleting...
                    </>
                  ) : (
                    'Delete Project'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Custom Styles */}
      <style jsx>{`
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
        
        .line-clamp-3 {
          display: -webkit-box;
          -webkit-line-clamp: 3;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  )
}

export default Projects