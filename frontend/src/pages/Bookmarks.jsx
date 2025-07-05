import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import api from '../services/api'
import { Bookmark, Search, Plus, ExternalLink, Trash2, Filter } from 'lucide-react'

const Bookmarks = () => {
  const { isAuthenticated } = useAuth()
  const [bookmarks, setBookmarks] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [filter, setFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

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

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1) // Reset to first page when searching
    fetchBookmarks()
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
      <div className="bookmarks-header">
        <h1>My Bookmarks</h1>
        <button className="add-button">
          <Plus size={16} />
          Add Bookmark
        </button>
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
            />
          </div>
          <button type="submit" className="search-button">
            Search
          </button>
        </form>

        <div className="filter-controls">
          <Filter size={16} />
          <select 
            value={filter} 
            onChange={(e) => setFilter(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Categories</option>
            <option value="work">Work</option>
            <option value="personal">Personal</option>
            <option value="research">Research</option>
            <option value="entertainment">Entertainment</option>
            <option value="other">Other</option>
          </select>
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
                    >
                      <ExternalLink size={16} />
                    </a>
                    <button 
                      onClick={() => handleDelete(bookmark.id)}
                      className="action-button delete"
                      title="Delete bookmark"
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