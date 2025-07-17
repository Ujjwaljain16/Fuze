import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { Sparkles, Lightbulb, ExternalLink, Bookmark, ThumbsUp, ThumbsDown, Filter, RefreshCw } from 'lucide-react'
import './recommendations-styles.css'
import Select from 'react-select'

const filterOptions = [
  { value: 'all', label: 'All Recommendations' },
  { value: 'general', label: 'General' },
  // Add more project-specific options here if needed
]

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
  }, [isAuthenticated, filter])

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
          aria-label="Refresh Recommendations"
          title="Refresh Recommendations"
        >
          <RefreshCw size={16} className={refreshing ? 'spinning' : ''} />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div className="recommendations-controls">
        <div className="filter-controls">
          <Filter size={16} />
          <div style={{ minWidth: 180, flex: 1 }}>
            <Select
              classNamePrefix="react-select"
              className="filter-select"
              value={filterOptions.find(opt => opt.value === filter)}
              onChange={option => setFilter(option.value)}
              options={filterOptions}
              isSearchable={false}
              inputId="recommendations-filter"
              aria-label="Filter recommendations"
              styles={{
                control: (base, state) => ({
                  ...base,
                  background: 'rgba(30,32,48,0.9)',
                  borderColor: state.isFocused ? '#667eea' : 'rgba(255,255,255,0.1)',
                  color: '#fff',
                  borderRadius: 8,
                  minHeight: 40,
                  boxShadow: state.isFocused ? '0 0 0 3px rgba(102,126,234,0.1)' : 'none',
                  fontWeight: 500,
                  fontSize: 14,
                  cursor: 'pointer',
                }),
                singleValue: base => ({ ...base, color: '#fff' }),
                menu: base => ({ ...base, background: '#232136', color: '#fff', borderRadius: 8, zIndex: 20 }),
                option: (base, state) => ({
                  ...base,
                  background: state.isFocused ? 'rgba(102,126,234,0.15)' : 'transparent',
                  color: '#fff',
                  cursor: 'pointer',
                }),
                dropdownIndicator: base => ({ ...base, color: '#aaa' }),
                indicatorSeparator: base => ({ ...base, display: 'none' }),
                input: base => ({ ...base, color: '#fff' }),
              }}
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="loading">
          <Sparkles className="loading-icon" aria-label="Loading recommendations" />
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
                    title="Mark as relevant"
                    aria-label={`Mark ${rec.title} as relevant`}
                  >
                    <ThumbsUp size={16} />
                  </button>
                  <button 
                    onClick={() => handleFeedback(rec.id, 'not_relevant')}
                    className="feedback-button negative"
                    title="Mark as not relevant"
                    aria-label={`Mark ${rec.title} as not relevant`}
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
                  aria-label={`Open ${rec.title}`}
                  title="Open link"
                >
                  <ExternalLink size={16} />
                  View Content
                </a>
                <button 
                  onClick={() => handleSaveRecommendation(rec)}
                  className="save-recommendation-btn"
                  aria-label={`Save ${rec.title} to bookmarks`}
                  title="Save to Bookmarks"
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
          <Sparkles className="empty-icon" aria-label="No recommendations found" />
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