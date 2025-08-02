import React, { useState, useEffect, createContext, useContext } from 'react';
import Dashboard from './pages/Dashboard';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import { ToastProvider } from './contexts/ToastContext';
import { BrowserRouter as Router } from 'react-router-dom';

// Create mock auth context
const MockAuthContext = createContext();

// Mock auth provider for preview
const MockAuthProvider = ({ children }) => {
  const mockAuthValue = {
    isAuthenticated: true,
    user: { username: 'ujjwaljain16', name: 'Ujjwal Jain' },
    login: () => Promise.resolve({ success: true }),
    logout: () => {},
    loading: false
  };

  return (
    <MockAuthContext.Provider value={mockAuthValue}>
      {children}
    </MockAuthContext.Provider>
  );
};

// Mock useAuth hook
const useAuth = () => {
  const context = useContext(MockAuthContext);
  if (!context) {
    return {
      isAuthenticated: true,
      user: { username: 'ujjwaljain16', name: 'Ujjwal Jain' },
      login: () => Promise.resolve({ success: true }),
      logout: () => {},
      loading: false
    };
  }
  return context;
};

// Override the useAuth import for Dashboard
window.useAuth = useAuth;

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(true);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 900);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 900);
      if (window.innerWidth > 900) {
        setSidebarOpen(false);
        setCollapsed(true);
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
        console.log('Added sidebar-collapsed class');
      } else {
        document.body.classList.add('sidebar-expanded');
        console.log('Added sidebar-expanded class');
      }
    }
  }, [collapsed, isMobile]);

  // Debug: Log state changes
  useEffect(() => {
    console.log('Sidebar state:', { collapsed, isMobile, sidebarOpen });
  }, [collapsed, isMobile, sidebarOpen]);

  // Hamburger menu click handler
  const handleMenuClick = () => {
    if (isMobile) {
      setSidebarOpen(!sidebarOpen);
    } else {
      setCollapsed((prev) => !prev);
    }
  };

  return (
    <Router>
      <ToastProvider>
        <MockAuthProvider>
          <div className="app">
            <Navbar onMenuClick={handleMenuClick} />
            <div className="app-layout">
              <Sidebar
                isOpen={isMobile ? sidebarOpen : true}
                onClose={() => setSidebarOpen(false)}
                collapsed={!isMobile && collapsed}
                setCollapsed={setCollapsed}
                isMobile={isMobile}
              />
              <main className="main-content">
                <Dashboard />
              </main>
            </div>
          </div>
        </MockAuthProvider>
      </ToastProvider>
    </Router>
  );
}

export default App;