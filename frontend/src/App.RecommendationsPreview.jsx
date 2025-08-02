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

import FuzeLanding from './pages/Landing'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ToastProvider } from './contexts/ToastContext'

// Mock Auth Context for Preview
const MockAuthProvider = ({ children }) => {
  const mockAuthValue = {
    isAuthenticated: true,
    user: { username: 'demo_user', name: 'Demo User' },
    loading: false,
    login: () => {},
    logout: () => {},
    register: () => {}
  }

  return (
    <div style={{ 
      '--auth-context': JSON.stringify(mockAuthValue)
    }}>
      {children}
    </div>
  )
}

// Mock Toast Context for Preview
const MockToastProvider = ({ children }) => {
  return <div>{children}</div>
}

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
    return <Navigate to="/app/dashboard" replace />
  }
  
  return children
}

function AppRoutes() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(true)
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 900)

  useEffect(() => {
    const handleResize = () => {
      const newIsMobile = window.innerWidth <= 900
      setIsMobile(newIsMobile)
      
      // Reset sidebar state on resize
      if (newIsMobile) {
        setSidebarOpen(false)
        setCollapsed(true)
      } else {
        setSidebarOpen(false)
        // Keep collapsed state for desktop
      }
    }
    
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Add sidebar state class to body
  useEffect(() => {
    if (isMobile) {
      document.body.classList.remove('sidebar-collapsed', 'sidebar-expanded')
    } else {
      if (collapsed) {
        document.body.classList.remove('sidebar-expanded')
        document.body.classList.add('sidebar-collapsed')
      } else {
        document.body.classList.remove('sidebar-collapsed')
        document.body.classList.add('sidebar-expanded')
      }
    }
  }, [collapsed, isMobile])

  return (
    <Router>
      <Routes>
        {/* Landing page - accessible to all */}
        <Route path="/" element={<FuzeLanding />} />
        
        {/* Auth pages - rendered outside main layout */}
        <Route path="/login" element={
          <AuthRedirect>
            <Login />
          </AuthRedirect>
        } />

        
        {/* Main app routes - rendered inside layout */}
        <Route path="/app/*" element={
          <ProtectedRoute>
            <div className="app">
              <Navbar />
              <div className="app-layout">
                <Sidebar
                  isOpen={isMobile ? sidebarOpen : true}
                  onClose={() => setSidebarOpen(false)}
                  collapsed={!isMobile && collapsed}
                  setCollapsed={setCollapsed}
                  isMobile={isMobile}
                />
                <main className="main-content">
                  <Routes>
                    <Route path="/" element={<Navigate to="/recommendations" replace />} />
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
    <MockAuthProvider>
      <MockToastProvider>
        <AppRoutes />
      </MockToastProvider>
    </MockAuthProvider>
  )
}

export default App