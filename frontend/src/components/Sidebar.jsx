import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useState } from 'react'
import { 
  Bookmark, 
  FolderOpen, 
  Grid3X3, 
  Sparkles, 
  Plus, 
  Settings, 
  User,
  X,
  Menu,
  LogOut
} from 'lucide-react'
import './sidebar-styles.css'

const Sidebar = ({ isOpen, onClose, collapsed, setCollapsed, isMobile, onToggle }) => {
  const { isAuthenticated, user } = useAuth()
  const location = useLocation()

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: Grid3X3 },
    { name: 'All Bookmarks', href: '/bookmarks', icon: Bookmark },
    { name: 'Projects', href: '/projects', icon: FolderOpen },
    { name: 'Save Content', href: '/save-content', icon: Plus },
    { name: 'Recommendations', href: '/recommendations', icon: Sparkles },
    { name: 'Settings', href: '/profile', icon: Settings },
  ]

  // Helper function to check if nav item is active
  const isNavItemActive = (item) => {
    if (item.href.includes('?')) {
      // For items with query params, check both pathname and search
      const [pathname, search] = item.href.split('?')
      return location.pathname === pathname && location.search.includes(search.split('=')[1])
    }
    return location.pathname === item.href
  }

  const [isAnimating, setIsAnimating] = useState(false)

  if (!isAuthenticated) return null

  // Clean class name construction with proper state management
  const sidebarClasses = [
    'sidebar',
    isMobile ? (isOpen ? 'sidebar-open' : '') : (collapsed ? 'sidebar-collapsed' : 'sidebar-expanded')
  ].filter(Boolean).join(' ')

  // Debug logging
  console.log('Sidebar state:', { isMobile, isOpen, collapsed, sidebarClasses });

  const handleToggle = () => {
    setIsAnimating(true)
    setCollapsed(!collapsed)
    setTimeout(() => setIsAnimating(false), 400)
  }

  return (
    <>
      {/* Mobile Menu Button - Floating */}
      {isMobile && !isOpen && onToggle && (
        <button
          className="mobile-sidebar-toggle"
          onClick={onToggle}
          aria-label="Open menu"
        >
          <Menu size={24} />
        </button>
      )}

      {/* Mobile backdrop */}
      {isMobile && isOpen && (
        <div className="sidebar-backdrop" onClick={onClose} />
      )}
      
      <div className={sidebarClasses}>
        {/* Mobile Close Button */}
        {isMobile && isOpen && (
          <button
            className="mobile-close-btn"
            onClick={onClose}
            aria-label="Close menu"
          >
            <X size={24} />
          </button>
        )}
        {/* Logo and Brand */}
        <div className="sidebar-brand">
          {/* Sidebar Toggle Button with Fuze Icon (Desktop only) */}
          {!isMobile && (
            <button
              className={`sidebar-toggle-btn ${isAnimating ? 'animating' : ''}`}
              onClick={handleToggle}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              <img 
                src="/favicon.svg" 
                alt="Fuze" 
                className="fuze-icon-toggle"
                style={{
                  width: '24px',
                  height: '24px',
                  transition: 'all 0.4s cubic-bezier(0.23, 1, 0.32, 1)'
                }}
              />
            </button>
          )}
          {(!collapsed || isMobile) && (
            <div className="brand-text-container" style={{ display: 'flex', flexDirection: 'column', gap: '4px', width: '100%' }}>
              <span className="text-xl font-bold brand-text" style={{ lineHeight: '1.2' }}>
                Fuze
              </span>
              <div className="text-xs font-medium tracking-wider uppercase opacity-80 brand-tagline" style={{ lineHeight: '1.2' }}>
                Intelligence Connected
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <ul className="nav-list">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = isNavItemActive(item)
              
              return (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className={`nav-item ${isActive ? 'nav-item-active' : ''}`}
                    onClick={onClose}
                    title={collapsed && !isMobile ? item.name : undefined} // Tooltip for collapsed state
                  >
                    <Icon className="w-6 h-6" />
                    {(!collapsed || isMobile) && <span>{item.name}</span>}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Footer with User Info */}
        <div className="sidebar-footer">
          <div className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-gray-800/50 transition-colors duration-300 cursor-pointer">
            <div className="w-8 h-8 bg-gradient-to-r from-cyan-500 via-teal-500 to-emerald-500 rounded-full flex items-center justify-center flex-shrink-0">
              <User className="w-5 h-5 text-white" />
            </div>
            {(!collapsed || isMobile) && (
              <div className="text-sm">
                <div className="font-medium text-white truncate">
                  {user?.username || user?.name || 'User'}
                </div>
                <div className="text-gray-400 text-xs">Pro Plan</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

export default Sidebar