import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import api from '../services/api'
import { Bookmark, ExternalLink, Loader2, Plus, Tag } from 'lucide-react'

const SaveContent = () => {
  const { isAuthenticated } = useAuth()
  const { success, error } = useToast()
  const [loading, setLoading] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [projects, setProjects] = useState([])
  const [formData, setFormData] = useState({
    url: '',
    title: '',
    description: '',
    category: 'other',
    tags: '',
    project_id: ''
  })

  // Fetch projects on component mount
  useState(() => {
    if (isAuthenticated) {
      fetchProjects()
    }
  }, [isAuthenticated])

  const fetchProjects = async () => {
    try {
      const response = await api.get('/api/projects')
      setProjects(response.data.projects || [])
    } catch (err) {
      console.error('Error fetching projects:', err)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const extractUrlData = async () => {
    if (!formData.url) {
      error('Please enter a URL first')
      return
    }

    setExtracting(true)
    try {
      // This would call your backend endpoint for URL extraction
      // For now, we'll simulate it
      const response = await api.post('/api/extract-url', { url: formData.url })
      
      if (response.data) {
        setFormData(prev => ({
          ...prev,
          title: response.data.title || prev.title,
          description: response.data.description || prev.description
        }))
        success('URL data extracted successfully!')
      }
    } catch (err) {
      console.error('Error extracting URL data:', err)
      error('Failed to extract URL data. Please fill in manually.')
    } finally {
      setExtracting(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!formData.url.trim()) {
      error('URL is required')
      return
    }

    setLoading(true)
    try {
      const bookmarkData = {
        url: formData.url.trim(),
        title: formData.title.trim() || 'Untitled Bookmark',
        description: formData.description.trim(),
        category: formData.category,
        tags: formData.tags.trim()
      }

      const response = await api.post('/api/bookmarks', bookmarkData)
      
      if (response.data) {
        success('Content saved successfully!')
        // Reset form
        setFormData({
          url: '',
          title: '',
          description: '',
          category: 'other',
          tags: '',
          project_id: ''
        })
      }
    } catch (err) {
      console.error('Error saving content:', err)
      if (err.response?.data?.message) {
        error(err.response.data.message)
      } else {
        error('Failed to save content. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="container">
        <div className="auth-required">
          <h2>Authentication Required</h2>
          <p>Please log in to save content.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="page-header">
        <div className="page-title">
          <Bookmark className="page-icon" />
          <h1>Save New Content</h1>
        </div>
        <p className="page-subtitle">
          Save web content to your Fuze library with intelligent categorization
        </p>
      </div>

      <div className="save-content-form">
        <form onSubmit={handleSubmit} className="form">
          {/* URL Input */}
          <div className="form-group">
            <label htmlFor="url" className="form-label">
              URL <span className="required">*</span>
            </label>
            <div className="url-input-group">
              <input
                type="url"
                id="url"
                name="url"
                value={formData.url}
                onChange={handleInputChange}
                placeholder="https://example.com/article"
                className="form-input"
                required
              />
              <button
                type="button"
                onClick={extractUrlData}
                disabled={extracting || !formData.url}
                className="btn btn-secondary extract-btn"
              >
                {extracting ? (
                  <Loader2 size={16} className="spinning" />
                ) : (
                  <ExternalLink size={16} />
                )}
                {extracting ? 'Extracting...' : 'Extract'}
              </button>
            </div>
          </div>

          {/* Title Input */}
          <div className="form-group">
            <label htmlFor="title" className="form-label">
              Title
            </label>
            <input
              type="text"
              id="title"
              name="title"
              value={formData.title}
              onChange={handleInputChange}
              placeholder="Enter title or leave blank for auto-extraction"
              className="form-input"
            />
          </div>

          {/* Description Input */}
          <div className="form-group">
            <label htmlFor="description" className="form-label">
              Notes
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              placeholder="Add your notes or description..."
              className="form-input form-textarea"
              rows={4}
            />
          </div>

          {/* Category and Tags Row */}
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="category" className="form-label">
                Category
              </label>
              <select
                id="category"
                name="category"
                value={formData.category}
                onChange={handleInputChange}
                className="form-input form-select"
              >
                <option value="other">Other</option>
                <option value="technology">Technology</option>
                <option value="programming">Programming</option>
                <option value="design">Design</option>
                <option value="business">Business</option>
                <option value="education">Education</option>
                <option value="news">News</option>
                <option value="tutorial">Tutorial</option>
                <option value="research">Research</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="tags" className="form-label">
                Tags
              </label>
              <div className="tags-input-group">
                <Tag size={16} className="tags-icon" />
                <input
                  type="text"
                  id="tags"
                  name="tags"
                  value={formData.tags}
                  onChange={handleInputChange}
                  placeholder="react, javascript, tutorial"
                  className="form-input"
                />
              </div>
              <small className="form-help">
                Separate tags with commas
              </small>
            </div>
          </div>

          {/* Project Association */}
          {projects.length > 0 && (
            <div className="form-group">
              <label htmlFor="project_id" className="form-label">
                Associate with Project (Optional)
              </label>
              <select
                id="project_id"
                name="project_id"
                value={formData.project_id}
                onChange={handleInputChange}
                className="form-input form-select"
              >
                <option value="">No Project</option>
                {projects.map(project => (
                  <option key={project.id} value={project.id}>
                    {project.title}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Submit Button */}
          <div className="form-actions">
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary btn-lg"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="spinning" />
                  Saving...
                </>
              ) : (
                <>
                  <Bookmark size={16} />
                  Save Content
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Tips Section */}
      <div className="tips-section">
        <h3>💡 Tips for Better Organization</h3>
        <ul className="tips-list">
          <li>Use descriptive titles to make content easier to find</li>
          <li>Add relevant tags to group similar content together</li>
          <li>Associate content with projects for better organization</li>
          <li>Use the Chrome extension for one-click saving</li>
        </ul>
      </div>
    </div>
  )
}

export default SaveContent 