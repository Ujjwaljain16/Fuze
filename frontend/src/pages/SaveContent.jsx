import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { Link } from 'react-router-dom'
import api from '../services/api'
import logo1 from '../assets/logo1.svg'
import { 
  Bookmark, ExternalLink, Loader2, Plus, Tag, AlertTriangle, Eye, 
  Zap, Sparkles, Globe, Clock, Star, CheckCircle, XCircle, LogOut
} from 'lucide-react'

const SaveContent = () => {
  const { isAuthenticated, logout } = useAuth()
  const { success, error } = useToast()
  const [loading, setLoading] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [checkingDuplicate, setCheckingDuplicate] = useState(false)
  const [duplicateInfo, setDuplicateInfo] = useState(null)
  const [projects, setProjects] = useState([])
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [formData, setFormData] = useState({
    url: '',
    title: '',
    description: '',
    category: 'other',
    tags: '',
    project_id: ''
  })
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)
  const [isSmallMobile, setIsSmallMobile] = useState(window.innerWidth <= 480)
  const [stats, setStats] = useState({
    total_bookmarks: { value: 0, change: '0%', change_value: 0 },
    weekly_saves: { value: 0, change: '0%', change_value: 0 },
    success_rate: { value: 0, change: '0%', change_value: 0 }
  })
  const [statsLoading, setStatsLoading] = useState(true)

  // Mouse tracking for animated background
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

  // Fetch projects and stats on component mount
  useEffect(() => {
    if (isAuthenticated) {
      fetchProjects()
      fetchStats()
    }
  }, [isAuthenticated])

  const fetchStats = async () => {
    try {
      setStatsLoading(true)
      const response = await api.get('/api/bookmarks/dashboard/stats')
      if (response.data) {
        setStats({
          total_bookmarks: response.data.total_bookmarks || { value: 0, change: '0%', change_value: 0 },
          weekly_saves: response.data.weekly_saves || { value: 0, change: '0%', change_value: 0 },
          success_rate: response.data.success_rate || { value: 0, change: '0%', change_value: 0 }
        })
      }
    } catch (err) {
      console.error('Error fetching stats:', err)
      // Keep default values on error
    } finally {
      setStatsLoading(false)
    }
  }

  // Check for duplicates when URL changes
  useEffect(() => {
    const checkDuplicate = async () => {
      if (!formData.url.trim() || formData.url.length < 10) {
        setDuplicateInfo(null)
        return
      }

      setCheckingDuplicate(true)
      try {
        const response = await api.post('/api/bookmarks/check-duplicate', { url: formData.url })
        setDuplicateInfo(response.data)
      } catch (err) {
        console.error('Error checking duplicate:', err)
        setDuplicateInfo(null)
      } finally {
        setCheckingDuplicate(false)
      }
    }

    // Debounce the duplicate check
    const timeoutId = setTimeout(checkDuplicate, 1000)
    return () => clearTimeout(timeoutId)
  }, [formData.url])

  const fetchProjects = async () => {
    try {
      const response = await api.get('/api/projects')
      setProjects(response.data.projects || [])
    } catch (err) {
      console.error('Error fetching projects:', err)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const extractUrlData = async () => {
    if (!formData.url) {
      error('Please enter a URL first')
      return
    }

    setExtracting(true)
    try {
      const response = await api.post('/api/bookmarks/extract-url', { url: formData.url })
      
      if (response.data) {
        setFormData(prev => ({
          ...prev,
          title: response.data.title || prev.title,
          description: response.data.description || prev.description
        }))
        success('URL data extracted successfully!')
      }
    } catch (err) {
      console.error('Error extracting URL data:', err)
      error('Failed to extract URL data. Please fill in manually.')
    } finally {
      setExtracting(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!formData.url.trim()) {
      error('URL is required')
      return
    }

    setLoading(true)
    try {
      const bookmarkData = {
        url: formData.url.trim(),
        title: formData.title.trim() || 'Untitled Bookmark',
        description: formData.description.trim(),
        category: formData.category,
        tags: formData.tags.trim()
      }

      if (formData.project_id) {
        bookmarkData.project_id = formData.project_id
      }

      const response = await api.post('/api/bookmarks', bookmarkData)
      
      if (response.data) {
        if (response.data.wasDuplicate) {
          const duplicateType = response.data.duplicateType || 'exact'
          let message = 'Bookmark already exists and has been updated.'
          
          if (duplicateType === 'normalized') {
            message = 'Similar bookmark found (different URL format) and has been updated.'
          } else if (duplicateType === 'similar') {
            message = 'Similar bookmark found (same page, different parameters) and has been updated.'
          }
          
          success(message)
        } else {
          success('Content saved successfully!')
        }
        
        // Reset form
        setFormData({
          url: '',
          title: '',
          description: '',
          category: 'other',
          tags: '',
          project_id: ''
        })
        
        // Refresh stats after saving
        fetchStats()
      }
    } catch (err) {
      console.error('Error saving content:', err)
      if (err.response?.data?.message) {
        error(err.response.data.message)
      } else {
        error('Failed to save content. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const categoryOptions = [
    { value: 'other', label: 'Other', icon: Globe },
    { value: 'technology', label: 'Technology', icon: Zap },
    { value: 'programming', label: 'Programming', icon: Sparkles },
    { value: 'design', label: 'Design', icon: Star },
    { value: 'business', label: 'Business', icon: CheckCircle },
    { value: 'education', label: 'Education', icon: Bookmark },
    { value: 'news', label: 'News', icon: Clock },
    { value: 'tutorial', label: 'Tutorial', icon: Plus },
    { value: 'research', label: 'Research', icon: Eye }
  ]

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
          <div className="max-w-lg mx-auto text-center">
            <div className={`bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl rounded-2xl ${isMobile ? 'p-6' : 'p-8'} border border-gray-800 shadow-2xl`}>
              <div className={`flex items-center justify-center ${isSmallMobile ? 'gap-2' : 'space-x-3'} ${isMobile ? 'mb-3' : 'mb-4'}`}>
                <div className="relative">
                  <Zap className={`${isMobile ? 'w-6 h-6' : 'w-8 h-8'} text-cyan-400`} />
                  <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                </div>
                <h2 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold bg-gradient-to-r from-cyan-400 via-teal-400 to-emerald-400 bg-clip-text text-transparent`}>
                  Authentication Required
                </h2>
              </div>
              <p className={`text-gray-300 ${isMobile ? 'mb-4 text-sm' : 'mb-6'}`}>Please log in to save content to your Fuze library.</p>
              <button className={`bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105`}>
                Sign In
              </button>
            </div>
          </div>
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
                  window.location.href = '/login'
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
              <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-4'} ${isMobile ? 'mb-3' : 'mb-4'} min-w-0`}>
                <div className="relative flex-shrink-0">
                  <Bookmark className={`${isMobile ? 'w-6 h-6' : 'w-8 h-8'} text-cyan-400`} />
                  <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
                </div>
                <h1 className={`${isSmallMobile ? 'text-2xl' : isMobile ? 'text-3xl' : 'text-3xl md:text-4xl'} font-bold flex-1 min-w-0 break-words`} style={{ 
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
                  Save New Content
                </h1>
              </div>
              <p className={`text-gray-300 ${isMobile ? 'text-base' : 'text-lg md:text-xl'} break-words`} style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                Add web content to your Fuze library with intelligent categorization and AI-powered organization.
              </p>
            </div>

            <div className={`grid grid-cols-1 ${isMobile ? 'gap-6' : 'lg:grid-cols-3 gap-8'}`}>
              {/* Main Form */}
              <div className="lg:col-span-2">
                                 <div className={`bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl ${isMobile ? 'p-4' : 'p-6 md:p-8'} shadow-2xl`}>
                   <form onSubmit={handleSubmit} className={`${isMobile ? 'space-y-4' : 'space-y-6'}`}>
                     {/* URL Input */}
                    <div className="space-y-2">
                      <label htmlFor="url" className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-semibold text-white`}>
                        URL <span className="text-red-400">*</span>
                      </label>
                      <div className={`flex ${isSmallMobile ? 'flex-col gap-2' : 'space-x-3'}`}>
                        <div className="flex-1 relative">
                          <input
                            type="url"
                            id="url"
                            name="url"
                            value={formData.url}
                            onChange={handleInputChange}
                            placeholder="https://example.com/article"
                            className={`w-full ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all duration-300 backdrop-blur-sm`}
                            required
                          />
                          <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-500/10 to-teal-500/10 opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                        </div>
                        <button
                          type="button"
                          onClick={extractUrlData}
                          disabled={extracting || !formData.url}
                          className={`${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} ${isSmallMobile ? 'w-full' : ''} bg-gradient-to-r from-cyan-600 to-teal-600 rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center ${isSmallMobile ? 'justify-center' : 'space-x-2'}`}
                        >
                          {extracting ? (
                            <Loader2 size={isMobile ? 14 : 16} className="animate-spin" />
                          ) : (
                            <ExternalLink size={isMobile ? 14 : 16} />
                          )}
                          <span>{extracting ? 'Extracting...' : 'Extract'}</span>
                        </button>
                      </div>
                    </div>

                    {/* Title Input */}
                    <div className="space-y-2">
                      <label htmlFor="title" className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-semibold text-white`}>
                        Title
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          id="title"
                          name="title"
                          value={formData.title}
                          onChange={handleInputChange}
                          placeholder="Enter title or leave blank for auto-extraction"
                          className={`w-full ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all duration-300 backdrop-blur-sm`}
                        />
                        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-500/10 to-teal-500/10 opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                      </div>
                    </div>

                    {/* Description Input */}
                    <div className="space-y-2">
                      <label htmlFor="description" className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-semibold text-white`}>
                        Notes
                      </label>
                      <div className="relative">
                        <textarea
                          id="description"
                          name="description"
                          value={formData.description}
                          onChange={handleInputChange}
                          placeholder="Add your notes or description..."
                          rows={4}
                          className={`w-full ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all duration-300 backdrop-blur-sm resize-none`}
                        />
                        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-500/10 to-teal-500/10 opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                      </div>
                    </div>

                    {/* Category and Tags Row */}
                    <div className={`grid grid-cols-1 ${isMobile ? 'gap-4' : 'md:grid-cols-2 gap-6'}`}>
                      <div className="space-y-2">
                        <label htmlFor="category" className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-semibold text-white`}>
                          Category
                        </label>
                        <div className="relative">
                          <select
                            id="category"
                            name="category"
                            value={formData.category}
                            onChange={handleInputChange}
                            className={`w-full ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all duration-300 backdrop-blur-sm appearance-none cursor-pointer`}
                          >
                            {categoryOptions.map(option => (
                              <option key={option.value} value={option.value} className="bg-gray-800">
                                {option.label}
                              </option>
                            ))}
                          </select>
                          <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-500/10 to-teal-500/10 opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <label htmlFor="tags" className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-semibold text-white`}>
                          Tags
                        </label>
                        <div className="relative">
                          <div className="flex items-center">
                            <Tag size={isMobile ? 14 : 16} className={`absolute ${isMobile ? 'left-2.5' : 'left-3'} text-gray-400 z-10`} />
                            <input
                              type="text"
                              id="tags"
                              name="tags"
                              value={formData.tags}
                              onChange={handleInputChange}
                              placeholder="react, javascript, tutorial"
                              className={`w-full ${isMobile ? 'pl-9 pr-3 py-2 text-sm' : 'pl-10 pr-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all duration-300 backdrop-blur-sm`}
                            />
                          </div>
                          <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-500/10 to-teal-500/10 opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                        </div>
                        <p className={`${isMobile ? 'text-xs' : 'text-xs'} text-gray-400`}>Separate tags with commas</p>
                      </div>
                    </div>

                    {/* Project Association */}
                    {projects.length > 0 && (
                      <div className="space-y-2">
                        <label htmlFor="project_id" className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-semibold text-white`}>
                          Associate with Project (Optional)
                        </label>
                        <div className="relative">
                          <select
                            id="project_id"
                            name="project_id"
                            value={formData.project_id}
                            onChange={handleInputChange}
                            className={`w-full ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} bg-gray-800/50 border border-gray-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all duration-300 backdrop-blur-sm appearance-none cursor-pointer`}
                          >
                            <option value="" className="bg-gray-800">No Project</option>
                            {projects.map(project => (
                              <option key={project.id} value={project.id} className="bg-gray-800">
                                {project.title}
                              </option>
                            ))}
                          </select>
                          <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-cyan-500/10 to-teal-500/10 opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                        </div>
                      </div>
                    )}

                    {/* Duplicate Check Results */}
                    {checkingDuplicate && (
                      <div className={`bg-gradient-to-r from-yellow-600/20 to-orange-600/20 border border-yellow-500/30 rounded-xl ${isMobile ? 'p-3' : 'p-4'} flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-3'}`}>
                        <Loader2 size={isMobile ? 16 : 20} className="text-yellow-400 animate-spin" />
                        <p className={`text-yellow-200 ${isMobile ? 'text-sm' : ''}`}>Checking for duplicates...</p>
                      </div>
                    )}

                    {duplicateInfo && !checkingDuplicate && (
                      <div className={`border rounded-xl ${isMobile ? 'p-3' : 'p-4'} flex items-start ${isSmallMobile ? 'gap-2' : 'space-x-3'} ${
                        duplicateInfo.isDuplicate 
                          ? 'bg-gradient-to-r from-red-600/20 to-pink-600/20 border-red-500/30' 
                          : 'bg-gradient-to-r from-cyan-600/20 to-teal-600/20 border-cyan-500/30'
                      }`}>
                        {duplicateInfo.isDuplicate ? (
                          <AlertTriangle size={isMobile ? 16 : 20} className="text-red-400 flex-shrink-0 mt-0.5" />
                        ) : (
                          <CheckCircle size={isMobile ? 16 : 20} className="text-cyan-400 flex-shrink-0 mt-0.5" />
                        )}
                        <div className="flex-1">
                          {duplicateInfo.isDuplicate ? (
                            <>
                              <p className={`text-red-200 font-semibold ${isMobile ? 'mb-1 text-sm' : 'mb-2'}`}>Duplicate Found!</p>
                              <p className={`text-red-300 ${isMobile ? 'text-xs mb-2' : 'text-sm mb-3'}`}>This URL already exists in your library.</p>
                              {duplicateInfo.existingBookmark && (
                                <div className={`flex items-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'}`}>
                                  <Eye size={isMobile ? 12 : 14} className="text-red-400" />
                                  <a 
                                    href={duplicateInfo.existingBookmark.url} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className={`text-red-400 hover:text-red-300 ${isMobile ? 'text-xs' : 'text-sm'} transition-colors duration-300 underline`}
                                  >
                                    {duplicateInfo.existingBookmark.title || duplicateInfo.existingBookmark.url}
                                  </a>
                                </div>
                              )}
                            </>
                          ) : (
                            <p className={`text-cyan-200 font-semibold ${isMobile ? 'text-sm' : ''}`}>No duplicates found - ready to save!</p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Submit Button */}
                    <div className={`${isMobile ? 'pt-3' : 'pt-4'}`}>
                      <button
                        type="submit"
                        disabled={loading}
                        className={`w-full bg-gradient-to-r from-cyan-600 to-teal-600 ${isMobile ? 'px-4 py-3 text-sm' : 'px-8 py-4 text-lg'} rounded-xl font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center justify-center ${isSmallMobile ? 'gap-2' : 'space-x-3'} group relative overflow-hidden`}
                      >
                        <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 to-teal-400 opacity-0 group-hover:opacity-20 transition-opacity duration-300"></div>
                        {loading ? (
                          <>
                            <Loader2 size={isMobile ? 16 : 20} className="animate-spin" />
                            <span>Saving Content...</span>
                          </>
                        ) : (
                          <>
                            <Bookmark size={isMobile ? 16 : 20} className="group-hover:scale-110 transition-transform duration-300" />
                            <span>Save to Library</span>
                          </>
                        )}
                      </button>
                    </div>
                  </form>
                </div>
              </div>

              {/* Sidebar */}
              <div className={`${isMobile ? 'space-y-4' : 'space-y-6'}`}>
                {/* Tips Section */}
                <div className={`bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl ${isMobile ? 'p-4' : 'p-6'} shadow-2xl`}>
                  <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-3'} ${isMobile ? 'mb-3' : 'mb-4'}`}>
                    <Sparkles className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} text-cyan-400`} />
                    <h3 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold text-white`}>Pro Tips</h3>
                  </div>
                  <ul className={`${isMobile ? 'space-y-2 text-xs' : 'space-y-3 text-sm'} text-gray-300`}>
                    <li className={`flex items-start ${isSmallMobile ? 'gap-1.5' : 'space-x-2'}`}>
                      <div className={`${isMobile ? 'w-1 h-1' : 'w-1.5 h-1.5'} bg-cyan-400 rounded-full ${isMobile ? 'mt-1.5' : 'mt-2'} flex-shrink-0`}></div>
                      <span>Use descriptive titles to make content easier to find later</span>
                    </li>
                    <li className={`flex items-start ${isSmallMobile ? 'gap-1.5' : 'space-x-2'}`}>
                      <div className={`${isMobile ? 'w-1 h-1' : 'w-1.5 h-1.5'} bg-teal-400 rounded-full ${isMobile ? 'mt-1.5' : 'mt-2'} flex-shrink-0`}></div>
                      <span>Add relevant tags to group similar content together</span>
                    </li>
                    <li className={`flex items-start ${isSmallMobile ? 'gap-1.5' : 'space-x-2'}`}>
                      <div className={`${isMobile ? 'w-1 h-1' : 'w-1.5 h-1.5'} bg-emerald-400 rounded-full ${isMobile ? 'mt-1.5' : 'mt-2'} flex-shrink-0`}></div>
                      <span>Associate content with projects for better organization</span>
                    </li>
                    <li className={`flex items-start ${isSmallMobile ? 'gap-1.5' : 'space-x-2'}`}>
                      <div className={`${isMobile ? 'w-1 h-1' : 'w-1.5 h-1.5'} bg-orange-400 rounded-full ${isMobile ? 'mt-1.5' : 'mt-2'} flex-shrink-0`}></div>
                      <span>Use the Chrome extension for one-click saving</span>
                    </li>
                  </ul>
                </div>

                {/* Quick Stats */}
                <div className={`bg-gradient-to-br from-gray-900/50 to-black/50 backdrop-blur-xl border border-gray-800 rounded-2xl ${isMobile ? 'p-4' : 'p-6'} shadow-2xl`}>
                  <h3 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold text-white ${isMobile ? 'mb-3' : 'mb-4'}`}>Quick Stats</h3>
                  {statsLoading ? (
                    <div className={`${isMobile ? 'space-y-3' : 'space-y-4'}`}>
                      <div className="flex items-center justify-between">
                        <span className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'}`}>Total Saved</span>
                        <div className="w-12 h-4 bg-gray-700 rounded animate-pulse"></div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'}`}>This Week</span>
                        <div className="w-12 h-4 bg-gray-700 rounded animate-pulse"></div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'}`}>Success Rate</span>
                        <div className="w-12 h-4 bg-gray-700 rounded animate-pulse"></div>
                      </div>
                    </div>
                  ) : (
                    <div className={`${isMobile ? 'space-y-3' : 'space-y-4'}`}>
                      <div className="flex items-center justify-between">
                        <span className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'}`}>Total Saved</span>
                        <span className={`text-white font-semibold ${isMobile ? 'text-sm' : ''}`}>
                          {stats.total_bookmarks.value.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'}`}>This Week</span>
                        <span className={`text-teal-400 font-semibold ${isMobile ? 'text-sm' : ''}`}>
                          {stats.weekly_saves.change_value >= 0 ? '+' : ''}{stats.weekly_saves.value}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'}`}>Success Rate</span>
                        <span className={`text-cyan-400 font-semibold ${isMobile ? 'text-sm' : ''}`}>
                          {Math.round(stats.success_rate.value)}%
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Chrome Extension CTA */}
                <div className={`bg-gradient-to-br from-orange-600/20 to-red-600/20 border border-orange-500/30 rounded-2xl ${isMobile ? 'p-4' : 'p-6'} shadow-2xl`}>
                  <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-3'} ${isMobile ? 'mb-3' : 'mb-4'}`}>
                    <ExternalLink className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} text-orange-400`} />
                    <h3 className={`${isMobile ? 'text-base' : 'text-lg'} font-semibold text-white`}>Chrome Extension</h3>
                  </div>
                  <p className={`text-gray-300 ${isMobile ? 'text-xs mb-3' : 'text-sm mb-4'}`}>
                    Save content with one click from any webpage. Install our Chrome extension for the ultimate bookmarking experience.
                  </p>
                  <a
                    href="/extension/download"
                    className={`w-full bg-gradient-to-r from-orange-600 to-red-600 ${isMobile ? 'px-3 py-2 text-sm' : 'px-4 py-3'} rounded-xl font-semibold hover:shadow-lg hover:shadow-orange-500/25 transition-all duration-300 transform hover:scale-105 flex items-center justify-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'}`}
                  >
                    <Plus size={isMobile ? 14 : 16} />
                    <span>Install Extension</span>
                  </a>
                </div>
              </div>
            </div>
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
      `}</style>
    </div>
  )
  
}

export default SaveContent