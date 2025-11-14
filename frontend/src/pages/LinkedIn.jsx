import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import api from '../services/api'
import { 
  Linkedin, ExternalLink, Download, Trash2, RefreshCw, 
  Search, Filter, Clock, CheckCircle, AlertCircle, Plus,
  Sparkles, Link as LinkIcon, FileText, TrendingUp
} from 'lucide-react'

const LinkedIn = () => {
  const { isAuthenticated } = useAuth()
  const { showToast } = useToast()
  const [linkedinUrl, setLinkedinUrl] = useState('')
  const [extracting, setExtracting] = useState(false)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')

  useEffect(() => {
    if (isAuthenticated) {
      fetchHistory()
    }
  }, [isAuthenticated])

  const fetchHistory = async () => {
    try {
      setLoading(true)
      const response = await api.get('/api/linkedin/history')
      if (response.data.success) {
        setHistory(response.data.data || [])
      }
    } catch (error) {
      console.error('Failed to fetch LinkedIn history:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleExtract = async (e) => {
    e.preventDefault()
    
    if (!linkedinUrl.trim()) {
      showToast('Please enter a LinkedIn URL', 'error')
      return
    }

    if (!linkedinUrl.includes('linkedin.com')) {
      showToast('Please enter a valid LinkedIn URL', 'error')
      return
    }

    try {
      setExtracting(true)
      const response = await api.post('/api/linkedin/extract', {
        url: linkedinUrl
      })

      if (response.data.success) {
        showToast('LinkedIn content extracted successfully! 🎉', 'success')
        setLinkedinUrl('')
        fetchHistory()
      } else {
        showToast(response.data.error || 'Failed to extract content', 'error')
      }
    } catch (error) {
      console.error('LinkedIn extraction error:', error)
      showToast(error.response?.data?.error || 'Failed to extract LinkedIn content', 'error')
    } finally {
      setExtracting(false)
    }
  }

  const handleSaveToBookmarks = async (item) => {
    try {
      const response = await api.post('/api/linkedin/save-to-bookmarks', {
        extraction_id: item.id
      })

      if (response.data.success) {
        showToast('Saved to bookmarks! 📚', 'success')
        fetchHistory()
      }
    } catch (error) {
      showToast('Failed to save to bookmarks', 'error')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this LinkedIn extraction?')) return

    try {
      await api.delete(`/api/linkedin/extract/${id}`)
      showToast('Deleted successfully', 'success')
      fetchHistory()
    } catch (error) {
      showToast('Failed to delete', 'error')
    }
  }

  const filteredHistory = history
    .filter(item => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        return (
          item.title?.toLowerCase().includes(query) ||
          item.content?.toLowerCase().includes(query) ||
          item.url?.toLowerCase().includes(query)
        )
      }
      return true
    })
    .filter(item => {
      if (filterStatus === 'saved') return item.saved_to_bookmarks
      if (filterStatus === 'unsaved') return !item.saved_to_bookmarks
      return true
    })

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center p-4">
        <div className="text-center">
          <Linkedin className="w-16 h-16 text-blue-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">LinkedIn Integration</h2>
          <p className="text-gray-300">Please login to use this feature</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-3 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg">
              <Linkedin className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-white">LinkedIn Integration</h1>
              <p className="text-gray-300">Extract and save content from LinkedIn posts</p>
            </div>
          </div>
        </div>

        {/* Extract Form */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 mb-6 border border-white/20">
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-yellow-400" />
            Extract LinkedIn Post
          </h2>
          <form onSubmit={handleExtract} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-200 mb-2">
                LinkedIn Post URL
              </label>
              <div className="flex gap-3">
                <div className="flex-1 relative">
                  <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="url"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                    placeholder="https://www.linkedin.com/posts/..."
                    className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={extracting}
                  />
                </div>
                <button
                  type="submit"
                  disabled={extracting}
                  className="px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl font-semibold hover:from-blue-600 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {extracting ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Extracting...
                    </>
                  ) : (
                    <>
                      <Download className="w-5 h-5" />
                      Extract
                    </>
                  )}
                </button>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                💡 Paste any LinkedIn post URL to extract its content, technologies, and insights
              </p>
            </div>
          </form>
        </div>

        {/* Search and Filter */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-4 mb-6 border border-white/20">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search extractions..."
                  className="w-full pl-10 pr-4 py-2 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setFilterStatus('all')}
                className={`px-4 py-2 rounded-xl font-medium transition-all ${
                  filterStatus === 'all'
                    ? 'bg-blue-500 text-white'
                    : 'bg-white/10 text-gray-300 hover:bg-white/20'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilterStatus('saved')}
                className={`px-4 py-2 rounded-xl font-medium transition-all ${
                  filterStatus === 'saved'
                    ? 'bg-green-500 text-white'
                    : 'bg-white/10 text-gray-300 hover:bg-white/20'
                }`}
              >
                Saved
              </button>
              <button
                onClick={() => setFilterStatus('unsaved')}
                className={`px-4 py-2 rounded-xl font-medium transition-all ${
                  filterStatus === 'unsaved'
                    ? 'bg-orange-500 text-white'
                    : 'bg-white/10 text-gray-300 hover:bg-white/20'
                }`}
              >
                Unsaved
              </button>
            </div>
            <button
              onClick={fetchHistory}
              className="px-4 py-2 bg-white/10 text-gray-300 rounded-xl hover:bg-white/20 transition-all"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* History */}
        {loading ? (
          <div className="text-center py-12">
            <RefreshCw className="w-12 h-12 text-blue-400 animate-spin mx-auto mb-4" />
            <p className="text-gray-300">Loading history...</p>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-12 text-center border border-white/20">
            <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">
              {searchQuery || filterStatus !== 'all' ? 'No results found' : 'No extractions yet'}
            </h3>
            <p className="text-gray-400">
              {searchQuery || filterStatus !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Start by extracting content from a LinkedIn post'}
            </p>
          </div>
        ) : (
          <div className="grid gap-6">
            {filteredHistory.map((item) => (
              <div
                key={item.id}
                className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20 hover:border-blue-500/50 transition-all"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-white mb-2 flex items-center gap-2">
                      {item.title || 'Untitled Post'}
                      {item.saved_to_bookmarks && (
                        <span className="px-2 py-1 bg-green-500/20 text-green-300 text-xs rounded-lg">
                          Saved
                        </span>
                      )}
                    </h3>
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1 mb-2"
                    >
                      <ExternalLink className="w-4 h-4" />
                      View original post
                    </a>
                  </div>
                  <div className="flex gap-2">
                    {!item.saved_to_bookmarks && (
                      <button
                        onClick={() => handleSaveToBookmarks(item)}
                        className="p-2 bg-green-500/20 text-green-300 rounded-lg hover:bg-green-500/30 transition-all"
                        title="Save to bookmarks"
                      >
                        <Plus className="w-5 h-5" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="p-2 bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/30 transition-all"
                      title="Delete"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {item.content && (
                  <p className="text-gray-300 mb-4 line-clamp-3">{item.content}</p>
                )}

                {item.technology_tags && item.technology_tags.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {item.technology_tags.map((tech, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-lg text-sm"
                      >
                        {tech}
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex items-center gap-4 text-sm text-gray-400">
                  <div className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {new Date(item.extracted_at).toLocaleDateString()}
                  </div>
                  {item.quality_score && (
                    <div className="flex items-center gap-1">
                      <TrendingUp className="w-4 h-4" />
                      Quality: {item.quality_score}/10
                    </div>
                  )}
                  {item.extraction_method && (
                    <div className="flex items-center gap-1">
                      <Sparkles className="w-4 h-4" />
                      {item.extraction_method}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default LinkedIn

