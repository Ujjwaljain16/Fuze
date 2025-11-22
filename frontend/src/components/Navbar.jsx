import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { LogOut } from 'lucide-react'
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
          <span className="nav-title">Fuze</span>
        </div>
        <div className="nav-right">
          {isAuthenticated && (
            <div className="nav-menu">
              <button onClick={handleLogout} className="nav-link logout-btn">
                <LogOut size={20} />
                <span>Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}

export default Navbar 