import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { Bookmark, FolderOpen, Plus, ExternalLink, Calendar, Sparkles, Lightbulb, Search, Settings, User } from 'lucide-react'

const Dashboard = () => {
  const { isAuthenticated, user } = useAuth()
  const [stats, setStats] = useState({
    bookmarks: 0,
    projects: 0
  })
  const [recentBookmarks, setRecentBookmarks] = useState([])
  const [recentProjects, setRecentProjects] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isAuthenticated) {
      fetchDashboardData()
    }
  }, [isAuthenticated])

  const fetchDashboardData = async () => {
    try {
      const [bookmarksRes, projectsRes, recommendationsRes] = await Promise.all([
        api.get('/api/bookmarks?per_page=5'),
        api.get('/api/projects'),
        api.get('/api/recommendations/general')
      ])

      setRecentBookmarks(bookmarksRes.data.bookmarks || [])
      setRecentProjects(projectsRes.data.projects?.slice(0, 3) || [])
      setStats({
        bookmarks: bookmarksRes.data.total || 0,
        projects: projectsRes.data.projects?.length || 0
      })
      setRecommendations(recommendationsRes.data.recommendations || [])
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
      setRecommendations([])
    } finally {
      setLoading(false)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="dashboard-container">
        <div className="welcome-card">
          <div className="welcome-header">
            <Bookmark className="welcome-logo" />
            <h1>Welcome to Fuze</h1>
          </div>
          <p className="welcome-subtitle">Your intelligent bookmark manager with semantic search and Chrome extension integration.</p>
          
          <div className="feature-grid">
            <div className="feature-card">
              <Bookmark className="feature-icon" />
              <h3>Smart Bookmarks</h3>
              <p>Save and organize web content with intelligent categorization</p>
            </div>
            <div className="feature-card">
              <FolderOpen className="feature-icon" />
              <h3>Project Organization</h3>
              <p>Group bookmarks by projects and tasks for better workflow</p>
            </div>
            <div className="feature-card">
              <ExternalLink className="feature-icon" />
              <h3>Chrome Extension</h3>
              <p>One-click bookmarking from any webpage with auto-sync</p>
            </div>
            <div className="feature-card">
              <Sparkles className="feature-icon" />
              <h3>AI Recommendations</h3>
              <p>Get intelligent content suggestions based on your interests</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="loading">
          <Sparkles className="loading-icon" />
          <p>Loading your dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard-container">
      {/* Welcome Header */}
      <div className="dashboard-header">
        <div className="welcome-section">
          <h1>Welcome back, {user?.username || 'User'}!</h1>
          <p>Here's what's happening with your bookmarks and projects.</p>
        </div>
        
        {/* Quick Actions */}
        <div className="quick-actions">
          <button className="quick-action-btn primary">
            <Plus size={16} />
            <span>Save New Content</span>
          </button>
          <button className="quick-action-btn secondary">
            <FolderOpen size={16} />
            <span>Create Project</span>
          </button>
          <button className="quick-action-btn secondary">
            <ExternalLink size={16} />
            <span>Install Extension</span>
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">
            <Bookmark />
          </div>
          <div className="stat-content">
            <h3>{stats.bookmarks}</h3>
            <p>Total Bookmarks</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">
            <FolderOpen />
          </div>
          <div className="stat-content">
            <h3>{stats.projects}</h3>
            <p>Active Projects</p>
          </div>
        </div>
      </div>

      <div className="dashboard-sections">
        {/* AI Recommendations Section */}
        {recommendations.length > 0 && (
          <div className="section recommendations-section">
            <div className="section-header">
              <div className="section-title">
                <Sparkles className="section-icon" />
                <h2>Intelligent Recommendations</h2>
              </div>
              <p className="section-subtitle">Content suggestions powered by AI, tailored to your interests</p>
            </div>
            
            <div className="recommendations-grid">
              {recommendations.slice(0, 3).map((rec) => (
                <div key={rec.id} className="recommendation-card">
                  <div className="recommendation-header">
                    <Lightbulb className="recommendation-icon" />
                    <span className="recommendation-score">Match: {rec.score}%</span>
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
                  <div className="recommendation-actions">
                    <a 
                      href={rec.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="recommendation-link"
                    >
                      <ExternalLink size={16} />
                      View Content
                    </a>
                    <button className="save-recommendation-btn">
                      <Bookmark size={16} />
                      Save
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="section-footer">
              <a href="/recommendations" className="view-all-link">
                View All Recommendations
                <ExternalLink size={16} />
              </a>
            </div>
          </div>
        )}

        {/* Recent Projects Section */}
        <div className="section">
          <div className="section-header">
            <div className="section-title">
              <FolderOpen className="section-icon" />
              <h2>Recent Projects</h2>
            </div>
            <a href="/projects" className="view-all-link">View All Projects</a>
          </div>
          
          {recentProjects.length > 0 ? (
            <div className="projects-grid">
              {recentProjects.map((project) => (
                <div key={project.id} className="project-card">
                  <div className="project-content">
                    <h4 className="project-title">{project.title}</h4>
                    {project.description && (
                      <p className="project-description">{project.description}</p>
                    )}
                    {project.technologies && (
                      <div className="project-technologies">
                        {project.technologies.split(',').map((tech, index) => (
                          <span key={index} className="tech-tag">{tech.trim()}</span>
                        ))}
                      </div>
                    )}
                    <div className="project-meta">
                      <Calendar size={14} />
                      <span>Updated {new Date(project.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="project-actions">
                    <a 
                      href={`/projects/${project.id}`}
                      className="project-link"
                    >
                      <ExternalLink size={16} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <FolderOpen className="empty-icon" />
              <h3>No projects yet</h3>
              <p>Create your first project to start organizing your bookmarks and tasks.</p>
              <button className="create-project-btn">
                <Plus size={16} />
                Create Project
              </button>
            </div>
          )}
        </div>

        {/* Recent Bookmarks Section */}
        <div className="section">
          <div className="section-header">
            <div className="section-title">
              <Bookmark className="section-icon" />
              <h2>Recent Bookmarks</h2>
            </div>
            <a href="/bookmarks" className="view-all-link">View All Bookmarks</a>
          </div>
          
          {recentBookmarks.length > 0 ? (
            <div className="bookmarks-list">
              {recentBookmarks.map((bookmark) => (
                <div key={bookmark.id} className="bookmark-item">
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
              <h3>No bookmarks yet</h3>
              <p>Start by adding your first bookmark using the Chrome extension or web form.</p>
              <button className="save-content-btn">
                <Plus size={16} />
                Save New Content
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Dashboard 