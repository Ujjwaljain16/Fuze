import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { Bookmark, FolderOpen, Plus, ExternalLink, Calendar, Sparkles, Lightbulb } from 'lucide-react'

const Dashboard = () => {
  const { isAuthenticated } = useAuth()
  const [stats, setStats] = useState({
    bookmarks: 0,
    projects: 0
  })
  const [recentBookmarks, setRecentBookmarks] = useState([])
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
        api.get('/api/recommendations/general') // New endpoint for general recommendations
      ])

      setRecentBookmarks(bookmarksRes.data.bookmarks || [])
      setStats({
        bookmarks: bookmarksRes.data.total || 0,
        projects: projectsRes.data.projects?.length || 0
      })
      setRecommendations(recommendationsRes.data.recommendations || [])
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
      // If recommendations fail, just continue without them
      setRecommendations([])
    } finally {
      setLoading(false)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="dashboard-container">
        <div className="welcome-card">
          <h1>Welcome to Fuze</h1>
          <p>Your intelligent bookmark manager with semantic search and Chrome extension integration.</p>
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
        <div className="loading">Loading dashboard...</div>
      </div>
    )
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <p>Welcome back! Here's what's happening with your bookmarks.</p>
      </div>

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
        {/* Recommendations Section */}
        {recommendations.length > 0 && (
          <div className="section">
            <div className="section-header">
              <h2>
                <Sparkles className="section-icon" />
                AI Recommendations
              </h2>
              <p className="section-subtitle">Content suggestions based on your interests</p>
            </div>
            
            <div className="recommendations-grid">
              {recommendations.slice(0, 3).map((rec) => (
                <div key={rec.id} className="recommendation-card">
                  <div className="recommendation-header">
                    <Lightbulb className="recommendation-icon" />
                    <span className="recommendation-score">Match: {rec.score}%</span>
                  </div>
                  <h4>{rec.title}</h4>
                  <p className="recommendation-url">{rec.url}</p>
                  {rec.description && (
                    <p className="recommendation-description">{rec.description}</p>
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
          </div>
        )}

        {/* Recent Bookmarks Section */}
        <div className="section">
          <div className="section-header">
            <h2>Recent Bookmarks</h2>
            <button className="add-button">
              <Plus size={16} />
              Add Bookmark
            </button>
          </div>
          
          {recentBookmarks.length > 0 ? (
            <div className="bookmarks-list">
              {recentBookmarks.map((bookmark) => (
                <div key={bookmark.id} className="bookmark-item">
                  <div className="bookmark-content">
                    <h4>{bookmark.title}</h4>
                    <p className="bookmark-url">{bookmark.url}</p>
                    {bookmark.description && (
                      <p className="bookmark-description">{bookmark.description}</p>
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
              <p>No bookmarks yet. Start by adding your first bookmark!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Dashboard 