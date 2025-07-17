import { useState } from 'react'
import { Eye, EyeOff, Mail, Lock, Github, Chrome } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import './auth-styles.css'

const Login = () => {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    identifier: '',
    password: ''
  })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')

    // Basic validation
    if (!formData.identifier || !formData.password) {
      setError('Please fill in all fields')
      setLoading(false)
      return
    }

    try {
      // Pass as both username and email for backend compatibility
      const result = await login(formData.identifier, formData.password)
      
      if (result.success) {
        setSuccess('Login successful! Redirecting...')
        setTimeout(() => {
          navigate('/dashboard')
        }, 1000)
      } else {
        setError(result.error || 'Login failed. Please try again.')
      }
    } catch (err) {
      setError('Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSocialLogin = (provider) => {
    // Handle social login logic here
    console.log(`Login with ${provider}`)
  }

  return (
    <div className="auth-container">
      <div className="geometric-bg">
        <div className="geometric-shape shape-1"></div>
        <div className="geometric-shape shape-2"></div>
        <div className="geometric-shape shape-3"></div>
      </div>
      
      <div className="auth-card">
        <div className="auth-header">
          <div className="logo">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <path d="M16 4L28 16L16 28L4 16L16 4Z" fill="currentColor" fillOpacity="0.8"/>
              <path d="M16 8L24 16L16 24L8 16L16 8Z" fill="currentColor"/>
            </svg>
          </div>
          <h1 className="auth-title">Welcome Back</h1>
          <p className="auth-subtitle">Sign in to your account to continue</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="message error-message">{error}</div>}
          {success && <div className="message success-message">{success}</div>}
          
          <div className="form-group">
            <label className="form-label" htmlFor="login-identifier">Username or Email</label>
            <div className="input-wrapper">
              <Mail className="input-icon" size={20} />
              <input
                id="login-identifier"
                type="text"
                name="identifier"
                value={formData.identifier}
                onChange={handleChange}
                className="form-input"
                placeholder="Enter your username or email"
                required
                autoComplete="username"
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="login-password">Password</label>
            <div className="input-wrapper">
              <Lock className="input-icon" size={20} />
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="form-input"
                placeholder="Enter your password"
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="password-toggle"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                tabIndex={0}
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          <button type="submit" className="auth-button" disabled={loading}>
            {loading && <div className="loading-spinner"></div>}
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="divider">
          <span>or continue with</span>
        </div>

        <div className="social-buttons">
          <button 
            className="social-button"
            onClick={() => handleSocialLogin('github')}
            title="Sign in with GitHub"
            aria-label="Sign in with GitHub"
            type="button"
          >
            <Github size={20} />
          </button>
          <button 
            className="social-button"
            onClick={() => handleSocialLogin('google')}
            title="Sign in with Google"
            aria-label="Sign in with Google"
            type="button"
          >
            <Chrome size={20} />
          </button>
          <button 
            className="social-button"
            onClick={() => handleSocialLogin('twitter')}
            title="Sign in with Twitter"
            aria-label="Sign in with Twitter"
            type="button"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M22.46 6c-.77.35-1.6.58-2.46.69.88-.53 1.56-1.37 1.88-2.38-.83.5-1.75.85-2.72 1.05C18.37 4.5 17.26 4 16 4c-2.35 0-4.27 1.92-4.27 4.29 0 .34.04.67.11.98C8.28 9.09 5.11 7.38 3 4.79c-.37.63-.58 1.37-.58 2.15 0 1.49.75 2.81 1.91 3.56-.71 0-1.37-.2-1.95-.5v.03c0 2.08 1.48 3.82 3.44 4.21a4.22 4.22 0 0 1-1.93.07 4.28 4.28 0 0 0 4 2.98 8.521 8.521 0 0 1-5.33 1.84c-.34 0-.68-.02-1.02-.06C3.44 20.29 5.7 21 8.12 21 16 21 20.33 14.46 20.33 8.79c0-.19 0-.37-.01-.56.84-.6 1.56-1.36 2.14-2.23z"/>
            </svg>
          </button>
        </div>

        <div className="auth-footer">
          <p>
            Don't have an account?{' '}
            <Link to="/register" className="auth-link">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default Login