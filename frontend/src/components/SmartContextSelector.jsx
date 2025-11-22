import React, { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import api from '../services/api'
import {
  Search, FolderOpen, CheckSquare, Clock, Sparkles,
  Globe, X, ChevronDown, ChevronRight, Zap, Target
} from 'lucide-react'

// Context caching utility
const CONTEXT_CACHE_KEY = 'fuze_context_data'
const CACHE_DURATION = 10 * 60 * 1000 // 10 minutes in milliseconds

const getCachedContextData = () => {
  try {
    const cached = localStorage.getItem(CONTEXT_CACHE_KEY)
    if (!cached) return null

    const data = JSON.parse(cached)
    const now = Date.now()

    // Check if cache is expired
    if (now - data.timestamp > CACHE_DURATION) {
      localStorage.removeItem(CONTEXT_CACHE_KEY)
      return null
    }

    return data.contextData
  } catch (error) {
    console.warn('Error reading context cache:', error)
    localStorage.removeItem(CONTEXT_CACHE_KEY)
    return null
  }
}

const setCachedContextData = (contextData) => {
  try {
    const cacheData = {
      contextData,
      timestamp: Date.now()
    }
    localStorage.setItem(CONTEXT_CACHE_KEY, JSON.stringify(cacheData))
  } catch (error) {
    console.warn('Error caching context data:', error)
  }
}

const clearContextCache = () => {
  localStorage.removeItem(CONTEXT_CACHE_KEY)
}

// Make cache clearing available globally for cache invalidation
window.clearContextCache = clearContextCache

// Add a global function to clear ALL recommendation caches (both client and server)
window.clearAllRecommendationCaches = async () => {
  try {
    // Clear client-side cache
    clearContextCache()

    // Clear server-side caches (this will clear both Redis recommendation and context caches)
    const response = await api.post('/api/recommendations/cache/clear-all-recommendations')
    console.log('All recommendation caches cleared:', response.data)
    return response.data
  } catch (error) {
    console.error('Failed to clear all recommendation caches:', error)
    throw error
  }
}

const SmartContextSelector = ({ onSelect, onClose }) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [recentItems, setRecentItems] = useState([])
  const [suggestedContexts, setSuggestedContexts] = useState([])
  const [allProjects, setAllProjects] = useState([])
  const [expandedProjects, setExpandedProjects] = useState(new Set())
  const [expandedTasks, setExpandedTasks] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [showAllProjects, setShowAllProjects] = useState(false)
  const searchInputRef = useRef(null)

  useEffect(() => {
    fetchContextData()
    // Auto-focus search input
    setTimeout(() => searchInputRef.current?.focus(), 100)
    
    // Lock body scroll when modal is open
    document.body.style.overflow = 'hidden'
    
    return () => {
      // Unlock body scroll when modal closes
      document.body.style.overflow = 'unset'
    }
  }, [])

  const fetchContextData = async () => {
    try {
      setLoading(true)

      // Check for cached data first
      const cachedData = getCachedContextData()
      if (cachedData) {
        console.log('📋 Using cached context data (10min TTL)')
        setSuggestedContexts(cachedData.suggestedContexts || [])
        setRecentItems(cachedData.recentItems || [])
        setAllProjects(cachedData.allProjects || [])
        setLoading(false)
        return
      }

      console.log('Fetching fresh context data from server...')
      const startTime = Date.now()

      let fetchedSuggestedContexts = []
      let fetchedRecentItems = []
      let fetchedProjects = []

      // Fetch suggested contexts (recent activity)
      try {
        const suggestedRes = await api.get('/api/recommendations/suggested-contexts')
        if (suggestedRes.data.success) {
          fetchedSuggestedContexts = suggestedRes.data.contexts || []
          setSuggestedContexts(fetchedSuggestedContexts)
        }
      } catch {
        console.log('Suggested contexts not available, using fallback')
      }

      // Fetch recent items
      const recentRes = await api.get('/api/recommendations/recent-contexts')
      if (recentRes.data.success) {
        fetchedRecentItems = recentRes.data.recent || []
        setRecentItems(fetchedRecentItems)
      }

      // Fetch all projects with tasks and subtasks
      const projectsRes = await api.get('/api/projects?include_tasks=true')
      fetchedProjects = projectsRes.data.projects || []
      setAllProjects(fetchedProjects)

      // Cache the fetched data
      const contextData = {
        suggestedContexts: fetchedSuggestedContexts,
        recentItems: fetchedRecentItems,
        allProjects: fetchedProjects
      }
      setCachedContextData(contextData)

      const fetchTime = Date.now() - startTime
      console.log(`Context data cached (${fetchTime}ms fetch time)`)

    } catch (error) {
      console.error('Failed to fetch context data:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleProject = (projectId) => {
    const newExpanded = new Set(expandedProjects)
    if (newExpanded.has(projectId)) {
      newExpanded.delete(projectId)
    } else {
      newExpanded.add(projectId)
    }
    setExpandedProjects(newExpanded)
  }

  const toggleTask = (taskId) => {
    const newExpanded = new Set(expandedTasks)
    if (newExpanded.has(taskId)) {
      newExpanded.delete(taskId)
    } else {
      newExpanded.add(taskId)
    }
    setExpandedTasks(newExpanded)
  }

  const handleSelectContext = (context) => {
    onSelect(context)
    onClose()
  }

  const handleSelectQuickOption = (type) => {
    if (type === 'general') {
      onSelect({ type: 'general', title: 'General Recommendations' })
    } else if (type === 'surprise') {
      onSelect({ type: 'surprise', title: 'Surprise Me!' })
    }
    onClose()
  }

  const filterItems = (items) => {
    if (!searchQuery) return items
    const query = searchQuery.toLowerCase()
    return items.filter(item => 
      item.title?.toLowerCase().includes(query) ||
      item.description?.toLowerCase().includes(query) ||
      item.technologies?.toLowerCase().includes(query)
    )
  }

  const filteredProjects = filterItems(allProjects)
  const filteredRecent = filterItems(recentItems)

  const modalContent = (
    <>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from { 
            opacity: 0;
            transform: translateY(20px) scale(0.95);
          }
          to { 
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 1rem;
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          animation: fadeIn 0.2s ease-out;
        }
        .modal-content {
          animation: slideUp 0.3s ease-out;
        }
      `}</style>
      <div 
        className="modal-overlay"
        style={{ 
          background: 'rgba(0, 0, 0, 0.85)'
        }}
        onClick={onClose}
      >
        <div 
          className="modal-content relative w-full max-w-3xl max-h-[85vh] overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
            borderRadius: '24px',
            border: '1px solid rgba(139, 92, 246, 0.3)',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(139, 92, 246, 0.1)'
          }}
          onClick={(e) => e.stopPropagation()}
        >
        {/* Header */}
        <div style={{ padding: '24px 24px 16px 24px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                padding: '10px',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Target size={24} />
              </div>
              Get Recommendations
            </h2>
            <button
              onClick={onClose}
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                border: 'none',
                borderRadius: '10px',
                padding: '8px',
                cursor: 'pointer',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <X size={20} />
            </button>
          </div>

          {/* Search Bar */}
          <div style={{ position: 'relative' }}>
            <Search 
              size={20} 
              style={{ 
                position: 'absolute', 
                left: '16px', 
                top: '50%', 
                transform: 'translateY(-50%)',
                color: '#9ca3af'
              }} 
            />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search projects, tasks..."
              style={{
                width: '100%',
                padding: '14px 14px 14px 48px',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '2px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '12px',
                color: '#fff',
                fontSize: '15px',
                outline: 'none',
                transition: 'all 0.2s'
              }}
              onFocus={(e) => e.target.style.borderColor = 'rgba(99, 102, 241, 0.5)'}
              onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.1)'}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '4px',
                  cursor: 'pointer',
                  color: '#9ca3af',
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                <X size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div style={{ 
          padding: '16px 24px 24px 24px', 
          maxHeight: 'calc(80vh - 150px)', 
          overflowY: 'auto'
        }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#9ca3af' }}>
              <Sparkles className="animate-pulse" size={32} style={{ margin: '0 auto 12px' }} />
              <p>Loading contexts...</p>
            </div>
          ) : (
            <>
              {/* Smart Suggestions */}
              {!searchQuery && suggestedContexts.length > 0 && (
                <div style={{ marginBottom: '24px' }}>
                  <h3 style={{ 
                    fontSize: '13px', 
                    fontWeight: '600', 
                    color: '#9ca3af', 
                    textTransform: 'uppercase', 
                    letterSpacing: '0.5px',
                    marginBottom: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <Sparkles size={16} />
                    Smart Suggestions
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {suggestedContexts.map((context, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSelectContext(context)}
                        style={{
                          width: '100%',
                          padding: '16px',
                          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)',
                          border: '1px solid rgba(99, 102, 241, 0.3)',
                          borderRadius: '12px',
                          cursor: 'pointer',
                          textAlign: 'left',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%)'
                          e.currentTarget.style.transform = 'translateY(-2px)'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)'
                          e.currentTarget.style.transform = 'translateY(0)'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                          <Zap size={18} style={{ color: '#a78bfa' }} />
                          <span style={{ color: '#fff', fontWeight: '600', fontSize: '15px' }}>
                            Continue: {context.title}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingLeft: '30px' }}>
                          <span style={{ color: '#9ca3af', fontSize: '13px' }}>
                            {context.subtitle || context.description}
                          </span>
                          {context.timeAgo && (
                            <span style={{ 
                              marginLeft: 'auto',
                              padding: '4px 8px',
                              background: 'rgba(255, 255, 255, 0.1)',
                              borderRadius: '6px',
                              fontSize: '12px',
                              color: '#60a5fa'
                            }}>
                              {context.timeAgo}
                            </span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent Items */}
              {!searchQuery && filteredRecent.length > 0 && (
                <div style={{ marginBottom: '24px' }}>
                  <h3 style={{ 
                    fontSize: '13px', 
                    fontWeight: '600', 
                    color: '#9ca3af', 
                    textTransform: 'uppercase', 
                    letterSpacing: '0.5px',
                    marginBottom: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <Clock size={16} />
                    Recent
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {filteredRecent.slice(0, 5).map((item, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSelectContext(item)}
                        style={{
                          width: '100%',
                          padding: '12px 16px',
                          background: 'rgba(255, 255, 255, 0.03)',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          borderRadius: '10px',
                          cursor: 'pointer',
                          textAlign: 'left',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          transition: 'all 0.2s'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)'
                          e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.3)'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'
                          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                        }}
                      >
                        {item.type === 'project' ? (
                          <FolderOpen size={18} style={{ color: '#60a5fa', flexShrink: 0 }} />
                        ) : (
                          <CheckSquare size={18} style={{ color: '#4ade80', flexShrink: 0 }} />
                        )}
                        <span style={{ color: '#fff', fontSize: '14px', flex: 1 }}>
                          {item.title}
                        </span>
                        {item.timeAgo && (
                          <span style={{ color: '#6b7280', fontSize: '12px', flexShrink: 0 }}>
                            {item.timeAgo}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* All Projects (Expandable) */}
              <div style={{ marginBottom: '24px' }}>
                <button
                  onClick={() => setShowAllProjects(!showAllProjects)}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '10px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: showAllProjects ? '12px' : '0',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                >
                  <span style={{ 
                    fontSize: '13px', 
                    fontWeight: '600', 
                    color: '#fff',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <FolderOpen size={16} />
                    Browse All Projects ({filteredProjects.length})
                  </span>
                  {showAllProjects ? <ChevronDown size={20} style={{ color: '#9ca3af' }} /> : <ChevronRight size={20} style={{ color: '#9ca3af' }} />}
                </button>

                {showAllProjects && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', paddingLeft: '12px' }}>
                    {filteredProjects.map((project) => (
                      <div key={project.id}>
                        <button
                          onClick={() => toggleProject(project.id)}
                          style={{
                            width: '100%',
                            padding: '10px 12px',
                            background: 'rgba(255, 255, 255, 0.03)',
                            border: '1px solid rgba(255, 255, 255, 0.08)',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            textAlign: 'left',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            transition: 'all 0.2s'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'}
                        >
                          {expandedProjects.has(project.id) ? (
                            <ChevronDown size={16} style={{ color: '#9ca3af', flexShrink: 0 }} />
                          ) : (
                            <ChevronRight size={16} style={{ color: '#9ca3af', flexShrink: 0 }} />
                          )}
                          <FolderOpen size={16} style={{ color: '#60a5fa', flexShrink: 0 }} />
                          <span style={{ color: '#fff', fontSize: '14px', flex: 1 }}>
                            {project.title}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleSelectContext({ type: 'project', id: project.id, title: project.title, description: project.description, technologies: project.technologies })
                            }}
                            style={{
                              padding: '4px 10px',
                              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                              border: 'none',
                              borderRadius: '6px',
                              color: '#fff',
                              fontSize: '12px',
                              fontWeight: '500',
                              cursor: 'pointer',
                              flexShrink: 0
                            }}
                          >
                            Choose
                          </button>
                        </button>

                        {/* Tasks (when expanded) */}
                        {expandedProjects.has(project.id) && project.tasks && project.tasks.length > 0 && (
                          <div style={{ paddingLeft: '32px', marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {project.tasks.map((task) => {
                              const hasSubtasks = task.subtasks && task.subtasks.length > 0
                              const isTaskExpanded = expandedTasks.has(task.id)
                              
                              return (
                                <div key={task.id}>
                                  <button
                                    onClick={(e) => {
                                      if (hasSubtasks) {
                                        e.stopPropagation()
                                        toggleTask(task.id)
                                      } else {
                                        handleSelectContext({ 
                                          type: 'task', 
                                          id: task.id, 
                                          projectId: project.id,
                                          title: task.title,
                                          description: task.description,
                                          projectTitle: project.title 
                                        })
                                      }
                                    }}
                                    style={{
                                      width: '100%',
                                      padding: '8px 12px',
                                      background: 'rgba(255, 255, 255, 0.02)',
                                      border: '1px solid rgba(255, 255, 255, 0.06)',
                                      borderRadius: '6px',
                                      cursor: 'pointer',
                                      textAlign: 'left',
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '10px',
                                      transition: 'all 0.2s'
                                    }}
                                    onMouseEnter={(e) => {
                                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                                      e.currentTarget.style.borderColor = 'rgba(34, 197, 94, 0.3)'
                                    }}
                                    onMouseLeave={(e) => {
                                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'
                                      e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.06)'
                                    }}
                                  >
                                    {hasSubtasks ? (
                                      isTaskExpanded ? (
                                        <ChevronDown size={14} style={{ color: '#9ca3af', flexShrink: 0 }} />
                                      ) : (
                                        <ChevronRight size={14} style={{ color: '#9ca3af', flexShrink: 0 }} />
                                      )
                                    ) : null}
                                    <CheckSquare size={14} style={{ color: '#4ade80', flexShrink: 0 }} />
                                    <span style={{ color: '#d1d5db', fontSize: '13px', flex: 1 }}>
                                      {task.title}
                                    </span>
                                    {!hasSubtasks && (
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          handleSelectContext({ 
                                            type: 'task', 
                                            id: task.id, 
                                            projectId: project.id,
                                            title: task.title,
                                            description: task.description,
                                            projectTitle: project.title 
                                          })
                                        }}
                                        style={{
                                          padding: '2px 8px',
                                          background: 'rgba(34, 197, 94, 0.2)',
                                          border: '1px solid rgba(34, 197, 94, 0.3)',
                                          borderRadius: '4px',
                                          color: '#4ade80',
                                          fontSize: '11px',
                                          cursor: 'pointer',
                                          flexShrink: 0
                                        }}
                                      >
                                        Choose
                                      </button>
                                    )}
                                  </button>
                                  
                                  {/* Subtasks (when task expanded) */}
                                  {isTaskExpanded && hasSubtasks && (
                                    <div style={{ paddingLeft: '24px', marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          handleSelectContext({ 
                                            type: 'task', 
                                            id: task.id, 
                                            projectId: project.id,
                                            title: task.title,
                                            description: task.description,
                                            projectTitle: project.title 
                                          })
                                        }}
                                        style={{
                                          width: '100%',
                                          padding: '6px 10px',
                                          background: 'rgba(34, 197, 94, 0.1)',
                                          border: '1px solid rgba(34, 197, 94, 0.2)',
                                          borderRadius: '5px',
                                          cursor: 'pointer',
                                          textAlign: 'left',
                                          display: 'flex',
                                          alignItems: 'center',
                                          gap: '8px',
                                          fontSize: '12px',
                                          color: '#4ade80',
                                          marginBottom: '4px'
                                        }}
                                        onMouseEnter={(e) => {
                                          e.currentTarget.style.background = 'rgba(34, 197, 94, 0.15)'
                                        }}
                                        onMouseLeave={(e) => {
                                          e.currentTarget.style.background = 'rgba(34, 197, 94, 0.1)'
                                        }}
                                      >
                                        <CheckSquare size={12} />
                                        <span>Task: {task.title}</span>
                                      </button>
                                      
                                      {task.subtasks.map((subtask) => (
                                        <button
                                          key={subtask.id}
                                          onClick={(e) => {
                                            e.stopPropagation()
                                            handleSelectContext({ 
                                              type: 'subtask', 
                                              id: subtask.id,
                                              taskId: task.id,
                                              projectId: project.id,
                                              title: subtask.title,
                                              description: subtask.description,
                                              taskTitle: task.title,
                                              projectTitle: project.title 
                                            })
                                          }}
                                          style={{
                                            width: '100%',
                                            padding: '6px 10px',
                                            background: 'rgba(255, 255, 255, 0.015)',
                                            border: '1px solid rgba(255, 255, 255, 0.05)',
                                            borderRadius: '5px',
                                            cursor: 'pointer',
                                            textAlign: 'left',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px',
                                            transition: 'all 0.2s'
                                          }}
                                          onMouseEnter={(e) => {
                                            e.currentTarget.style.background = 'rgba(139, 92, 246, 0.1)'
                                            e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.3)'
                                          }}
                                          onMouseLeave={(e) => {
                                            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.015)'
                                            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.05)'
                                          }}
                                        >
                                          <span style={{ color: '#a78bfa', fontSize: '11px' }}>▸</span>
                                          <span style={{ color: '#d1d5db', fontSize: '12px', flex: 1 }}>
                                            {subtask.title}
                                          </span>
                                          {subtask.completed && (
                                            <span style={{ 
                                              fontSize: '10px', 
                                              color: '#6b7280',
                                              textDecoration: 'line-through'
                                            }}>
                                              ✓
                                            </span>
                                          )}
                                        </button>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Quick Options */}
              <div>
                <h3 style={{ 
                  fontSize: '13px', 
                  fontWeight: '600', 
                  color: '#9ca3af', 
                  textTransform: 'uppercase', 
                  letterSpacing: '0.5px',
                  marginBottom: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <Zap size={16} />
                  Quick Options
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <button
                    onClick={() => handleSelectQuickOption('general')}
                    style={{
                      padding: '16px',
                      background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%)',
                      border: '1px solid rgba(59, 130, 246, 0.3)',
                      borderRadius: '12px',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '8px',
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(37, 99, 235, 0.2) 100%)'
                      e.currentTarget.style.transform = 'translateY(-2px)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%)'
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                  >
                    <Globe size={24} style={{ color: '#60a5fa' }} />
                    <span style={{ color: '#fff', fontWeight: '500', fontSize: '14px' }}>
                      General
                    </span>
                  </button>

                  <button
                    onClick={() => handleSelectQuickOption('surprise')}
                    style={{
                      padding: '16px',
                      background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)',
                      border: '1px solid rgba(168, 85, 247, 0.3)',
                      borderRadius: '12px',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '8px',
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%)'
                      e.currentTarget.style.transform = 'translateY(-2px)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)'
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                  >
                    <Sparkles size={24} style={{ color: '#a78bfa' }} />
                    <span style={{ color: '#fff', fontWeight: '500', fontSize: '14px' }}>
                      Surprise Me!
                    </span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
    </>
  )

  // Use React Portal to render modal at document body level
  return typeof window !== 'undefined' && document.body
    ? createPortal(modalContent, document.body)
    : modalContent
}

export default SmartContextSelector

