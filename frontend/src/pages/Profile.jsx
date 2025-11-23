import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { Link } from 'react-router-dom'
import api from '../services/api'
import logo1 from '../assets/logo1.svg'
import { Zap, LogOut } from 'lucide-react'
import ProfileHeader from '../components/ProfileHeader'
import ProfileStats from '../components/ProfileStats'
import ProfileForm from '../components/ProfileForm'
import PasswordForm from '../components/PasswordForm'
import AccountActions from '../components/AccountActions'
import ApiKeyManager from '../components/ApiKeyManager'

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
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768)
  const [isSmallMobile, setIsSmallMobile] = useState(window.innerWidth <= 480)

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768)
      setIsSmallMobile(window.innerWidth <= 480)
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
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
      <div className="min-h-screen text-white relative overflow-hidden flex items-center justify-center" style={{ backgroundColor: '#0F0F1E' }}>
        {/* Animated Background */}
        <div className="fixed inset-0 opacity-10">
          <div 
            className="absolute w-96 h-96 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(77, 208, 225, 0.3) 0%, transparent 70%)',
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
                className="border border-cyan-500/10 animate-pulse"
                style={{
                  animationDelay: `${Math.random() * 5}s`,
                  animationDuration: `${4 + Math.random() * 3}s`
                }}
              />
            ))}
          </div>
        </div>

        <div className="relative z-10 text-center">
          <div className={`flex items-center justify-center ${isSmallMobile ? 'gap-2' : 'space-x-3'} ${isMobile ? 'mb-3' : 'mb-4'}`}>
            <div className="relative">
              <Zap className={`${isMobile ? 'w-8 h-8' : 'w-12 h-12'} text-cyan-400`} />
              <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-50 animate-pulse" />
            </div>
            <span className={`${isMobile ? 'text-2xl' : 'text-4xl'} font-bold bg-gradient-to-r from-cyan-400 via-teal-400 to-emerald-400 bg-clip-text text-transparent`}>
              Fuze
            </span>
          </div>
          <h2 className={`${isMobile ? 'text-xl' : 'text-2xl'} font-bold text-white ${isMobile ? 'mb-3' : 'mb-4'}`}>Authentication Required</h2>
          <p className={`text-gray-300 ${isMobile ? 'text-sm' : ''}`}>Please log in to access your profile.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen text-white relative overflow-hidden" style={{ backgroundColor: '#0F0F1E' }}>
      {/* Animated Background */}
      <div className="fixed inset-0 opacity-10">
        <div 
          className="absolute w-96 h-96 rounded-full"
          style={{
            background: 'radial-gradient(circle, rgba(77, 208, 225, 0.3) 0%, transparent 70%)',
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
              className="border border-cyan-500/10 animate-pulse"
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
        <div className="w-full">
          <main className={`${isMobile ? 'p-4' : 'p-4 md:p-6 lg:p-8'} max-w-[1600px] mx-auto`} style={{ backgroundColor: '#0F0F1E' }}>
            {/* Header with Logo and Logout */}
            <div className={`flex items-center justify-between ${isMobile ? 'mb-6 pt-2' : 'mb-8 pt-6'} ${isSmallMobile ? 'flex-col gap-4' : ''} ${isMobile ? 'mt-12' : ''}`}>
              {/* Logo - Top Left (Home Link) */}
              <Link
                to="/"
                className="logo-container"
                style={{ 
                  cursor: 'pointer'
                }}
              >
                <img 
                  src={logo1} 
                  alt="FUZE Logo"
                  style={{
                    backgroundColor: 'transparent',
                    mixBlendMode: 'normal'
                  }}
                />
              </Link>

              {/* Logout Button - Top Right */}
              <button
                onClick={() => {
                  logout()
                  window.location.href = '/login'
                }}
                className={`flex items-center gap-2.5 ${isMobile ? 'px-4 py-2' : 'px-5 py-3'} rounded-xl transition-all duration-300 group`}
                style={{
                  background: 'rgba(20, 20, 20, 0.6)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  backdropFilter: 'blur(10px)',
                  color: '#9ca3af'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.5)'
                  e.currentTarget.style.background = 'rgba(30, 20, 20, 0.8)'
                  e.currentTarget.style.color = '#ef4444'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 4px 16px rgba(239, 68, 68, 0.3)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.2)'
                  e.currentTarget.style.background = 'rgba(20, 20, 20, 0.6)'
                  e.currentTarget.style.color = '#9ca3af'
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <LogOut className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'} group-hover:translate-x-1 transition-transform duration-300`} />
                {!isSmallMobile && <span className={`${isMobile ? 'text-sm' : 'text-base'} font-medium`}>Logout</span>}
              </button>
            </div>
          {/* Profile Header */}
          <ProfileHeader user={user} />

          {/* Profile Stats */}
          <ProfileStats user={user} />

          {/* Main Content Grid */}
          <div className={`grid grid-cols-1 ${isMobile ? 'gap-6' : 'lg:grid-cols-2 gap-8'} ${isMobile ? 'mb-6' : 'mb-8'}`}>
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

          {/* API Key Management */}
          <div className="mb-8">
            <ApiKeyManager />
          </div>

          {/* Account Actions */}
          <AccountActions onLogout={handleLogout} />
        </main>
      </div>
      </div>

      <style jsx>{`
        .logo-container {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
          background: transparent;
          border: none;
          box-shadow: none;
          transition: transform 0.3s ease;
          padding: 0;
          clip-path: circle(50% at 50% 50%);
          -webkit-clip-path: circle(50% at 50% 50%);
          position: relative;
        }
        
        .logo-container:hover {
          transform: scale(1.05) !important;
        }
        
        .logo-container img {
          width: 100%;
          height: 100%;
          object-fit: contain;
          clip-path: circle(50% at 50% 50%);
          -webkit-clip-path: circle(50% at 50% 50%);
          mix-blend-mode: normal;
        }
        
        @media (max-width: 768px) {
          .logo-container {
            width: 90px;
            height: 90px;
            padding: 0;
          }
        }
        
        @media (max-width: 480px) {
          .logo-container {
            width: 70px;
            height: 70px;
            padding: 0;
          }
        }
      `}</style>
    </div>
  )
}

export default Profile