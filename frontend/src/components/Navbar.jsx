import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { LogOut, Menu, X } from 'lucide-react'
import { useState, useEffect } from 'react'
import './navbar-styles.css'

const Navbar = ({ onMenuClick, isSidebarOpen }) => {
  const { isAuthenticated, logout } = useAuth()
  const navigate = useNavigate()
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 900)

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 900)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="navbar">
      <div className="nav-container">
        <div className="nav-left">
          {/* Mobile Menu Button */}
          {isAuthenticated && isMobile && onMenuClick && (
            <button
              onClick={onMenuClick}
              className="mobile-menu-btn"
              aria-label="Toggle menu"
            >
              {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          )}
          <span className="nav-title">Fuze</span>
        </div>
        <div className="nav-right">
          {isAuthenticated && (
            <div className="nav-menu">
              <button onClick={handleLogout} className="nav-link logout-btn">
                <LogOut size={20} />
                {!isMobile && <span>Logout</span>}
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}

export default Navbar 