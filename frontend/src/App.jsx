import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Bookmarks from './pages/Bookmarks'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import Recommendations from './pages/Recommendations'
import SaveContent from './pages/SaveContent'
import Profile from './pages/Profile'
import Login from './pages/Login'
import Register from './pages/Register'
import { AuthProvider } from './contexts/AuthContext'
import { ToastProvider } from './contexts/ToastContext'
import './App.css'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <AuthProvider>
      <ToastProvider>
        <Router>
          <Routes>
            {/* Auth pages - rendered outside main layout */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            {/* Main app routes - rendered inside layout */}
            <Route path="/*" element={
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
            } />
          </Routes>
        </Router>
      </ToastProvider>
    </AuthProvider>
  )
}

export default App
