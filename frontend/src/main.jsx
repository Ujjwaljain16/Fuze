import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { AuthProvider } from './contexts/AuthContext'
import { ToastProvider } from './contexts/ToastContext'
import ErrorBoundary from './components/ErrorBoundary.jsx'

// PWA Service Worker Registration
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    // Check if service worker file exists before registering
    fetch('/sw.js')
      .then(response => {
        if (response.ok) {
          return navigator.serviceWorker.register('/sw.js');
        } else {
          throw new Error('Service worker file not found');
        }
      })
      .then((registration) => {
        if (import.meta.env.DEV) {
          console.log('Service Worker registered successfully:', registration.scope);
        }
        
        // Check for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              if (import.meta.env.DEV) {
                console.log('New version available!');
              }
              // You can show a notification to the user here
            }
          });
        });
      })
      .catch((error) => {
        // Don't show error for missing service worker - it's optional
        if (error.message !== 'Service worker file not found') {
          console.warn('Service Worker not available:', error.message);
        }
      });
  });
}

// PWA Install Prompt
// eslint-disable-next-line no-unused-vars
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  if (import.meta.env.DEV) {
    console.log('PWA install prompt ready');
  }
});

// Handle PWA installation
window.addEventListener('appinstalled', () => {
  if (import.meta.env.DEV) {
    console.log('PWA installed successfully');
  }
  deferredPrompt = null;
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ToastProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ToastProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
