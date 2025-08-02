import React, { useState, useEffect, createContext, useContext } from 'react';
import Profile from './pages/Profile';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import { ToastProvider } from './contexts/ToastContext';
import { BrowserRouter as Router } from 'react-router-dom';

// Create mock auth context
const MockAuthContext = createContext();

// Mock toast context
const MockToastContext = createContext();

// Mock auth provider for preview
const MockAuthProvider = ({ children }) => {
  const mockAuthValue = {
    isAuthenticated: true,
    user: { 
      id: 1,
      username: 'ujjwaljain16', 
      name: 'Ujjwal Jain',
      email: 'ujjwal@fuze.dev',
      technology_interests: 'React, Node.js, Python, Machine Learning, Web Development',
      created_at: '2024-01-15T10:30:00Z'
    },
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

// Mock toast provider
const MockToastProvider = ({ children }) => {
  const mockToastValue = {
    success: (message) => console.log('Success:', message),
    error: (message) => console.log('Error:', message),
    info: (message) => console.log('Info:', message)
  };

  return (
    <MockToastContext.Provider value={mockToastValue}>
      {children}
    </MockToastContext.Provider>
  );
};

// Mock useAuth hook
const useAuth = () => {
  const context = useContext(MockAuthContext);
  if (!context) {
    return {
      isAuthenticated: true,
      user: { 
        id: 1,
        username: 'ujjwaljain16', 
        name: 'Ujjwal Jain',
        email: 'ujjwal@fuze.dev',
        technology_interests: 'React, Node.js, Python, Machine Learning, Web Development',
        created_at: '2024-01-15T10:30:00Z'
      },
      login: () => Promise.resolve({ success: true }),
      logout: () => {},
      loading: false
    };
  }
  return context;
};

// Mock useToast hook
const useToast = () => {
  const context = useContext(MockToastContext);
  if (!context) {
    return {
      success: (message) => console.log('Success:', message),
      error: (message) => console.log('Error:', message),
      info: (message) => console.log('Info:', message)
    };
  }
  return context;
};

// Override the hooks for Profile
window.useAuth = useAuth;
window.useToast = useToast;

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

  // Add sidebar state class to body
  useEffect(() => {
    document.body.classList.remove('sidebar-collapsed', 'sidebar-expanded');
    
    if (!isMobile) {
      if (collapsed) {
        document.body.classList.add('sidebar-collapsed');
      } else {
        document.body.classList.add('sidebar-expanded');
      }
    }
  }, [collapsed, isMobile]);

  // Sidebar toggle handler
  const handleSidebarToggle = () => {
    if (isMobile) {
      setSidebarOpen(!sidebarOpen);
    } else {
      setCollapsed((prev) => !prev);
    }
  };

  return (
    <Router>
      <MockToastProvider>
        <MockAuthProvider>
          <div className="app">
            <Navbar />
            <div className="app-layout">
              <Sidebar
                isOpen={isMobile ? sidebarOpen : true}
                onClose={() => setSidebarOpen(false)}
                collapsed={!isMobile && collapsed}
                setCollapsed={setCollapsed}
                isMobile={isMobile}
                onToggle={handleSidebarToggle}
              />
              <main className="main-content">
                <Profile />
              </main>
            </div>
          </div>
        </MockAuthProvider>
      </MockToastProvider>
    </Router>
  );
}

export default App;