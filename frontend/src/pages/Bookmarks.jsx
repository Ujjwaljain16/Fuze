import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import logo1 from '../assets/logo1.svg'
import { 
  Bookmark, Search, Plus, ExternalLink, Trash2, Filter, Sparkles, 
  Grid3X3, List, Star, Clock, Globe, MoreHorizontal, Zap, ArrowLeft, ArrowRight, X, LogOut
} from 'lucide-react'

const categoryOptions = [
  { value: 'all', label: 'All Categories' },
  { value: 'work', label: 'Work' },
  { value: 'personal', label: 'Personal' },
  { value: 'research', label: 'Research' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'other', label: 'Other' },
]

const Bookmarks = () => {
  const { isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()
  const [bookmarks, setBookmarks] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [filter, setFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [semanticQuery, setSemanticQuery] = useState('')
  const [semanticResults, setSemanticResults] = useState([])
  const [semanticLoading, setSemanticLoading] = useState(false)
  const [semanticError, setSemanticError] = useState('')
  const [viewMode, setViewMode] = useState('grid')
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)
  const [isSmallMobile, setIsSmallMobile] = useState(window.innerWidth <= 480)

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768)
      setIsSmallMobile(window.innerWidth <= 480)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, []);

  // Debounce search term
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
      // Reset page to 1 when search term changes
      if (searchTerm !== debouncedSearchTerm) {
        setPage(1);
      }
    }, 500); // Wait 500ms after user stops typing

    return () => clearTimeout(timer);
  }, [searchTerm, debouncedSearchTerm]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchBookmarks()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, page, debouncedSearchTerm, filter])

  const fetchBookmarks = async () => {
    try {
      setLoading(true)
      setSearchLoading(true)
      const params = {
        page,
        per_page: 10,
        ...(debouncedSearchTerm && { search: debouncedSearchTerm }),
        ...(filter !== 'all' && { category: filter })
      }
      
      const response = await api.get('/api/bookmarks', { params })
      setBookmarks(response.data.bookmarks || [])
      setTotalPages(response.data.pages || 1)
    } catch (error) {
      console.error('Error fetching bookmarks:', error)
    } finally {
      setLoading(false)
      setSearchLoading(false)
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
      
      // Show fallback message if using fallback search
      if (response.data.source === 'fallback') {
        setSemanticError(`${response.data.message || 'Using fallback search mode'}`)
      }
    } catch {
      setSemanticError('Semantic search failed. Try again.')
      setSemanticResults([])
    } finally {
      setSemanticLoading(false)
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen text-white relative overflow-hidden" style={{ backgroundColor: '#0F0F1E' }}>
        {/* Animated Background */}
        <div className="fixed inset-0 opacity-10">
          <div 
            className="absolute w-96 h-96 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(77, 208, 225, 0.3) 0%, transparent 70%)',
              left: mousePos.x - 192,
              top: mousePos.y - 192,
              transition: 'all 0.3s ease-out'
            }}
          />
        </div>

        {/* Lightning Grid Background */}
        <div className="fixed inset-0 opacity-5">
          <div className="grid grid-cols-24 grid-rows-24 h-full w-full">
            {Array.from({ length: 576 }).map((_, i) => (
              <div
                key={i}
                className="border border-cyan-500/10 animate-pulse"
                style={{
                  animationDelay: `${Math.random() * 5}s`,
                  animationDuration: `${4 + Math.random() * 3}s`
                }}
              />
            ))}
          </div>
        </div>

        <div className="relative z-10 flex items-center justify-center min-h-screen p-8">
          <div className="max-w-2xl mx-auto text-center">
            <div className="mb-8">
              <div className="flex items-center justify-center space-x-3 mb-4">
                <div className="relative">
                  <Bookmark className="w-12 h-12 text-cyan-400" />
                  <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                </div>
                <span className="text-4xl font-bold bg-gradient-to-r from-cyan-400 via-teal-400 to-emerald-400 bg-clip-text text-transparent">
                  Authentication Required
                </span>
              </div>
              <p className="text-xl text-gray-300 mb-8">
                Please log in to view your bookmarks.
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen text-white relative overflow-hidden flex items-center justify-center" style={{ backgroundColor: '#0F0F1E' }}>
        {/* Animated Background */}
        <div className="fixed inset-0 opacity-10">
          <div 
            className="absolute w-96 h-96 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(77, 208, 225, 0.3) 0%, transparent 70%)',
              left: mousePos.x - 192,
              top: mousePos.y - 192,
              transition: 'all 0.3s ease-out'
            }}
          />
        </div>

        <div className="text-center relative z-10">
          <div className="relative mb-4">
            <Bookmark className="w-12 h-12 text-cyan-400 mx-auto animate-spin" />
            <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
          </div>
          <p className="text-xl text-gray-300">Loading your bookmarks...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen text-white relative overflow-hidden" style={{ backgroundColor: '#0F0F1E' }}>
      {/* Animated Background */}
      <div className="fixed inset-0 opacity-10">
        <div 
          className="absolute w-96 h-96 rounded-full"
          style={{
            background: 'radial-gradient(circle, rgba(77, 208, 225, 0.3) 0%, transparent 70%)',
            left: mousePos.x - 192,
            top: mousePos.y - 192,
            transition: 'all 0.3s ease-out'
          }}
        />
      </div>
        
      {/* Lightning Grid Background */}
      <div className="fixed inset-0 opacity-5">
        <div className="grid grid-cols-24 grid-rows-24 h-full w-full">
          {Array.from({ length: 576 }).map((_, i) => (
            <div
              key={i}
              className="border border-cyan-500/10 animate-pulse"
              style={{
                animationDelay: `${Math.random() * 5}s`,
                animationDuration: `${4 + Math.random() * 3}s`
              }}
            />
          ))}
        </div>
      </div>

      <div className="relative z-10">
        {/* Main Content */}
        <div className="w-full">
          <main className={`${isMobile ? 'p-4' : 'p-4 md:p-6 lg:p-8'} max-w-[1600px] mx-auto`} style={{ backgroundColor: '#0F0F1E' }}>
            {/* Header with Logo and Logout */}
            <div className={`flex items-center justify-between ${isMobile ? 'mb-6 pt-2' : 'mb-8 pt-6'} ${isSmallMobile ? 'flex-col gap-4' : ''} ${isMobile ? 'mt-12' : ''}`}>
              {/* Logo - Top Left (Home Link) */}
              <Link
                to="/"
                className="logo-container"
                style={{ 
                  cursor: 'pointer'
                }}
              >
                <img 
                  src={logo1} 
                  alt="FUZE Logo"
                  style={{
                    backgroundColor: 'transparent',
                    mixBlendMode: 'normal'
                  }}
                />
              </Link>

              {/* Logout Button - Top Right */}
              <button
                onClick={() => {
                  logout()
                  navigate('/login')
                }}
                className={`flex items-center gap-2.5 ${isMobile ? 'px-4 py-2' : 'px-5 py-3'} rounded-xl transition-all duration-300 group`}
                style={{
                  background: 'rgba(20, 20, 20, 0.6)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  backdropFilter: 'blur(10px)',
                  color: '#9ca3af'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.5)'
                  e.currentTarget.style.background = 'rgba(30, 20, 20, 0.8)'
                  e.currentTarget.style.color = '#ef4444'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 4px 16px rgba(239, 68, 68, 0.3)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.2)'
                  e.currentTarget.style.background = 'rgba(20, 20, 20, 0.6)'
                  e.currentTarget.style.color = '#9ca3af'
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <LogOut className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} group-hover:translate-x-1 transition-transform duration-300`} />
                {!isSmallMobile && <span className={`${isMobile ? 'text-sm' : 'text-base'} font-medium`}>Logout</span>}
              </button>
            </div>
          {/* Header Section */}
          <div className={`${isMobile ? 'mt-0 mb-6 p-4' : 'mt-0 mb-8 p-6 md:p-8'} bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl rounded-2xl border border-gray-800 shadow-2xl`}>
            <div className={`flex ${isSmallMobile ? 'flex-col gap-3' : 'items-center justify-between'} min-w-0`}>
              <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-4'} flex-1 min-w-0`}>
                <div className="relative flex-shrink-0">
                  <Bookmark className={`${isMobile ? 'w-6 h-6' : 'w-8 h-8'} text-cyan-400`} />
                  <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                </div>
                <div className="flex-1 min-w-0">
                  <h1 className={`${isSmallMobile ? 'text-2xl' : isMobile ? 'text-3xl' : 'text-3xl md:text-4xl'} font-bold break-words`} style={{ 
                    wordBreak: 'break-word', 
                    overflowWrap: 'anywhere',
                    background: 'linear-gradient(to right, #4DD0E1, #14B8A6, #10B981)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                    color: '#4DD0E1',
                    width: '100%',
                    maxWidth: '100%',
                    display: 'block'
                  }}>
                    My Bookmarks
                  </h1>
                </div>
              </div>
              <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-2 w-full' : 'space-x-4'}`}>
                <button 
                  onClick={() => navigate('/save-content')}
                  className={`${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 flex items-center justify-center ${isSmallMobile ? 'w-full' : 'space-x-2'} group relative overflow-hidden whitespace-nowrap`}
                  style={{
                    background: 'rgba(20, 20, 20, 0.6)',
                    border: '1px solid rgba(77, 208, 225, 0.2)',
                    backdropFilter: 'blur(10px)',
                    color: '#9ca3af'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(77, 208, 225, 0.5)'
                    e.currentTarget.style.background = 'rgba(20, 20, 20, 0.8)'
                    e.currentTarget.style.color = '#4DD0E1'
                    e.currentTarget.style.transform = 'translateY(-2px)'
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(77, 208, 225, 0.3)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(77, 208, 225, 0.2)'
                    e.currentTarget.style.background = 'rgba(20, 20, 20, 0.6)'
                    e.currentTarget.style.color = '#9ca3af'
                    e.currentTarget.style.transform = 'translateY(0)'
                    e.currentTarget.style.boxShadow = 'none'
                  }}
                >
                  <Plus className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} group-hover:rotate-90 transition-transform duration-300`} />
                  <span>{isSmallMobile ? 'Add' : 'Add Bookmark'}</span>
                </button>
                <button
                  onClick={handleDeleteAll}
                  disabled={bookmarks.length === 0}
                  className={`${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} ${isSmallMobile ? 'w-full' : ''} border border-red-700 rounded-xl hover:border-red-500/50 hover:bg-red-500/10 transition-all duration-300 transform hover:scale-105 flex items-center ${isSmallMobile ? 'justify-center' : 'space-x-2'} group relative overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100`}
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-red-500/10 to-red-600/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                  <Trash2 className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} group-hover:text-red-400 transition-colors duration-300`} />
                  <span className="group-hover:text-red-400 transition-colors duration-300">{isSmallMobile ? 'Delete All' : 'Delete All'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Semantic Search Section */}
          <div className={`${isMobile ? 'mb-6 p-4' : 'mb-8 p-6'} bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl hover:border-cyan-500/30 transition-all duration-300`}>
            <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-3'} mb-4`}>
              <Sparkles className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} text-cyan-400`} />
              <h2 className={`${isMobile ? 'text-lg' : 'text-xl'} font-semibold text-white`}>AI-Powered Semantic Search</h2>
            </div>
            <p className={`text-gray-400 ${isMobile ? 'mb-4 text-sm' : 'mb-6'}`}>Find bookmarks by meaning and context, not just keywords</p>
            
            <form onSubmit={handleSemanticSearch} className={`flex ${isSmallMobile ? 'flex-col' : 'items-center'} ${isSmallMobile ? 'gap-3' : 'space-x-4'} ${isMobile ? 'mb-4' : 'mb-6'}`}>
              <div className="flex-1 relative w-full">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Sparkles className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400`} />
                </div>
                <input
                  type="text"
                  placeholder="e.g., 'OAuth2 login flow', 'React hooks best practices'..."
                  value={semanticQuery}
                  onChange={e => setSemanticQuery(e.target.value)}
                  className={`w-full ${isMobile ? 'pl-10 pr-3 py-2 text-sm' : 'pl-12 pr-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300`}
                />
              </div>
              <button 
                type="submit" 
                disabled={semanticLoading || !semanticQuery.trim()}
                className={`bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center ${isSmallMobile ? 'justify-center w-full' : 'space-x-2'}`}
              >
                <Sparkles className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                <span>{semanticLoading ? 'Searching...' : 'Semantic Search'}</span>
              </button>
            </form>

            {semanticError && (
              <div className={`mb-4 p-4 border rounded-xl ${
                semanticError && !semanticError.toLowerCase().includes('error') 
                  ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400' 
                  : 'bg-red-500/10 border-red-500/20 text-red-400'
              }`}>
                {semanticError}
              </div>
            )}

            {semanticLoading && (
              <div className={`text-center ${isMobile ? 'py-6' : 'py-8'}`}>
                <div className="relative mb-4">
                  <Sparkles className={`${isMobile ? 'w-6 h-6' : 'w-8 h-8'} text-cyan-400 mx-auto animate-spin`} />
                  <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                </div>
                <p className={`text-cyan-400 ${isMobile ? 'text-sm' : ''}`}>Finding the most relevant bookmarks...</p>
              </div>
            )}

            {!semanticLoading && semanticResults.length > 0 && (
              <div className={`grid grid-cols-1 ${isMobile ? 'gap-4' : 'md:grid-cols-2 gap-6'}`}>
                {semanticResults.map((result, idx) => (
                  <div key={result.id || idx} className={`bg-gradient-to-br from-gray-800/50 to-black/50 border border-gray-700 rounded-xl ${isMobile ? 'p-4' : 'p-6'} hover:border-cyan-500/30 transition-all duration-300`}>
                    <div className={`flex items-center justify-between ${isMobile ? 'mb-2' : 'mb-3'}`}>
                      <div className={`flex items-center ${isSmallMobile ? 'gap-1' : 'space-x-2'}`}>
                        <div className={`${isMobile ? 'p-1.5' : 'p-2'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 rounded-lg`}>
                          <Sparkles className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} text-cyan-400`} />
                        </div>
                        <span className={`${isMobile ? 'text-xs' : 'text-sm'} text-cyan-400 font-medium`}>
                          Relevance: {result.similarity_percentage ? `${Math.round(result.similarity_percentage)}%` : result.relevance_score ? `${Math.round(result.relevance_score)}%` : 'High'}
                        </span>
                      </div>
                    </div>
                    <h3 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold text-white ${isMobile ? 'mb-1' : 'mb-2'}`}>{result.title}</h3>
                    <p className={`text-cyan-400 ${isMobile ? 'text-xs mb-2' : 'text-sm mb-3'}`}>{result.url}</p>
                    {result.content_snippet && (
                      <p className={`text-gray-400 ${isMobile ? 'text-xs mb-3' : 'text-sm mb-4'}`}>{result.content_snippet}</p>
                    )}
                    <a 
                      href={result.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className={`flex items-center ${isSmallMobile ? 'justify-center' : 'space-x-2'} ${isMobile ? 'px-3 py-1.5 text-xs' : 'px-4 py-2'} bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 rounded-lg transition-colors duration-300 inline-flex`}
                    >
                      <ExternalLink className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`} />
                      <span>View Content</span>
                    </a>
                  </div>
                ))}
              </div>
            )}

            {!semanticLoading && semanticResults.length === 0 && semanticQuery && !semanticError && (
              <div className="text-center py-8 text-gray-400">
                No semantically relevant bookmarks found.
              </div>
            )}
          </div>

                     {/* Controls Section */}
           <div className={`${isMobile ? 'mb-6 p-4' : 'mb-8 p-6'} bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl`}>
             {debouncedSearchTerm && (
               <div className={`${isMobile ? 'mb-3 p-2' : 'mb-4 p-3'} bg-cyan-600/10 border border-cyan-500/20 rounded-xl`}>
                 <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-2' : 'justify-between'}`}>
                   <div className={`flex items-center ${isSmallMobile ? 'gap-1' : 'space-x-2'}`}>
                     <Search className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} text-cyan-400`} />
                     <span className={`text-cyan-400 ${isMobile ? 'text-xs' : 'text-sm'}`}>
                       Searching for: <span className="font-semibold">"{debouncedSearchTerm}"</span>
                     </span>
                   </div>
                   <span className={`text-cyan-400 ${isMobile ? 'text-xs' : 'text-sm'}`}>
                     {bookmarks.length} result{bookmarks.length !== 1 ? 's' : ''}
                   </span>
                 </div>
               </div>
             )}
            <div className={`flex flex-col ${isMobile ? 'gap-3' : 'lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0 lg:space-x-6'}`}>
                             {/* Search Form */}
               <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-2' : 'space-x-4'} flex-1`}>
                 <div className="flex-1 relative w-full">
                   <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                     {searchLoading ? (
                       <div className="animate-spin">
                         <Search className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-cyan-400`} />
                       </div>
                     ) : searchTerm && searchTerm !== debouncedSearchTerm ? (
                       <Search className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-yellow-400`} />
                     ) : (
                       <Search className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400`} />
                     )}
                   </div>
                   <input
                     type="text"
                     placeholder="Search bookmarks... (auto-searches as you type)"
                     value={searchTerm}
                     onChange={(e) => setSearchTerm(e.target.value)}
                     className={`w-full ${isMobile ? 'pl-10 pr-3 py-2 text-sm' : 'pl-12 pr-4 py-3'} bg-gray-800/50 border rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 transition-all duration-300 ${
                       searchLoading 
                         ? 'border-cyan-500/50 focus:border-cyan-500/50 focus:ring-cyan-500/20' 
                         : searchTerm && searchTerm !== debouncedSearchTerm
                         ? 'border-yellow-500/50 focus:border-yellow-500/50 focus:ring-yellow-500/20'
                         : 'border-gray-700 focus:border-cyan-500/50 focus:ring-cyan-500/20'
                     }`}
                   />
                   {searchLoading && (
                     <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
                       <div className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} border-2 border-cyan-400 border-t-transparent rounded-full animate-spin`}></div>
                     </div>
                   )}
                 </div>
                 {searchTerm && (
                   <button 
                     onClick={() => setSearchTerm('')}
                     className={`bg-gradient-to-r from-gray-600 to-gray-700 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} ${isSmallMobile ? 'w-full' : ''} rounded-xl font-semibold hover:shadow-lg hover:shadow-gray-500/25 transition-all duration-300 transform hover:scale-105 flex items-center ${isSmallMobile ? 'justify-center' : 'space-x-2'}`}
                   >
                     <X className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                     <span>Clear</span>
                   </button>
                 )}
               </div>

              {/* Filter and View Controls */}
              <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-3 w-full' : 'space-x-4'}`}>
                <div className={`flex items-center ${isSmallMobile ? 'w-full gap-2' : 'space-x-2'}`}>
                  <Filter className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400`} />
                  <select
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    className={`bg-gray-800/50 border border-gray-700 rounded-xl ${isMobile ? 'px-3 py-2 text-sm flex-1' : 'px-4 py-3'} text-white focus:outline-none focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300 ${isSmallMobile ? 'w-full' : ''}`}
                  >
                    {categoryOptions.map(option => (
                      <option key={option.value} value={option.value} className="bg-gray-800">
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className={`flex items-center ${isSmallMobile ? 'w-full justify-center' : 'space-x-2'} bg-gray-800/50 rounded-xl p-1`}>
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-2 rounded-lg transition-all duration-300 ${viewMode === 'grid' ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-500/25' : 'text-gray-400 hover:text-white hover:bg-gray-700/50'}`}
                  >
                    <Grid3X3 className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-2 rounded-lg transition-all duration-300 ${viewMode === 'list' ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-500/25' : 'text-gray-400 hover:text-white hover:bg-gray-700/50'}`}
                  >
                    <List className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Bookmarks Content */}
          {bookmarks.length > 0 ? (
            <>
              {viewMode === 'grid' ? (
                <div className={`grid grid-cols-1 ${isMobile ? 'sm:grid-cols-2' : 'md:grid-cols-2 lg:grid-cols-3'} ${isMobile ? 'gap-4' : 'gap-6'} ${isMobile ? 'mb-6' : 'mb-8'}`}>
                  {bookmarks.map((bookmark) => (
                    <div key={bookmark.id} className="group bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl overflow-hidden hover:border-cyan-500/30 transition-all duration-300 hover:transform hover:scale-[1.02]">
                      <div className="aspect-video bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center">
                        <Globe className={`${isMobile ? 'w-8 h-8' : 'w-12 h-12'} text-gray-600`} />
                      </div>
                      
                      <div className={`${isMobile ? 'p-4' : 'p-6'}`}>
                        <div className={`flex items-start justify-between ${isMobile ? 'mb-2' : 'mb-3'}`}>
                          <h3 className={`font-semibold text-white group-hover:text-cyan-400 transition-colors duration-300 line-clamp-2 ${isMobile ? 'text-sm' : ''}`}>
                            {bookmark.title}
                          </h3>
                          <div className={`flex items-center ${isSmallMobile ? 'gap-1' : 'space-x-2'} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}>
                            <button className="p-1">
                              <Star className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} text-gray-400 hover:text-yellow-500`} />
                            </button>
                            <button onClick={() => handleDelete(bookmark.id)} className="p-1">
                              <Trash2 className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} text-gray-400 hover:text-red-500`} />
                            </button>
                          </div>
                        </div>
                        
                        <p className={`text-cyan-400 ${isMobile ? 'text-xs mb-1' : 'text-sm mb-2'} truncate`}>{bookmark.url}</p>
                        {bookmark.description && (
                          <p className={`text-gray-400 ${isMobile ? 'text-xs mb-3' : 'text-sm mb-4'} line-clamp-2`}>{bookmark.description}</p>
                        )}
                        
                        <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-2' : 'justify-between'}`}>
                          <div className={`flex items-center ${isSmallMobile ? 'gap-1' : 'space-x-2'}`}>
                            {bookmark.category && (
                              <span className={`${isMobile ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-xs'} bg-cyan-600/20 text-cyan-400 rounded-lg`}>
                                {bookmark.category}
                              </span>
                            )}
                            <div className={`${isMobile ? 'text-xs' : 'text-xs'} text-gray-500 flex items-center`}>
                              <Clock className={`${isMobile ? 'w-2.5 h-2.5' : 'w-3 h-3'} mr-1`} />
                              {new Date(bookmark.saved_at).toLocaleDateString()}
                            </div>
                          </div>
                          <a 
                            href={bookmark.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className={`${isMobile ? 'p-1.5' : 'p-2'} bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 rounded-lg transition-colors duration-300`}
                          >
                            <ExternalLink className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`} />
                          </a>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={`${isMobile ? 'space-y-3 mb-6' : 'space-y-4 mb-8'}`}>
                  {bookmarks.map((bookmark) => (
                    <div key={bookmark.id} className={`flex items-center ${isSmallMobile ? 'flex-col gap-3' : 'space-x-4'} ${isMobile ? 'p-4' : 'p-6'} bg-gradient-to-r from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-xl hover:border-cyan-500/30 transition-all duration-300`}>
                      <div className={`${isMobile ? 'w-10 h-10' : 'w-12 h-12'} bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg flex items-center justify-center ${isSmallMobile ? 'w-full' : ''}`}>
                        <Globe className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} text-gray-600`} />
                      </div>
                      
                      <div className={`flex-1 ${isSmallMobile ? 'w-full' : ''}`}>
                        <h3 className={`font-semibold text-white ${isMobile ? 'text-sm mb-1' : 'mb-1'}`}>{bookmark.title}</h3>
                        <p className={`text-cyan-400 ${isMobile ? 'text-xs mb-1' : 'text-sm mb-1'} truncate`}>{bookmark.url}</p>
                        {bookmark.description && (
                          <p className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'} line-clamp-1`}>{bookmark.description}</p>
                        )}
                        <div className={`flex items-center ${isSmallMobile ? 'flex-col gap-1 items-start' : 'space-x-2'} ${isMobile ? 'mt-1' : 'mt-2'}`}>
                          {bookmark.category && (
                            <span className={`${isMobile ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-xs'} bg-cyan-600/20 text-cyan-400 rounded-lg`}>
                              {bookmark.category}
                            </span>
                          )}
                          <span className={`${isMobile ? 'text-xs' : 'text-xs'} text-gray-500`}>
                            {new Date(bookmark.saved_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                      
                      <div className={`flex items-center ${isSmallMobile ? 'w-full justify-center gap-3' : 'space-x-2'}`}>
                        <button>
                          <Star className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 hover:text-yellow-500`} />
                        </button>
                        <a 
                          href={bookmark.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 hover:text-cyan-400`} />
                        </a>
                        <button onClick={() => handleDelete(bookmark.id)}>
                          <Trash2 className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 hover:text-red-500`} />
                        </button>
                        <button>
                          <MoreHorizontal className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 hover:text-white`} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className={`flex items-center justify-center ${isSmallMobile ? 'flex-col gap-3' : 'space-x-4'} ${isMobile ? 'mb-6' : 'mb-8'}`}>
                  <button 
                    onClick={() => setPage(page - 1)} 
                    disabled={page === 1}
                    className={`flex items-center ${isSmallMobile ? 'w-full justify-center' : 'space-x-2'} ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} bg-gradient-to-r from-gray-800/50 to-black/50 border border-gray-700 rounded-xl hover:border-cyan-500/50 hover:bg-cyan-500/10 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-gray-700 disabled:hover:bg-transparent`}
                  >
                    <ArrowLeft className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                    <span>Previous</span>
                  </button>
                  
                  <div className={`${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 border border-cyan-500/30 rounded-xl`}>
                    <span className={`text-cyan-400 font-semibold ${isMobile ? 'text-sm' : ''}`}>Page {page} of {totalPages}</span>
                  </div>
                  
                  <button 
                    onClick={() => setPage(page + 1)} 
                    disabled={page === totalPages}
                    className={`flex items-center ${isSmallMobile ? 'w-full justify-center' : 'space-x-2'} ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} bg-gradient-to-r from-gray-800/50 to-black/50 border border-gray-700 rounded-xl hover:border-cyan-500/50 hover:bg-cyan-500/10 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-gray-700 disabled:hover:bg-transparent`}
                  >
                    <span>Next</span>
                    <ArrowRight className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className={`text-center ${isMobile ? 'py-12' : 'py-16'} bg-gradient-to-br from-gray-900/30 to-black/30 rounded-2xl border border-gray-800`}>
              <div className={`${isMobile ? 'p-4' : 'p-6'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 rounded-full ${isMobile ? 'w-16 h-16' : 'w-24 h-24'} mx-auto ${isMobile ? 'mb-4' : 'mb-6'}`}>
                <Bookmark className={`${isMobile ? 'w-8 h-8' : 'w-12 h-12'} text-cyan-400 mx-auto ${isMobile ? 'mt-2' : 'mt-3'}`} />
              </div>
              <h3 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-semibold text-white ${isMobile ? 'mb-3' : 'mb-4'}`}>No bookmarks found</h3>
              <p className={`text-gray-400 ${isMobile ? 'mb-6 text-base' : 'mb-8 text-lg'}`}>
                {searchTerm || filter !== 'all' 
                  ? 'Try adjusting your search or filter criteria.'
                  : 'Start by adding your first bookmark using the Chrome extension or the add button above.'
                }
              </p>
              {!searchTerm && filter === 'all' && (
                <button 
                  onClick={() => navigate('/save-content')}
                  className={`bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-6 py-3 text-sm' : 'px-8 py-4'} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 flex items-center ${isSmallMobile ? 'justify-center w-full' : 'space-x-3'} mx-auto`}
                >
                  <Plus className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'}`} />
                  <span>{isSmallMobile ? 'Add Bookmark' : 'Add Your First Bookmark'}</span>
                </button>
              )}
            </div>
          )}
        </main>
        </div>
      </div>

      <style jsx>{`
        .logo-container {
          width: auto;
          height: auto;
          max-width: 200px;
          max-height: 80px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: transparent;
          border: none;
          box-shadow: none;
          transition: transform 0.3s ease;
          padding: 0;
          position: relative;
        }
        
        .logo-container:hover {
          transform: scale(1.05) !important;
        }
        
        .logo-container img {
          width: auto;
          height: auto;
          max-width: 200px;
          max-height: 80px;
          object-fit: contain;
          mix-blend-mode: normal;
        }
        
        @media (max-width: 768px) {
          .logo-container {
            max-width: 150px;
            max-height: 60px;
            padding: 0;
          }
          
          .logo-container img {
            max-width: 150px;
            max-height: 60px;
          }
        }
        
        @media (max-width: 480px) {
          .logo-container {
            max-width: 120px;
            max-height: 50px;
            padding: 0;
          }
          
          .logo-container img {
            max-width: 120px;
            max-height: 50px;
          }
        }
        
        .line-clamp-1 {
          display: -webkit-box;
          -webkit-line-clamp: 1;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  )
}

export default Bookmarks