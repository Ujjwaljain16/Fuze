import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { FolderOpen, Plus, Edit, Trash2, Calendar } from 'lucide-react'
import './projects-styles.css'

const Projects = () => {
  const { isAuthenticated } = useAuth()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [showEditForm, setShowEditForm] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [editingProject, setEditingProject] = useState(null)
  const [deletingProject, setDeletingProject] = useState(null)
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

  const handleEditProject = async (e) => {
    e.preventDefault()
    try {
      await api.put(`/api/projects/${editingProject.id}`, formData)
      setFormData({ title: '', description: '', technologies: '' })
      setShowEditForm(false)
      setEditingProject(null)
      fetchProjects()
    } catch (error) {
      console.error('Error updating project:', error)
    }
  }

  const handleDeleteProject = async () => {
    try {
      await api.delete(`/api/projects/${deletingProject.id}`)
      setShowDeleteModal(false)
      setDeletingProject(null)
      fetchProjects()
    } catch (error) {
      console.error('Error deleting project:', error)
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

      {/* Create Project Modal */}
      {showCreateForm && (
        <div className="modal-overlay" onClick={closeForms}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Create New Project</h2>
              <button 
                onClick={closeForms}
                className="close-button"
              >
                ×
              </button>
            </div>
            <form onSubmit={handleCreateProject} className="project-form">
              <div className="form-group">
                <label htmlFor="create-title">Project Title</label>
                <input
                  type="text"
                  id="create-title"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  required
                  placeholder="Enter project title"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="create-description">Description</label>
                <textarea
                  id="create-description"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  required
                  placeholder="Describe your project"
                  rows="3"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="create-technologies">Technologies</label>
                <input
                  type="text"
                  id="create-technologies"
                  value={formData.technologies}
                  onChange={(e) => setFormData({...formData, technologies: e.target.value})}
                  placeholder="e.g., React, Python, PostgreSQL"
                />
              </div>
              
              <div className="form-actions">
                <button type="button" onClick={closeForms}>
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

      {/* Edit Project Modal */}
      {showEditForm && editingProject && (
        <div className="modal-overlay" onClick={closeForms}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Edit Project</h2>
              <button 
                onClick={closeForms}
                className="close-button"
              >
                ×
              </button>
            </div>
            <form onSubmit={handleEditProject} className="project-form">
              <div className="form-group">
                <label htmlFor="edit-title">Project Title</label>
                <input
                  type="text"
                  id="edit-title"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  required
                  placeholder="Enter project title"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="edit-description">Description</label>
                <textarea
                  id="edit-description"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  required
                  placeholder="Describe your project"
                  rows="3"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="edit-technologies">Technologies</label>
                <input
                  type="text"
                  id="edit-technologies"
                  value={formData.technologies}
                  onChange={(e) => setFormData({...formData, technologies: e.target.value})}
                  placeholder="e.g., React, Python, PostgreSQL"
                />
              </div>
              
              <div className="form-actions">
                <button type="button" onClick={closeForms}>
                  Cancel
                </button>
                <button type="submit" className="primary">
                  Update Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && deletingProject && (
        <div className="modal-overlay" onClick={closeForms}>
          <div className="modal delete-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Delete Project</h2>
              <button 
                onClick={closeForms}
                className="close-button"
              >
                ×
              </button>
            </div>
            <div className="delete-modal-content">
              <div className="delete-icon">
                <Trash2 size={48} />
              </div>
              <h3>Are you sure you want to delete this project?</h3>
              <p className="delete-project-name">"{deletingProject.title}"</p>
              <p className="delete-warning">
                This action cannot be undone. All project data will be permanently removed.
              </p>
              <div className="form-actions">
                <button type="button" onClick={closeForms}>
                  Cancel
                </button>
                <button 
                  type="button" 
                  className="delete-btn"
                  onClick={handleDeleteProject}
                >
                  Delete Project
                </button>
              </div>
            </div>
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
                  <button 
                    className="action-button" 
                    title="Edit project"
                    onClick={() => openEditForm(project)}
                  >
                    <Edit size={16} />
                  </button>
                  <button 
                    onClick={() => openDeleteModal(project)}
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