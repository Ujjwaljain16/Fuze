import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        background: '#0a0a0a',
        color: '#ffffff'
      }}>
        <div className="loading-spinner"></div>
        <span style={{ marginLeft: '10px' }}>Loading...</span>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}

export default ProtectedRoute 