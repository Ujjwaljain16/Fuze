import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Bookmark, LogOut } from 'lucide-react'
import './navbar-styles.css'

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
        <div className="nav-left">
          <span className="nav-logo"><Bookmark size={24} /></span>
          <span className="nav-title">Fuze</span>
        </div>
        {isAuthenticated && (
          <div className="nav-menu">
            <button onClick={handleLogout} className="nav-link logout-btn">
              <LogOut size={20} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </nav>
  )
}

export default Navbar 