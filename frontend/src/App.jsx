import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import ProtectedRoute from './components/ProtectedRoute'
import Dashboard from './pages/Dashboard'
import Bookmarks from './pages/Bookmarks'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import Recommendations from './pages/Recommendations'
import SaveContent from './pages/SaveContent'
import Profile from './pages/Profile'
import Login from './pages/Login'
import Register from './pages/Register'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ToastProvider } from './contexts/ToastContext'
import './App.css'

// Component to redirect authenticated users away from auth pages
const AuthRedirect = ({ children }) => {
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
  
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }
  
  return children
}

function AppRoutes() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <Router>
      <Routes>
        {/* Auth pages - rendered outside main layout */}
        <Route path="/login" element={
          <AuthRedirect>
            <Login />
          </AuthRedirect>
        } />
        <Route path="/register" element={
          <AuthRedirect>
            <Register />
          </AuthRedirect>
        } />
        
        {/* Main app routes - rendered inside layout */}
        <Route path="/*" element={
          <ProtectedRoute>
            <div className="app">
              <Navbar onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
              <div className="app-layout">
                <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
                <main className="main-content">
                  <Routes>
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/bookmarks" element={<Bookmarks />} />
                    <Route path="/projects" element={<Projects />} />
                    <Route path="/projects/:id" element={<ProjectDetail />} />
                    <Route path="/recommendations" element={<Recommendations />} />
                    <Route path="/save-content" element={<SaveContent />} />
                    <Route path="/profile" element={<Profile />} />
                  </Routes>
                </main>
              </div>
            </div>
          </ProtectedRoute>
        } />
      </Routes>
    </Router>
  )
}

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppRoutes />
      </ToastProvider>
    </AuthProvider>
  )
}

export default App
