import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useState } from 'react'
import { 
  FolderOpen, 
  Home, 
  Sparkles, 
  Plus, 
  Settings, 
  User,
  X,
  Menu
} from 'lucide-react'
import './sidebar-styles.css'

const Sidebar = ({ isOpen, onClose, collapsed, setCollapsed, isMobile }) => {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: Home },
    { name: 'Bookmarks', href: '/bookmarks', icon: Menu }, // Use Menu icon for Bookmarks
    { name: 'Projects', href: '/projects', icon: FolderOpen },
    { name: 'Recommendations', href: '/recommendations', icon: Sparkles },
    { name: 'Save Content', href: '/save-content', icon: Plus },
    { name: 'Profile', href: '/profile', icon: User },
  ]

  if (!isAuthenticated) return null

  // Only add sidebar-open on mobile when open
  const sidebarClass = [
    'sidebar',
    isMobile && isOpen ? 'sidebar-open' : '',
    collapsed ? 'sidebar-collapsed' : 'sidebar-expanded'
  ].join(' ')

  return (
    <>
      {/* Mobile backdrop */}
      {isMobile && isOpen && (
        <div className="sidebar-backdrop" onClick={onClose} />
      )}
      <div
        className={sidebarClass}
        onMouseEnter={() => !isMobile && setCollapsed(false)}
        onMouseLeave={() => !isMobile && setCollapsed(true)}
      >
        {/* Hamburger menu icon and Fuze name at the top */}
        <div className="sidebar-brand">
          <Menu className="sidebar-logo" />
        </div>
        <div className="sidebar-header">
          {/* Hamburger menu on mobile when sidebar is closed */}
          {isMobile && !isOpen && (
            <button className="sidebar-menu-btn" onClick={onClose}>
              <Menu size={20} />
            </button>
          )}
          {/* Only show close button on mobile when sidebar is open */}
          {isMobile && isOpen && (
            <button className="sidebar-close" onClick={onClose}>
              <X size={20} />
            </button>
          )}
        </div>
        <nav className="sidebar-nav">
          <ul className="nav-list">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <li key={item.name}>
                  <Link
                    to={item.href}
                    className={`nav-item ${isActive ? 'nav-item-active' : ''}`}
                    onClick={onClose}
                  >
                    <Icon size={20} />
                    {!collapsed && <span>{item.name}</span>}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>
        <div className="sidebar-footer">
          <Link to="/profile" className="sidebar-profile" onClick={onClose}>
            <User size={20} />
            {!collapsed && <span>Settings</span>}
          </Link>
        </div>
      </div>
    </>
  )
}

export default Sidebar 