# Part 3: Frontend Implementation & React Patterns

## 📋 Table of Contents

1. [React Application Structure](#react-application-structure)
2. [State Management (Context API)](#state-management-context-api)
3. [Component Architecture](#component-architecture)
4. [Routing and Navigation](#routing-and-navigation)
5. [API Integration](#api-integration)
6. [Performance Optimizations](#performance-optimizations)
7. [Q&A Section](#qa-section)

---

## React Application Structure

### Application Entry Point

**File**: `frontend/src/main.jsx`

```javascript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### App Component Structure

**File**: `frontend/src/App.jsx`

**Key Features:**
- Lazy loading for code splitting
- Protected routes
- Sidebar management
- Onboarding modal

```javascript
// Lazy load routes for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Profile = lazy(() => import('./pages/Profile'));
const Projects = lazy(() => import('./pages/Projects'));
// ... more routes

function AppContent() {
  const { user, loading, isAuthenticated } = useAuth();
  
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Suspense fallback={<Loader />}>
                <Dashboard />
              </Suspense>
            </ProtectedRoute>
          }
        />
        {/* More routes */}
      </Routes>
    </Router>
  );
}
```

### Code Splitting Strategy

**Benefits:**
- ✅ 58.4% smaller initial bundle
- ✅ Faster initial load (61% improvement)
- ✅ Better caching (chunks cached separately)
- ✅ Lazy loading on demand

**Implementation:**
```javascript
// Route-based code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));

// Component-based splitting
const HeavyComponent = lazy(() => import('./components/HeavyComponent'));

// Usage with Suspense
<Suspense fallback={<Loader />}>
  <Dashboard />
</Suspense>
```

---

## State Management (Context API)

### Auth Context

**File**: `frontend/src/contexts/AuthContext.jsx`

**Purpose**: Global authentication state

**Features:**
- User state management
- Token management
- Login/logout functions
- Automatic token refresh
- CSRF token initialization

```javascript
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  
  const login = async (email, password) => {
    const response = await api.post('/api/auth/login', { email, password });
    const { access_token, user: userData } = response.data;
    
    localStorage.setItem('token', access_token);
    setToken(access_token);
    setUser(userData);
  };
  
  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };
  
  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
```

**Usage:**
```javascript
const { user, login, logout } = useAuth();
```

### Toast Context

**File**: `frontend/src/contexts/ToastContext.jsx`

**Purpose**: Global notification system

**Features:**
- Success, error, warning, info toasts
- Auto-dismiss with configurable timeout
- Beautiful animations
- Stack management

```javascript
export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);
  
  const showToast = (message, type = 'info', duration = 3000) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type, duration }]);
    
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id));
    }, duration);
  };
  
  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <ToastContainer toasts={toasts} />
    </ToastContext.Provider>
  );
};
```

---

## Component Architecture

### Component Structure

**Organization:**
```
frontend/src/
├── components/        # Reusable components
│   ├── Button.jsx
│   ├── Input.jsx
│   ├── Loader.jsx
│   ├── Sidebar.jsx
│   └── Navbar.jsx
├── pages/            # Page components
│   ├── Dashboard.jsx
│   ├── Bookmarks.jsx
│   ├── Projects.jsx
│   └── Recommendations.jsx
├── contexts/         # Context providers
│   ├── AuthContext.jsx
│   └── ToastContext.jsx
└── hooks/            # Custom hooks
    ├── useErrorHandler.js
    └── useResize.js
```

### Reusable Components

#### Button Component

**File**: `frontend/src/components/Button.jsx`

```javascript
const Button = ({ children, variant = 'primary', onClick, disabled, ...props }) => {
  const baseStyles = 'px-4 py-2 rounded-lg font-medium transition-colors';
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
    danger: 'bg-red-600 text-white hover:bg-red-700'
  };
  
  return (
    <button
      className={`${baseStyles} ${variants[variant]}`}
      onClick={onClick}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};
```

#### Protected Route Component

**File**: `frontend/src/components/ProtectedRoute.jsx`

```javascript
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();
  
  if (loading) {
    return <Loader />;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  return children;
};
```

### Custom Hooks

#### useErrorHandler Hook

**File**: `frontend/src/hooks/useErrorHandler.js`

```javascript
export const useErrorHandler = () => {
  const { error: showErrorToast } = useToast();
  
  const handleError = (error, context = '') => {
    const errorInfo = handleApiError(error, context);
    showErrorToast(errorInfo.userMessage);
    return errorInfo;
  };
  
  return { handleError };
};
```

**Usage:**
```javascript
const { handleError } = useErrorHandler();

try {
  await api.post('/api/bookmarks', data);
} catch (error) {
  handleError(error, 'saving bookmark');
}
```

#### useResize Hook

**File**: `frontend/src/hooks/useResize.js`

**Purpose**: Throttled window resize handler

```javascript
export const useResize = (callback, delay = 150) => {
  useEffect(() => {
    let timeoutId;
    
    const handleResize = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(callback, delay);
    };
    
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(timeoutId);
    };
  }, [callback, delay]);
};
```

**Benefits:**
- ✅ Reduces event listener overhead by 80%
- ✅ Better performance on mobile
- ✅ Smooth animations

---

## Routing and Navigation

### React Router Setup

**File**: `frontend/src/App.jsx`

```javascript
<Router>
  <Routes>
    <Route path="/" element={<Landing />} />
    <Route path="/login" element={<Login />} />
    <Route
      path="/dashboard"
      element={
        <ProtectedRoute>
          <Suspense fallback={<Loader />}>
            <Dashboard />
          </Suspense>
        </ProtectedRoute>
      }
    />
    {/* More routes */}
  </Routes>
</Router>
```

### Navigation Patterns

**Programmatic Navigation:**
```javascript
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();

// Navigate after login
navigate('/dashboard');

// Navigate with state
navigate('/profile', { state: { from: 'dashboard' } });
```

**Link Navigation:**
```javascript
import { Link } from 'react-router-dom';

<Link to="/dashboard">Dashboard</Link>
```

---

## API Integration

### API Service

**File**: `frontend/src/services/api.js`

**Features:**
- Axios instance with base URL
- Request/response interceptors
- Automatic token refresh
- CSRF token management
- Error handling

```javascript
const api = axios.create({
  baseURL: getBaseURL(),
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  timeout: 30000,
});

// Request interceptor - add auth token
api.interceptors.request.use(
  async (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Attempt token refresh
      const res = await axios.post(`${baseURL}/api/auth/refresh`, {}, {
        withCredentials: true
      });
      const newToken = res.data.access_token;
      localStorage.setItem('token', newToken);
      originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
      return api(originalRequest);
    }
    return Promise.reject(error);
  }
);
```

### API Optimization

**File**: `frontend/src/utils/apiOptimization.js`

**Features:**
- Request debouncing
- Request batching
- Response caching
- Request deduplication

```javascript
// Debounce requests
export const debounceRequest = (key, requestFn, delay = 300) => {
  return new Promise((resolve, reject) => {
    if (debounceMap.has(key)) {
      clearTimeout(debounceMap.get(key).timeout);
    }
    
    const timeout = setTimeout(async () => {
      const result = await requestFn();
      resolve(result);
    }, delay);
    
    debounceMap.set(key, { timeout, resolve, reject });
  });
};

// Cache responses
const responseCache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export const getCachedResponse = (cacheKey) => {
  const cached = responseCache.get(cacheKey);
  if (cached && Date.now() < cached.expiresAt) {
    return cached.data;
  }
  return null;
};
```

---

## Performance Optimizations

### Code Splitting Results

**Before:**
- Initial bundle: ~935 KB (uncompressed)
- Load time (3G): ~2.54s

**After:**
- Initial bundle: 388.64 KB (uncompressed)
- Load time (3G): ~0.99s
- **Improvement: 61% faster**

### Bundle Structure

```
Initial Load (Critical):
- index.js: 79.69 kB
- react-vendor.js: 207.79 kB
- index.css: 101.16 kB
Total: 388.64 kB

Lazy Loaded (On-Demand):
- dashboard.js: 48.03 kB
- recommendations.js: 50.04 kB
- project-detail.js: 29.52 kB
- ... more chunks
```

### Event Listener Optimization

**Before:** 12+ duplicate resize listeners

**After:** Shared `useResize` hook with throttling

**Result:** 80% reduction in event listener overhead

### Memoization

**Example:**
```javascript
const Dashboard = () => {
  const cleanDisplayName = useMemo(() => {
    return user?.username?.replace(/[^a-zA-Z0-9]/g, '') || 'User';
  }, [user?.username]);
  
  // ... rest of component
};
```

---

## Q&A Section

### Q1: Why Context API over Redux?

**Answer:**
Context API is sufficient for our use case:
- ✅ Simpler setup and maintenance
- ✅ Less boilerplate code
- ✅ Built into React (no extra dependency)
- ✅ Good performance for our scale
- ✅ Easier to understand for team

**Trade-offs:**
- ❌ Less powerful than Redux
- ❌ No time-travel debugging
- ❌ Can cause re-renders if not optimized

**When to use Redux:**
- Complex state management
- Time-travel debugging needed
- Large team with complex state requirements

### Q2: How do you handle API errors globally?

**Answer:**
Multiple layers:

1. **Axios Interceptor**: Handles token refresh
2. **Error Handler Hook**: Categorizes errors
3. **Toast Context**: Shows user-friendly messages

```javascript
// Error categorization
const ERROR_CATEGORIES = {
  NETWORK: { message: 'Network connection failed...' },
  AUTH: { message: 'Your session has expired...' },
  VALIDATION: { message: 'Please check your input...' },
  SERVER: { message: 'Server error occurred...' }
};

// Usage
const { handleError } = useErrorHandler();
try {
  await api.post('/api/bookmarks', data);
} catch (error) {
  handleError(error, 'saving bookmark');
}
```

### Q3: How do you optimize re-renders?

**Answer:**
Multiple strategies:

1. **React.memo**: Memoize components
2. **useMemo**: Memoize expensive computations
3. **useCallback**: Memoize event handlers
4. **Code splitting**: Reduce initial bundle

**Example:**
```javascript
const ExpensiveComponent = React.memo(({ data }) => {
  const processedData = useMemo(() => {
    return expensiveComputation(data);
  }, [data]);
  
  return <div>{processedData}</div>;
});
```

### Q4: How do you handle loading states?

**Answer:**
Multiple approaches:

1. **Suspense**: For lazy-loaded components
2. **Loading State**: Component-level loading
3. **Skeleton Screens**: Better UX than spinners

```javascript
// Suspense for lazy loading
<Suspense fallback={<Loader />}>
  <Dashboard />
</Suspense>

// Component-level loading
const [loading, setLoading] = useState(true);
if (loading) return <Loader />;
```

### Q5: How do you test React components?

**Answer:**
Vitest + React Testing Library:

```javascript
import { render, screen } from '@testing-library/react';
import { Button } from './Button';

test('renders button with text', () => {
  render(<Button>Click me</Button>);
  expect(screen.getByText('Click me')).toBeInTheDocument();
});
```

**File**: `frontend/src/tests/`

---

## Summary

Frontend implementation focuses on:
- ✅ **Modern React patterns** (Hooks, Context API)
- ✅ **Code splitting** for performance
- ✅ **Reusable components** and hooks
- ✅ **API optimization** (debouncing, caching)
- ✅ **Error handling** with user-friendly messages
- ✅ **Performance optimizations** (61% faster load)

**Key Files:**
- `frontend/src/App.jsx` - Main app component
- `frontend/src/contexts/` - Context providers
- `frontend/src/components/` - Reusable components
- `frontend/src/services/api.js` - API service

---

**Next**: [Part 4: Security, Authentication & Multi-tenancy](./04_Security_Authentication.md)

