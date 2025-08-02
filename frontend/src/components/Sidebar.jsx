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
  Zap,
  PanelLeftOpen,
  PanelLeftClose
} from 'lucide-react'
import './sidebar-styles.css'

const Sidebar = ({ isOpen, onClose, collapsed, setCollapsed, isMobile }) => {
  const { isAuthenticated, user } = useAuth()
  const location = useLocation()

  const navigation = [
    { name: 'Dashboard', href: '/app/dashboard', icon: Grid3X3 },
    { name: 'All Bookmarks', href: '/app/bookmarks', icon: Bookmark },
    { name: 'Projects', href: '/app/projects', icon: FolderOpen },
    { name: 'Save Content', href: '/app/save-content', icon: Plus },
    { name: 'Recommendations', href: '/app/recommendations', icon: Sparkles },
    { name: 'Settings', href: '/app/profile', icon: Settings },
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

  if (!isAuthenticated) return null

  // Clean class name construction with proper state management
  const sidebarClasses = [
    'sidebar',
    isMobile && isOpen ? 'sidebar-open' : '',
    !isMobile && collapsed ? 'sidebar-collapsed' : '',
    !isMobile && !collapsed ? 'sidebar-expanded' : ''
  ].filter(Boolean).join(' ')

  // Debug logging
  // console.log('Sidebar classes:', sidebarClasses, { isMobile, isOpen, collapsed });

  return (
    <>
      {/* Mobile backdrop */}
      {isMobile && isOpen && (
        <div className="sidebar-backdrop" onClick={onClose} />
      )}
      
      <div className={sidebarClasses}>
        {/* Sidebar Toggle Button (Desktop only) */}
        {!isMobile && (
          <button
            className="sidebar-toggle-btn"
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            style={{
              position: 'absolute',
              top: 18,
              left: collapsed ? 12 : 18,
              zIndex: 10,
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 4,
              borderRadius: 8,
              transition: 'left 0.3s',
            }}
          >
            {collapsed ? <PanelLeftOpen size={22} /> : <PanelLeftClose size={22} />}
          </button>
        )}
        {/* Logo and Brand */}
        <div className="sidebar-brand" style={{ paddingLeft: !isMobile && collapsed ? 0 : 40 }}>
          <div className="flex items-center space-x-3">
            <div className="relative">
              <Zap className="w-10 h-10 text-blue-400" />
              <div className="absolute inset-0 blur-lg bg-blue-400 opacity-50 animate-pulse" />
            </div>
            {(!collapsed || isMobile) && (
              <div>
                <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                  Fuze
                </span>
                <div className="text-xs text-blue-300 font-medium tracking-wider uppercase opacity-80">
                  Strike Through the Chaos
                </div>
              </div>
            )}
          </div>
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
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center flex-shrink-0">
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