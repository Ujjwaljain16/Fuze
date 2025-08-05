import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import api from '../services/api'
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
  Tag
} from 'lucide-react'

const ProjectDetail = () => {
  const { id } = useParams()
  const { isAuthenticated } = useAuth()
  const { success, error } = useToast()
  const [project, setProject] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [projectBookmarks, setProjectBookmarks] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (isAuthenticated && id) {
      fetchProjectData()
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
    <div className="container">
      {/* Project Header */}
      <div className="project-header">
        <div className="project-info">
          <div className="project-title-section">
            <FolderOpen className="project-icon" />
            <div>
              <h1 className="project-title">{project.title}</h1>
              {project.description && (
                <p className="project-description">{project.description}</p>
              )}
            </div>
          </div>
          
          {project.technologies && (
            <div className="project-technologies">
              {project.technologies.split(',').map((tech, index) => (
                <span key={index} className="tech-tag">
                  {tech.trim()}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="project-actions">
          <button className="btn btn-secondary">
            <Edit size={16} />
            Edit Project
          </button>
          <button className="btn btn-primary">
            <Plus size={16} />
            Add Content
          </button>
        </div>
      </div>

      <div className="project-content">
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
    </div>
  )
}

export default ProjectDetail 