import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { Sparkles, Lightbulb, ExternalLink, Bookmark, ThumbsUp, ThumbsDown, Filter, RefreshCw } from 'lucide-react'

const Recommendations = () => {
  const { isAuthenticated } = useAuth()
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (isAuthenticated) {
      fetchRecommendations()
    }
  }, [isAuthenticated])

  const fetchRecommendations = async () => {
    try {
      setLoading(true)
      const endpoint = filter === 'all' 
        ? '/api/recommendations/general'
        : `/api/recommendations/project/${filter}`
      
      const response = await api.get(endpoint)
      setRecommendations(response.data.recommendations || [])
    } catch (error) {
      console.error('Error fetching recommendations:', error)
      setRecommendations([])
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchRecommendations()
    setRefreshing(false)
  }

  const handleFeedback = async (recommendationId, feedbackType) => {
    try {
      await api.post('/api/recommendations/feedback', {
        content_id: recommendationId,
        feedback_type: feedbackType
      })
      // Optionally refresh recommendations after feedback
      // fetchRecommendations()
    } catch (error) {
      console.error('Error submitting feedback:', error)
    }
  }

  const handleSaveRecommendation = async (recommendation) => {
    try {
      await api.post('/api/bookmarks', {
        url: recommendation.url,
        title: recommendation.title,
        description: recommendation.description || '',
        category: 'recommended'
      })
      // Remove from recommendations list
      setRecommendations(prev => prev.filter(rec => rec.id !== recommendation.id))
    } catch (error) {
      console.error('Error saving recommendation:', error)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="recommendations-container">
        <div className="auth-required">
          <h2>Authentication Required</h2>
          <p>Please log in to view your personalized recommendations.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="recommendations-container">
      <div className="recommendations-header">
        <div className="header-content">
          <h1>
            <Sparkles className="header-icon" />
            AI Recommendations
          </h1>
          <p>Discover content tailored to your interests and projects</p>
        </div>
        <button 
          onClick={handleRefresh}
          disabled={refreshing}
          className="refresh-button"
        >
          <RefreshCw size={16} className={refreshing ? 'spinning' : ''} />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div className="recommendations-controls">
        <div className="filter-controls">
          <Filter size={16} />
          <select 
            value={filter} 
            onChange={(e) => setFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Recommendations</option>
            <option value="general">General</option>
            {/* You can add project-specific filters here */}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="loading">
          <Sparkles className="loading-icon" />
          <p>Finding the best content for you...</p>
        </div>
      ) : recommendations.length > 0 ? (
        <div className="recommendations-grid">
          {recommendations.map((rec) => (
            <div key={rec.id} className="recommendation-card">
              <div className="recommendation-header">
                <div className="recommendation-meta">
                  <Lightbulb className="recommendation-icon" />
                  <span className="recommendation-score">Match: {rec.score || 'High'}%</span>
                </div>
                <div className="recommendation-actions">
                  <button 
                    onClick={() => handleFeedback(rec.id, 'relevant')}
                    className="feedback-button positive"
                    title="This is relevant"
                  >
                    <ThumbsUp size={16} />
                  </button>
                  <button 
                    onClick={() => handleFeedback(rec.id, 'not_relevant')}
                    className="feedback-button negative"
                    title="This is not relevant"
                  >
                    <ThumbsDown size={16} />
                  </button>
                </div>
              </div>
              
              <h3 className="recommendation-title">{rec.title}</h3>
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
                  Save to Bookmarks
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <Sparkles className="empty-icon" />
          <h3>No recommendations yet</h3>
          <p>
            {filter === 'all' 
              ? 'Start by adding some bookmarks and projects to get personalized recommendations.'
              : 'No recommendations found for this filter. Try refreshing or changing the filter.'
            }
          </p>
          <button onClick={handleRefresh} className="refresh-button">
            <RefreshCw size={16} />
            Refresh Recommendations
          </button>
        </div>
      )}
    </div>
  )
}

export default Recommendations 