import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import Loader from './Loader'

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return <Loader fullScreen={true} message="Loading..." size="large" variant="full" />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}

export default ProtectedRoute 