import React from 'react';
import Login from './pages/Login';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { BrowserRouter as Router } from 'react-router-dom';

function App() {
  return (
    <Router>
      <AuthProvider>
        <ToastProvider>
          <div className="min-h-screen">
            <Login />
          </div>
        </ToastProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;