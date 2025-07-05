import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { 
  Bookmark, 
  FolderOpen, 
  Home, 
  Sparkles, 
  Plus, 
  Settings, 
  User,
  X
} from 'lucide-react'

const Sidebar = ({ isOpen, onClose }) => {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: Home },
    { name: 'Bookmarks', href: '/bookmarks', icon: Bookmark },
    { name: 'Projects', href: '/projects', icon: FolderOpen },
    { name: 'Recommendations', href: '/recommendations', icon: Sparkles },
    { name: 'Save Content', href: '/save-content', icon: Plus },
    { name: 'Profile', href: '/profile', icon: User },
  ]

  if (!isAuthenticated) {
    return null
  }

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div 
          className="sidebar-backdrop"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <div className={`sidebar ${isOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <Bookmark className="sidebar-logo" />
            <span className="sidebar-title">Fuze</span>
          </div>
          <button 
            className="sidebar-close"
            onClick={onClose}
          >
            <X size={20} />
          </button>
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
                    <span>{item.name}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        <div className="sidebar-footer">
          <Link to="/profile" className="sidebar-profile" onClick={onClose}>
            <User size={20} />
            <span>Settings</span>
          </Link>
        </div>
      </div>
    </>
  )
}

export default Sidebar 