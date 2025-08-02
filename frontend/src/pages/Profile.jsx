import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import api from '../services/api'
import { Zap } from 'lucide-react'
import ProfileHeader from '../components/ProfileHeader'
import ProfileStats from '../components/ProfileStats'
import ProfileForm from '../components/ProfileForm'
import PasswordForm from '../components/PasswordForm'
import AccountActions from '../components/AccountActions'

const Profile = () => {
  const { isAuthenticated, user, logout } = useAuth()
  const { success, error } = useToast()
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [formData, setFormData] = useState({
    username: '',
    technology_interests: '',
    current_password: '',
    new_password: '',
    confirm_password: ''
  })

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

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
      <div className="min-h-screen bg-black text-white relative overflow-hidden flex items-center justify-center">
        {/* Animated Background */}
        <div className="fixed inset-0 opacity-10">
          <div 
            className="absolute w-96 h-96 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, transparent 70%)',
              left: mousePos.x - 192,
              top: mousePos.y - 192,
              transition: 'all 0.3s ease-out'
            }}
          />
        </div>

        {/* Lightning Grid Background */}
        <div className="fixed inset-0 opacity-5">
          <div className="grid grid-cols-24 grid-rows-24 h-full w-full">
            {Array.from({ length: 576 }).map((_, i) => (
              <div
                key={i}
                className="border border-blue-500/10 animate-pulse"
                style={{
                  animationDelay: `${Math.random() * 5}s`,
                  animationDuration: `${4 + Math.random() * 3}s`
                }}
              />
            ))}
          </div>
        </div>

        <div className="relative z-10 text-center">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <div className="relative">
              <Zap className="w-12 h-12 text-blue-400" />
              <div className="absolute inset-0 blur-lg bg-blue-400 opacity-50 animate-pulse" />
            </div>
            <span className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Fuze
            </span>
          </div>
          <h2 className="text-2xl font-bold text-white mb-4">Authentication Required</h2>
          <p className="text-gray-300">Please log in to access your profile.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 opacity-10">
        <div 
          className="absolute w-96 h-96 rounded-full"
          style={{
            background: 'radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, transparent 70%)',
            left: mousePos.x - 192,
            top: mousePos.y - 192,
            transition: 'all 0.3s ease-out'
          }}
        />
      </div>
      
      {/* Lightning Grid Background */}
      <div className="fixed inset-0 opacity-5">
        <div className="grid grid-cols-24 grid-rows-24 h-full w-full">
          {Array.from({ length: 576 }).map((_, i) => (
            <div
              key={i}
              className="border border-blue-500/10 animate-pulse"
              style={{
                animationDelay: `${Math.random() * 5}s`,
                animationDuration: `${4 + Math.random() * 3}s`
              }}
            />
          ))}
        </div>
      </div>

      <div className="relative z-10">
        {/* Main Content */}
        <main className="ml-12 md:ml-16 lg:ml-20 p-4 md:p-6 lg:p-8">
          {/* Profile Header */}
          <ProfileHeader user={user} />

          {/* Profile Stats */}
          <ProfileStats user={user} />

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            {/* Profile Form */}
            <ProfileForm
              formData={formData}
              onInputChange={handleInputChange}
              onSubmit={handleProfileUpdate}
              loading={loading}
            />

            {/* Password Form */}
            <PasswordForm
              formData={formData}
              onInputChange={handleInputChange}
              onSubmit={handlePasswordChange}
              loading={loading}
              showPassword={showPassword}
              setShowPassword={setShowPassword}
            />
          </div>

          {/* Account Actions */}
          <AccountActions onLogout={handleLogout} />
        </main>
      </div>
    </div>
  )
}

export default Profile