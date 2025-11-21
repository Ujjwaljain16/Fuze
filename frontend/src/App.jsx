import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
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
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ProtectedRoute from './components/ProtectedRoute';
import OnboardingModal from './components/OnboardingModal';
import Loader from './components/Loader';
import './App.css';

function AppContent() {
  const { user, loading, isAuthenticated } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(true); // Start collapsed by default
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 900);
  const [showOnboarding, setShowOnboarding] = useState(false);
  
  // Don't show sidebar on landing page or login page
  const showSidebar = user && location.pathname !== '/' && location.pathname !== '/login';

  // Debug: Log initial state (development only)
  if (import.meta.env.DEV) {
    console.log('App initial state:', { collapsed, isMobile, sidebarOpen });
  }

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

  // Check if onboarding should be shown
  useEffect(() => {
    if (isAuthenticated && !loading) {
      const checkAndShowOnboarding = async () => {
        try {
          // Check if user has API key
          const api = (await import('./services/api')).default;
          const response = await api.get('/api/user/api-key/status');
          const hasApiKey = response.data?.has_api_key || false;
          
          // Show onboarding if:
          // 1. User explicitly requested it (show_onboarding flag), OR
          // 2. User doesn't have API key (regardless of completion status - they need to set it up)
          const explicitRequest = localStorage.getItem('show_onboarding') === 'true';
          const notCompleted = localStorage.getItem('onboarding_completed') !== 'true';
          
          // If user doesn't have API key, always show onboarding (reset completion if needed)
          if (!hasApiKey && localStorage.getItem('onboarding_completed') === 'true') {
            localStorage.removeItem('onboarding_completed');
          }
          
          const shouldShow = explicitRequest || (!hasApiKey && notCompleted);
          
          setShowOnboarding(shouldShow);
        } catch (error) {
          // If API check fails, fall back to explicit flag
          const shouldShow = localStorage.getItem('show_onboarding') === 'true' && 
                            localStorage.getItem('onboarding_completed') !== 'true';
          setShowOnboarding(shouldShow);
        }
      };
      
      checkAndShowOnboarding();
    }
  }, [isAuthenticated, loading]);

  // Listen for API key added event and showOnboarding event
  useEffect(() => {
    const handleApiKeyAdded = async () => {
      if (isAuthenticated && !loading) {
        // When API key is added, keep showing onboarding so user can continue to extension step
        // The modal will handle progression to step 2 automatically
        const explicitRequest = localStorage.getItem('show_onboarding') === 'true';
        if (explicitRequest) {
          setShowOnboarding(true);
        }
      }
    };
    
    const handleShowOnboarding = () => {
      if (isAuthenticated && !loading) {
        localStorage.setItem('show_onboarding', 'true');
        localStorage.removeItem('onboarding_completed');
        setShowOnboarding(true);
      }
    };
    
    window.addEventListener('apiKeyAdded', handleApiKeyAdded);
    window.addEventListener('showOnboarding', handleShowOnboarding);
    return () => {
      window.removeEventListener('apiKeyAdded', handleApiKeyAdded);
      window.removeEventListener('showOnboarding', handleShowOnboarding);
    };
  }, [isAuthenticated, loading]);

  // Add sidebar state class to body - CRITICAL for layout
  useEffect(() => {
    // Clear all classes first
    document.body.classList.remove('sidebar-collapsed', 'sidebar-expanded');
    
    if (!isMobile) {
      if (collapsed) {
        document.body.classList.add('sidebar-collapsed');
        if (import.meta.env.DEV) {
          console.log('Added sidebar-collapsed class to body');
        }
      } else {
        document.body.classList.add('sidebar-expanded');
        if (import.meta.env.DEV) {
          console.log('Added sidebar-expanded class to body');
        }
      }
      
      // Force immediate layout recalculation
      document.body.offsetHeight;
      
      // Force a repaint to ensure layout is applied
      window.requestAnimationFrame(() => {
        document.body.offsetHeight;
      });
    }
    
    // Debug: log current body classes (development only)
    if (import.meta.env.DEV) {
      console.log('Current body classes:', document.body.className);
    }
  }, [collapsed, isMobile]);

  // Ensure initial body class is applied on mount
  useEffect(() => {
    if (!isMobile) {
      // Apply immediately without delay to fix layout
      document.body.classList.add('sidebar-collapsed'); // Start collapsed
      if (import.meta.env.DEV) {
        console.log('Initial body class applied on mount - collapsed');
      }
      
      // Force layout recalculation
      document.body.offsetHeight;
    }
  }, []); // Empty dependency array - runs only on mount

  if (loading) {
    return <Loader fullScreen={true} message="Loading Fuze..." size="large" variant="full" />;
  }

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
    localStorage.removeItem('show_onboarding');
  };

  return (
    <div className="App">
      {/* Onboarding Modal */}
      {showOnboarding && (
        <OnboardingModal onComplete={handleOnboardingComplete} />
      )}
      <div className="app-container">
        {showSidebar && (
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
              element={<Landing />} 
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

            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
