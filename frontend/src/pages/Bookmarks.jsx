import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { Bookmark, Search, Plus, ExternalLink, Trash2, Filter, Sparkles } from 'lucide-react'
import './bookmarks-styles.css'
import Select from 'react-select'

const categoryOptions = [
  { value: 'all', label: 'All Categories' },
  { value: 'work', label: 'Work' },
  { value: 'personal', label: 'Personal' },
  { value: 'research', label: 'Research' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'other', label: 'Other' },
]

const Bookmarks = () => {
  const { isAuthenticated } = useAuth()
  const [bookmarks, setBookmarks] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [filter, setFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [semanticQuery, setSemanticQuery] = useState('')
  const [semanticResults, setSemanticResults] = useState([])
  const [semanticLoading, setSemanticLoading] = useState(false)
  const [semanticError, setSemanticError] = useState('')

  useEffect(() => {
    if (isAuthenticated) {
      fetchBookmarks()
    }
  }, [isAuthenticated, page, searchTerm, filter])

  const fetchBookmarks = async () => {
    try {
      setLoading(true)
      const params = {
        page,
        per_page: 10,
        ...(searchTerm && { search: searchTerm }),
        ...(filter !== 'all' && { category: filter })
      }
      
      const response = await api.get('/api/bookmarks', { params })
      setBookmarks(response.data.bookmarks || [])
      setTotalPages(response.data.pages || 1)
    } catch (error) {
      console.error('Error fetching bookmarks:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (bookmarkId) => {
    if (window.confirm('Are you sure you want to delete this bookmark?')) {
      try {
        await api.delete(`/api/bookmarks/${bookmarkId}`)
        fetchBookmarks() // Refresh the list
      } catch (error) {
        console.error('Error deleting bookmark:', error)
      }
    }
  }

  const handleDeleteAll = async () => {
    if (bookmarks.length === 0) return;
    if (window.confirm('Are you sure you want to delete ALL your bookmarks? This cannot be undone.')) {
      try {
        await api.delete('/api/bookmarks/all')
        setPage(1)
        fetchBookmarks()
      } catch (error) {
        console.error('Error deleting all bookmarks:', error)
      }
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1) // Reset to first page when searching
    fetchBookmarks()
  }

  const handleSemanticSearch = async (e) => {
    e.preventDefault()
    setSemanticLoading(true)
    setSemanticError('')
    setSemanticResults([])
    try {
      const response = await api.post('/api/search/supabase-semantic', {
        query: semanticQuery,
        limit: 8
      })
      setSemanticResults(response.data.results || [])
    } catch (error) {
      setSemanticError('Semantic search failed. Try again.')
      setSemanticResults([])
    } finally {
      setSemanticLoading(false)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="bookmarks-container">
        <div className="auth-required">
          <h2>Authentication Required</h2>
          <p>Please log in to view your bookmarks.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bookmarks-container">
      {/* Semantic Search UI */}
      <div className="semantic-search-section">
        <form onSubmit={handleSemanticSearch} className="semantic-search-form">
          <Sparkles size={24} className="semantic-search-icon" />
          <input
            type="text"
            placeholder="Semantic search (e.g. 'OAuth2 login flow', 'React hooks best practices')..."
            value={semanticQuery}
            onChange={e => setSemanticQuery(e.target.value)}
            className="semantic-search-input"
            aria-label="Semantic search bookmarks"
          />
          <button type="submit" className="semantic-search-button" disabled={semanticLoading || !semanticQuery.trim()}>
            {semanticLoading ? 'Searching...' : 'Semantic Search'}
          </button>
        </form>
        {semanticError && <div className="semantic-search-error">{semanticError}</div>}
        {semanticLoading && <div className="semantic-search-loading">Finding the most relevant bookmarks...</div>}
        {!semanticLoading && semanticResults.length > 0 && (
          <div className="semantic-results-grid">
            {semanticResults.map((result, idx) => (
              <div key={result.id || idx} className="semantic-result-card">
                <div className="semantic-result-header">
                  <Sparkles size={18} className="semantic-result-icon" />
                  <span className="semantic-result-score">Relevance: {result.distance ? (100 - Math.round(result.distance * 100)).toString() + '%' : 'High'}</span>
                </div>
                <h3 className="semantic-result-title">{result.title}</h3>
                <p className="semantic-result-url">{result.url}</p>
                {result.content_snippet && <p className="semantic-result-snippet">{result.content_snippet}</p>}
                <div className="semantic-result-footer">
                  <a href={result.url} target="_blank" rel="noopener noreferrer" className="semantic-result-link">
                    <ExternalLink size={16} /> View Content
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
        {!semanticLoading && semanticResults.length === 0 && semanticQuery && !semanticError && (
          <div className="semantic-search-empty">No semantically relevant bookmarks found.</div>
        )}
      </div>
      <div className="bookmarks-header">
        <h1>My Bookmarks</h1>
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="add-button" aria-label="Add Bookmark" title="Add Bookmark">
            <Plus size={16} />
            Add Bookmark
          </button>
          <button
            className="delete-all-button"
            aria-label="Delete All Bookmarks"
            title="Delete All Bookmarks"
            onClick={handleDeleteAll}
            disabled={bookmarks.length === 0}
            style={{ background: '#e53e3e', color: '#fff', borderRadius: 8, padding: '0 16px', fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6, opacity: bookmarks.length === 0 ? 0.6 : 1, cursor: bookmarks.length === 0 ? 'not-allowed' : 'pointer' }}
          >
            <Trash2 size={16} />
            Delete All
          </button>
        </div>
      </div>

      <div className="bookmarks-controls">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input">
            <Search size={20} />
            <input
              type="text"
              placeholder="Search bookmarks..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              aria-label="Search bookmarks"
            />
          </div>
          <button type="submit" className="search-button" aria-label="Search Bookmarks">
            Search
          </button>
        </form>

        <div className="filter-controls">
          <Filter size={16} />
          <div style={{ minWidth: 180, flex: 1 }}>
            <Select
              classNamePrefix="react-select"
              className="filter-select"
              value={categoryOptions.find(opt => opt.value === filter)}
              onChange={option => setFilter(option.value)}
              options={categoryOptions}
              isSearchable={false}
              inputId="bookmark-category-filter"
              aria-label="Filter by category"
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
        <div className="loading">Loading bookmarks...</div>
      ) : bookmarks.length > 0 ? (
        <>
          <div className="bookmarks-grid">
            {bookmarks.map((bookmark) => (
              <div key={bookmark.id} className="bookmark-card">
                <div className="bookmark-header">
                  <h3>{bookmark.title}</h3>
                  <div className="bookmark-actions">
                    <a 
                      href={bookmark.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="action-button"
                      title="Open link"
                      aria-label={`Open ${bookmark.title}`}
                    >
                      <ExternalLink size={16} />
                    </a>
                    <button 
                      onClick={() => handleDelete(bookmark.id)}
                      className="action-button delete"
                      title="Delete bookmark"
                      aria-label={`Delete ${bookmark.title}`}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
                
                <p className="bookmark-url">{bookmark.url}</p>
                
                {bookmark.description && (
                  <p className="bookmark-description">{bookmark.description}</p>
                )}
                
                <div className="bookmark-meta">
                  <span className="bookmark-date">
                    {new Date(bookmark.saved_at).toLocaleDateString()}
                  </span>
                  {bookmark.category && (
                    <span className="bookmark-category">{bookmark.category}</span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button 
                onClick={() => setPage(page - 1)} 
                disabled={page === 1}
                className="pagination-button"
              >
                Previous
              </button>
              <span className="pagination-info">
                Page {page} of {totalPages}
              </span>
              <button 
                onClick={() => setPage(page + 1)} 
                disabled={page === totalPages}
                className="pagination-button"
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="empty-state">
          <Bookmark className="empty-icon" />
          <h3>No bookmarks found</h3>
          <p>
            {searchTerm || filter !== 'all' 
              ? 'Try adjusting your search or filter criteria.'
              : 'Start by adding your first bookmark using the Chrome extension or the add button above.'
            }
          </p>
        </div>
      )}
    </div>
  )
}

export default Bookmarks 