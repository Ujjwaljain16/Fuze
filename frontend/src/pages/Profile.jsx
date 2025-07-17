import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import api from '../services/api'
import { User, Settings, Save, LogOut, Eye, EyeOff } from 'lucide-react'
import './profile-styles.css'

const Profile = () => {
  const { isAuthenticated, user, logout } = useAuth()
  const { success, error } = useToast()
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({
    username: '',
    technology_interests: '',
    current_password: '',
    new_password: '',
    confirm_password: ''
  })

  useEffect(() => {
    if (isAuthenticated && user) {
      setFormData(prev => ({
        ...prev,
        username: user.username || '',
        technology_interests: user.technology_interests || ''
      }))
    }
  }, [isAuthenticated, user])

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleProfileUpdate = async (e) => {
    e.preventDefault()
    
    if (!formData.username.trim()) {
      error('Username is required')
      return
    }

    setLoading(true)
    try {
      const updateData = {
        username: formData.username.trim(),
        technology_interests: formData.technology_interests.trim()
      }

      const response = await api.put(`/api/users/${user.id}`, updateData)
      
      if (response.data) {
        success('Profile updated successfully!')
        // Update local user data if needed
      }
    } catch (err) {
      console.error('Error updating profile:', err)
      if (err.response?.data?.message) {
        error(err.response.data.message)
      } else {
        error('Failed to update profile. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    
    if (!formData.current_password || !formData.new_password || !formData.confirm_password) {
      error('All password fields are required')
      return
    }

    if (formData.new_password !== formData.confirm_password) {
      error('New passwords do not match')
      return
    }

    if (formData.new_password.length < 6) {
      error('New password must be at least 6 characters long')
      return
    }

    setLoading(true)
    try {
      const passwordData = {
        current_password: formData.current_password,
        new_password: formData.new_password
      }

      const response = await api.put(`/api/users/${user.id}/password`, passwordData)
      
      if (response.data) {
        success('Password changed successfully!')
        // Clear password fields
        setFormData(prev => ({
          ...prev,
          current_password: '',
          new_password: '',
          confirm_password: ''
        }))
      }
    } catch (err) {
      console.error('Error changing password:', err)
      if (err.response?.data?.message) {
        error(err.response.data.message)
      } else {
        error('Failed to change password. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    logout()
    success('Logged out successfully!')
  }

  if (!isAuthenticated) {
    return (
      <div className="container">
        <div className="auth-required">
          <h2>Authentication Required</h2>
          <p>Please log in to access your profile.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="page-header">
        <div className="page-title">
          <User className="page-icon" />
          <h1>My Profile</h1>
        </div>
        <p className="page-subtitle">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="profile-content">
        {/* Profile Information */}
        <div className="profile-section">
          <div className="section-header">
            <h2>Profile Information</h2>
          </div>
          
          <form onSubmit={handleProfileUpdate} className="form">
            <div className="form-group">
              <label htmlFor="username" className="form-label">
                Username
              </label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                className="form-input"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="technology_interests" className="form-label">
                Technology Interests
              </label>
              <textarea
                id="technology_interests"
                name="technology_interests"
                value={formData.technology_interests}
                onChange={handleInputChange}
                placeholder="e.g., React, Python, Machine Learning, Web Development"
                className="form-input form-textarea"
                rows={3}
              />
              <small className="form-help">
                This helps us provide better recommendations for you
              </small>
            </div>

            <div className="form-actions">
              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
              >
                <Save size={16} />
                {loading ? 'Updating...' : 'Update Profile'}
              </button>
            </div>
          </form>
        </div>

        {/* Change Password */}
        <div className="profile-section">
          <div className="section-header">
            <h2>Change Password</h2>
          </div>
          
          <form onSubmit={handlePasswordChange} className="form">
            <div className="form-group">
              <label htmlFor="current_password" className="form-label">
                Current Password
              </label>
              <div className="password-input-group">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="current_password"
                  name="current_password"
                  value={formData.current_password}
                  onChange={handleInputChange}
                  className="form-input"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="password-toggle"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="new_password" className="form-label">
                New Password
              </label>
              <input
                type={showPassword ? 'text' : 'password'}
                id="new_password"
                name="new_password"
                value={formData.new_password}
                onChange={handleInputChange}
                className="form-input"
                required
                minLength={6}
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirm_password" className="form-label">
                Confirm New Password
              </label>
              <input
                type={showPassword ? 'text' : 'password'}
                id="confirm_password"
                name="confirm_password"
                value={formData.confirm_password}
                onChange={handleInputChange}
                className="form-input"
                required
                minLength={6}
              />
            </div>

            <div className="form-actions">
              <button
                type="submit"
                disabled={loading}
                className="btn btn-secondary"
              >
                {loading ? 'Changing...' : 'Change Password'}
              </button>
            </div>
          </form>
        </div>

        {/* Account Actions */}
        <div className="profile-section">
          <div className="section-header">
            <h2>Account Actions</h2>
          </div>
          
          <div className="account-actions">
            <button
              onClick={handleLogout}
              className="btn btn-error"
            >
              <LogOut size={16} />
              Logout
            </button>
          </div>
        </div>

        {/* Account Statistics */}
        <div className="profile-section">
          <div className="section-header">
            <h2>Account Statistics</h2>
          </div>
          
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">
                <User />
              </div>
              <div className="stat-content">
                <h3>Member Since</h3>
                <p>{user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</p>
              </div>
            </div>
            
            <div className="stat-card">
              <div className="stat-icon">
                <Settings />
              </div>
              <div className="stat-content">
                <h3>Account Status</h3>
                <p>Active</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Profile 