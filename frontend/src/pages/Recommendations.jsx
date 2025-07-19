import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { Sparkles, Lightbulb, ExternalLink, Bookmark, ThumbsUp, ThumbsDown, Filter, RefreshCw } from 'lucide-react'
import './recommendations-styles.css'
import Select from 'react-select'

const Recommendations = () => {
  const { isAuthenticated } = useAuth()
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [refreshing, setRefreshing] = useState(false)
  const [projects, setProjects] = useState([])
  const [filterOptions, setFilterOptions] = useState([
    { value: 'all', label: 'All Recommendations' },
    { value: 'general', label: 'General' }
  ])

  useEffect(() => {
    if (isAuthenticated) {
      fetchProjects()
      fetchRecommendations()
    }
  }, [isAuthenticated])

  useEffect(() => {
    if (isAuthenticated && filter) {
      fetchRecommendations()
    }
  }, [filter])

  const fetchProjects = async () => {
    try {
      const response = await api.get('/api/projects')
      const userProjects = response.data.projects || []
      setProjects(userProjects)
      
      // Update filter options to include projects
      const projectOptions = userProjects.map(project => ({
        value: project.id.toString(),
        label: `Project: ${project.title}`
      }))
      
      setFilterOptions([
        { value: 'all', label: 'All Recommendations' },
        { value: 'general', label: 'General' },
        ...projectOptions
      ])
    } catch (error) {
      console.error('Error fetching projects:', error)
    }
  }

  const fetchRecommendations = async () => {
    try {
      setLoading(true)
      let endpoint
      if (filter === 'all' || filter === 'general') {
        endpoint = '/api/recommendations/general'
      } else {
        // For project-specific recommendations
        endpoint = `/api/recommendations/project/${filter}`
      }
      
      const response = await api.get(endpoint)
      // Handle different response formats
      const recommendations = response.data.recommendations || response.data || []
      setRecommendations(recommendations)
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
            <RecommendationCard key={rec.id} recommendation={rec} />
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

const RecommendationCard = ({ recommendation }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="recommendation-card">
      <div className="recommendation-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="recommendation-title">
          <h3>{recommendation.title}</h3>
          {recommendation.score && (
            <span className="score-badge">
              {Math.round(recommendation.score)}/100
            </span>
          )}
        </div>
        <div className="recommendation-meta">
          <span className="reason">{recommendation.reason}</span>
          <button className="expand-btn">
            {isExpanded ? '▼' : '▶'}
          </button>
        </div>
      </div>
      
      {isExpanded && recommendation.analysis && (
        <div className="ai-analysis">
          <h4>AI Analysis</h4>
          <div className="score-breakdown">
            <div className="score-item">
              <span>Technology Match:</span>
              <div className="score-bar">
                <div 
                  className="score-fill" 
                  style={{width: `${(recommendation.analysis.tech_score/30)*100}%`}}
                ></div>
                <span>{Math.round(recommendation.analysis.tech_score)}/30</span>
              </div>
            </div>
            <div className="score-item">
              <span>Content Relevance:</span>
              <div className="score-bar">
                <div 
                  className="score-fill" 
                  style={{width: `${(recommendation.analysis.content_score/20)*100}%`}}
                ></div>
                <span>{Math.round(recommendation.analysis.content_score)}/20</span>
              </div>
            </div>
            <div className="score-item">
              <span>Difficulty Match:</span>
              <div className="score-bar">
                <div 
                  className="score-fill" 
                  style={{width: `${(recommendation.analysis.difficulty_score/15)*100}%`}}
                ></div>
                <span>{Math.round(recommendation.analysis.difficulty_score)}/15</span>
              </div>
            </div>
            <div className="score-item">
              <span>Intent Alignment:</span>
              <div className="score-bar">
                <div 
                  className="score-fill" 
                  style={{width: `${(recommendation.analysis.intent_score/15)*100}%`}}
                ></div>
                <span>{Math.round(recommendation.analysis.intent_score)}/15</span>
              </div>
            </div>
            <div className="score-item">
              <span>Semantic Similarity:</span>
              <div className="score-bar">
                <div 
                  className="score-fill" 
                  style={{width: `${(recommendation.analysis.semantic_score/20)*100}%`}}
                ></div>
                <span>{Math.round(recommendation.analysis.semantic_score)}/20</span>
              </div>
            </div>
          </div>
          
          <div className="content-details">
            <div className="detail-item">
              <strong>Technologies:</strong> 
              {recommendation.analysis.technologies.length > 0 
                ? recommendation.analysis.technologies.join(', ') 
                : 'None detected'
              }
            </div>
            <div className="detail-item">
              <strong>Content Type:</strong> {recommendation.analysis.content_type}
            </div>
            <div className="detail-item">
              <strong>Difficulty:</strong> {recommendation.analysis.difficulty}
            </div>
            <div className="detail-item">
              <strong>Intent:</strong> {recommendation.analysis.intent}
            </div>
          </div>
        </div>
      )}
      
      <div className="recommendation-actions">
        <a 
          href={recommendation.url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="visit-btn"
        >
          Visit Link
        </a>
        {recommendation.notes && (
          <div className="notes">
            <strong>Notes:</strong> {recommendation.notes}
          </div>
        )}
      </div>
    </div>
  );
};

export default Recommendations 