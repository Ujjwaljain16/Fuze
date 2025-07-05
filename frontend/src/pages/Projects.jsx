import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { FolderOpen, Plus, Edit, Trash2, Calendar } from 'lucide-react'

const Projects = () => {
  const { isAuthenticated } = useAuth()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    technologies: ''
  })

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
    try {
      await api.post('/api/projects', formData)
      setFormData({ title: '', description: '', technologies: '' })
      setShowCreateForm(false)
      fetchProjects()
    } catch (error) {
      console.error('Error creating project:', error)
    }
  }

  const handleDeleteProject = async (projectId) => {
    if (window.confirm('Are you sure you want to delete this project?')) {
      try {
        await api.delete(`/api/projects/${projectId}`)
        fetchProjects()
      } catch (error) {
        console.error('Error deleting project:', error)
      }
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="projects-container">
        <div className="auth-required">
          <h2>Authentication Required</h2>
          <p>Please log in to view your projects.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="projects-container">
      <div className="projects-header">
        <h1>My Projects</h1>
        <button 
          onClick={() => setShowCreateForm(true)}
          className="add-button"
        >
          <Plus size={16} />
          New Project
        </button>
      </div>

      {showCreateForm && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2>Create New Project</h2>
              <button 
                onClick={() => setShowCreateForm(false)}
                className="close-button"
              >
                ×
              </button>
            </div>
            <form onSubmit={handleCreateProject} className="project-form">
              <div className="form-group">
                <label htmlFor="title">Project Title</label>
                <input
                  type="text"
                  id="title"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  required
                  placeholder="Enter project title"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="description">Description</label>
                <textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  required
                  placeholder="Describe your project"
                  rows="3"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="technologies">Technologies</label>
                <input
                  type="text"
                  id="technologies"
                  value={formData.technologies}
                  onChange={(e) => setFormData({...formData, technologies: e.target.value})}
                  placeholder="e.g., React, Python, PostgreSQL"
                />
              </div>
              
              <div className="form-actions">
                <button type="button" onClick={() => setShowCreateForm(false)}>
                  Cancel
                </button>
                <button type="submit" className="primary">
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="loading">Loading projects...</div>
      ) : projects.length > 0 ? (
        <div className="projects-grid">
          {projects.map((project) => (
            <div key={project.id} className="project-card">
              <div className="project-header">
                <h3>{project.title}</h3>
                <div className="project-actions">
                  <button className="action-button" title="Edit project">
                    <Edit size={16} />
                  </button>
                  <button 
                    onClick={() => handleDeleteProject(project.id)}
                    className="action-button delete"
                    title="Delete project"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              
              <p className="project-description">{project.description}</p>
              
              {project.technologies && (
                <div className="project-technologies">
                  <strong>Technologies:</strong> {project.technologies}
                </div>
              )}
              
              <div className="project-meta">
                <span className="project-date">
                  <Calendar size={14} />
                  {new Date(project.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <FolderOpen className="empty-icon" />
          <h3>No projects yet</h3>
          <p>Create your first project to start organizing your bookmarks and tasks.</p>
          <button 
            onClick={() => setShowCreateForm(true)}
            className="add-button"
          >
            <Plus size={16} />
            Create Project
          </button>
        </div>
      )}
    </div>
  )
}

export default Projects 