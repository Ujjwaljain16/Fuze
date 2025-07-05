import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Bookmark, FolderOpen, Home, LogOut, User } from 'lucide-react'

const Navbar = () => {
  const { isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="navbar">
      <div className="nav-container">
        <Link to="/" className="nav-brand">
          <Bookmark className="nav-logo" />
          <span>Fuze</span>
        </Link>

        {isAuthenticated ? (
          <div className="nav-menu">
            <Link to="/" className="nav-link">
              <Home size={20} />
              <span>Dashboard</span>
            </Link>
            <Link to="/bookmarks" className="nav-link">
              <Bookmark size={20} />
              <span>Bookmarks</span>
            </Link>
            <Link to="/projects" className="nav-link">
              <FolderOpen size={20} />
              <span>Projects</span>
            </Link>
            <button onClick={handleLogout} className="nav-link logout-btn">
              <LogOut size={20} />
              <span>Logout</span>
            </button>
          </div>
        ) : (
          <div className="nav-menu">
            <Link to="/login" className="nav-link">
              <User size={20} />
              <span>Login</span>
            </Link>
          </div>
        )}
      </div>
    </nav>
  )
}

export default Navbar 