import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Profile from './pages/Profile';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import Recommendations from './pages/Recommendations';
import Bookmarks from './pages/Bookmarks';
import SaveContent from './pages/SaveContent';
import LinkedIn from './pages/LinkedIn';
import Analytics from './pages/Analytics';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ProtectedRoute from './components/ProtectedRoute';
import './App.css';

function App() {
  const { user, loading } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(true); // Start collapsed by default
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 900);

  // Debug: Log initial state
  console.log('App initial state:', { collapsed, isMobile, sidebarOpen });

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 900);
      if (window.innerWidth > 900) {
        setSidebarOpen(false);
        setCollapsed(false); // Keep expanded on desktop
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Add sidebar state class to body - CRITICAL for layout
  useEffect(() => {
    // Clear all classes first
    document.body.classList.remove('sidebar-collapsed', 'sidebar-expanded');
    
    if (!isMobile) {
      if (collapsed) {
        document.body.classList.add('sidebar-collapsed');
        console.log('Added sidebar-collapsed class to body');
      } else {
        document.body.classList.add('sidebar-expanded');
        console.log('Added sidebar-expanded class to body');
      }
      
      // Force immediate layout recalculation
      document.body.offsetHeight;
      
      // Force a repaint to ensure layout is applied
      window.requestAnimationFrame(() => {
        document.body.offsetHeight;
      });
    }
    
    // Debug: log current body classes
    console.log('Current body classes:', document.body.className);
  }, [collapsed, isMobile]);

  // Ensure initial body class is applied on mount
  useEffect(() => {
    if (!isMobile) {
      // Apply immediately without delay to fix layout
      document.body.classList.add('sidebar-collapsed'); // Start collapsed
      console.log('Initial body class applied on mount - collapsed');
      
      // Force layout recalculation
      document.body.offsetHeight;
    }
  }, []); // Empty dependency array - runs only on mount

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading Fuze...</p>
      </div>
    );
  }

  return (
    <Router>
      <div className="App">
        {user && <Navbar />}
        <div className="app-container">
          {user && (
            <Sidebar
              isOpen={isMobile ? sidebarOpen : true}
              onClose={() => setSidebarOpen(false)}
              collapsed={!isMobile && collapsed}
              setCollapsed={setCollapsed}
              isMobile={isMobile}
            />
          )}
          <main className="main-content">
            <Routes>
              <Route 
                path="/" 
                element={user ? <Navigate to="/dashboard" /> : <Landing />} 
              />
              <Route 
                path="/login" 
                element={user ? <Navigate to="/dashboard" /> : <Login />} 
              />
              <Route 
                path="/dashboard" 
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/profile" 
                element={
                  <ProtectedRoute>
                    <Profile />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/projects" 
                element={
                  <ProtectedRoute>
                    <Projects />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/projects/:id" 
                element={
                  <ProtectedRoute>
                    <ProjectDetail />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/recommendations" 
                element={
                  <ProtectedRoute>
                    <Recommendations />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/bookmarks" 
                element={
                  <ProtectedRoute>
                    <Bookmarks />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/save-content" 
                element={
                  <ProtectedRoute>
                    <SaveContent />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/linkedin" 
                element={
                  <ProtectedRoute>
                    <LinkedIn />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/analytics" 
                element={
                  <ProtectedRoute>
                    <Analytics />
                  </ProtectedRoute>
                } 
              />

              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
}

export default App;
