import React, { useState, useEffect, useRef } from 'react';
import { Zap, Mail, Lock, User, Eye, EyeOff, ArrowRight, Home, AlertTriangle } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Button from '../components/Button';
import Input from '../components/Input';
import AuthToggle from '../components/AuthToggle';

export default function FuzeAuth() {
  const [searchParams] = useSearchParams();
  const initialMode = searchParams.get('mode') === 'signup' ? false : true;
  const [isLogin, setIsLogin] = useState(initialMode);
  const [showPassword, setShowPassword] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [formData, setFormData] = useState({
    name: '',
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [passwordErrors, setPasswordErrors] = useState({});
  const [passwordStrength, setPasswordStrength] = useState({
    score: 0,
    label: '',
    color: ''
  });
  const [passwordsMatch, setPasswordsMatch] = useState(null);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [isSmallMobile, setIsSmallMobile] = useState(window.innerWidth <= 480);
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const submitRef = useRef(false); // Prevent duplicate submissions

  useEffect(() => {
    setIsVisible(true);
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
      setIsSmallMobile(window.innerWidth <= 480);
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('resize', handleResize);
    handleResize(); // Check initial size
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  // Password validation functions
  const validatePasswordStrength = (password) => {
    const errors = {};
    let score = 0;

    if (password.length < 8) {
      errors.length = 'At least 8 characters';
    } else {
      score += 1;
    }

    if (!/[A-Za-z]/.test(password)) {
      errors.letter = 'At least one letter';
    } else {
      score += 1;
    }

    if (!/\d/.test(password)) {
      errors.number = 'At least one number';
    } else {
      score += 1;
    }

    // Optional: special character check
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      errors.special = 'At least one special character';
    } else {
      score += 1;
    }

    // Check for common patterns (bonus points)
    if (password.length >= 12) score += 1;
    if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1;

    let label, color;
    if (score < 3) {
      label = 'Weak';
      color = '#ef4444'; // red
    } else if (score < 5) {
      label = 'Fair';
      color = '#f59e0b'; // amber
    } else if (score < 7) {
      label = 'Good';
      color = '#3b82f6'; // blue
    } else {
      label = 'Strong';
      color = '#22c55e'; // green
    }

    return { errors, strength: { score, label, color } };
  };

  const checkPasswordsMatch = (password, confirmPassword) => {
    if (!confirmPassword) return null;
    return password === confirmPassword;
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    const newFormData = {
      ...formData,
      [name]: value
    };

    setFormData(newFormData);

    // Real-time password validation (only for signup mode)
    if (name === 'password' && !isLogin) {
      const { errors, strength } = validatePasswordStrength(value);
      setPasswordErrors(errors);
      setPasswordStrength(strength);

      // Also check if passwords match when password changes
      if (newFormData.confirmPassword) {
        setPasswordsMatch(checkPasswordsMatch(value, newFormData.confirmPassword));
      }
    }

    // Real-time confirm password validation
    if (name === 'confirmPassword') {
      setPasswordsMatch(checkPasswordsMatch(newFormData.password, value));
    }
  };

  const handleSubmit = async (e) => {
    e && e.preventDefault && e.preventDefault();
    
    // Prevent duplicate submissions
    if (isSubmitting || submitRef.current) {
      return;
    }
    
    setError('');
    setSuccess('');
    setIsSubmitting(true);
    setLoading(true);
    submitRef.current = true;
    
    try {
      if (isLogin) {
        if (!formData.email && !formData.username) {
          setError('Please enter your email or username.');
          setIsSubmitting(false);
          setLoading(false);
          submitRef.current = false;
          return;
        }
        if (!formData.password) {
          setError('Please enter your password.');
          setIsSubmitting(false);
          setLoading(false);
          submitRef.current = false;
          return;
        }
        const identifier = formData.email || formData.username;
        const result = await login(identifier, formData.password);
        if (result.success) {
          setSuccess('Logged in successfully! Redirecting to dashboard...');
          // Wait a bit for auth state to update, then navigate
          setTimeout(() => {
            navigate('/dashboard');
          }, 1000);
        } else {
          setError(result.error || 'Login failed. Please try again.');
          setIsSubmitting(false);
          setLoading(false);
          submitRef.current = false;
        }
      } else {
        // Signup validation
        if (!formData.username || !formData.email || !formData.password || !formData.confirmPassword || !formData.name) {
          setError('Please fill in all fields.');
          setIsSubmitting(false);
          setLoading(false);
          submitRef.current = false;
          return;
        }

        // Password strength validation
        if (Object.keys(passwordErrors).length > 0) {
          setError('Please create a stronger password that meets all requirements.');
          setIsSubmitting(false);
          setLoading(false);
          submitRef.current = false;
          return;
        }

        // Password matching validation
        if (passwordsMatch === false) {
          setError('Passwords do not match.');
          setIsSubmitting(false);
          setLoading(false);
          submitRef.current = false;
          return;
        }

        if (passwordsMatch !== true) {
          setError('Please confirm your password.');
          setIsSubmitting(false);
          setLoading(false);
          submitRef.current = false;
          return;
        }

        const result = await register(formData.username, formData.email, formData.password, formData.name);
        if (result.success) {
          setSuccess('Sign up complete! Please log in to continue.');
          // Clear form
          setFormData({
            name: '',
            username: '',
            email: '',
            password: '',
            confirmPassword: ''
          });
          setPasswordErrors({});
          setPasswordStrength({ score: 0, label: '', color: '' });
          setPasswordsMatch(null);
          // Switch to login mode after 2 seconds
          setTimeout(() => {
            setIsLogin(true);
            setSuccess('Please log in with your credentials.');
            setIsSubmitting(false);
            setLoading(false);
            submitRef.current = false;
          }, 2000);
        } else {
          setError(result.error || 'Registration failed. Please try again.');
          setIsSubmitting(false);
          setLoading(false);
          submitRef.current = false;
        }
      }
    } catch {
      setError('An unexpected error occurred. Please try again.');
      setIsSubmitting(false);
      setLoading(false);
      submitRef.current = false;
    }
  };

  useEffect(() => {
    // Ensure body and html have black background for login page
    const originalBodyBg = document.body.style.backgroundColor;
    const originalHtmlBg = document.documentElement.style.backgroundColor;
    const originalRootBg = document.getElementById('root')?.style.backgroundColor;
    
    document.body.style.backgroundColor = '#000000';
    document.documentElement.style.backgroundColor = '#000000';
    if (document.getElementById('root')) {
      document.getElementById('root').style.backgroundColor = '#000000';
    }
    
    return () => {
      // Reset on unmount
      document.body.style.backgroundColor = originalBodyBg;
      document.documentElement.style.backgroundColor = originalHtmlBg;
      if (document.getElementById('root')) {
        document.getElementById('root').style.backgroundColor = originalRootBg || '';
      }
    };
  }, []);

  return (
    <>
      <style>{`
        /* Override main-content background for login page */
        .main-content:has(> div[data-login-page="true"]) {
          background-color: #000000 !important;
          margin: 0 !important;
          padding: 0 !important;
        }
        
        /* Ensure app-container doesn't interfere */
        .app-container:has(> .main-content > div[data-login-page="true"]) {
          background-color: #000000 !important;
          margin: 0 !important;
        }
        
        /* Fade-in animation */
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .animate-fade-in {
          animation: fadeIn 0.3s ease-in;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
          .auth-card {
            padding: 1.5rem !important;
          }
        }
        
        @media (max-width: 480px) {
          .auth-card {
            padding: 1.25rem !important;
            border-radius: 1.5rem !important;
          }
        }
      `}</style>
      <div 
        data-login-page="true"
        className="text-white flex justify-center relative"
        style={{
          backgroundColor: '#000000',
          minHeight: '100vh',
          width: '100vw',
          maxWidth: '100vw',
          margin: 0,
          padding: isMobile ? '1rem' : '2rem 1rem',
          paddingLeft: 0,
          boxSizing: 'border-box',
          position: 'relative',
          overflowY: 'auto',
          overflowX: 'hidden',
          alignItems: 'flex-start',
          paddingTop: isMobile ? '6rem' : '8rem',
          paddingBottom: isMobile ? '2rem' : '4rem'
        }}
      >
        {/* Full Screen Black Background */}
        <div 
          className="fixed inset-0 pointer-events-none"
          style={{
            backgroundColor: '#000000',
            zIndex: -1
          }}
        />

      {/* Subtle animated glow following cursor */}
      <div className="fixed inset-0 pointer-events-none">
        <div 
          className="absolute w-[600px] h-[600px] rounded-full blur-[100px] opacity-20"
          style={{
            background: 'radial-gradient(circle, rgba(77, 208, 225, 0.4) 0%, transparent 70%)',
            left: mousePos.x - 300,
            top: mousePos.y - 300,
            transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)'
          }}
        />
      </div>

      {/* Minimal grid overlay */}
      <div className="fixed inset-0 opacity-[0.015]" style={{
        backgroundImage: 'linear-gradient(rgba(77, 208, 225, 0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(77, 208, 225, 0.5) 1px, transparent 1px)',
        backgroundSize: '50px 50px'
      }} />

      {/* Header - Text and Home Button */}
      <div 
        className="fixed top-0 left-0 right-0 z-50"
        style={{
          padding: isMobile ? '1rem' : '2rem',
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          pointerEvents: 'none',
          background: 'rgba(0, 0, 0, 0.8)',
          backdropFilter: 'blur(10px)'
        }}
      >
        {/* Text - Top Center - Two Lines */}
        <div 
          style={{
            position: 'absolute',
            left: '50%',
            top: isMobile ? '1rem' : '2rem',
            transform: 'translateX(-50%)',
            pointerEvents: 'auto',
            textAlign: 'center',
            whiteSpace: 'nowrap'
          }}
        >
          <div style={{ lineHeight: '1.3' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', marginBottom: '0.125rem' }}>
              <Zap 
                size={isMobile ? 20 : 24}
                style={{ 
                  color: '#4DD0E1',
                  flexShrink: 0
                }} 
              />
              <div 
                style={{
                  fontSize: isSmallMobile ? '1.25rem' : isMobile ? '1.5rem' : '1.875rem',
                  fontWeight: '800',
                  fontFamily: "'Inter', system-ui, sans-serif",
                  background: 'linear-gradient(135deg, #4DD0E1 0%, #14B8A6 50%, #10B981 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                  letterSpacing: '-0.03em',
                  textTransform: 'uppercase'
                }}
              >
                FUZE
              </div>
            </div>
            <div 
              style={{
                fontSize: isSmallMobile ? '0.6rem' : '0.7rem',
                fontWeight: '500',
                fontFamily: "'Inter', system-ui, sans-serif",
                color: '#6b7280',
                letterSpacing: '0.12em',
                textTransform: 'none'
              }}
            >
              strike through the chaos
            </div>
          </div>
        </div>

        {/* Back to Home Button - Top Right */}
        <button
          onClick={() => navigate('/')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: isMobile ? '0.5rem 1rem' : '0.625rem 1.25rem',
            background: 'rgba(20, 20, 20, 0.6)',
            border: '1px solid rgba(77, 208, 225, 0.2)',
            borderRadius: '9999px',
            color: '#9ca3af',
            fontSize: isMobile ? '0.75rem' : '0.875rem',
            fontWeight: '500',
            cursor: 'pointer',
            pointerEvents: 'auto',
            transition: 'all 0.3s ease',
            backdropFilter: 'blur(10px)',
            marginLeft: 'auto'
          }}
          onMouseEnter={(e) => {
            e.target.style.color = '#4DD0E1';
            e.target.style.borderColor = 'rgba(77, 208, 225, 0.5)';
            e.target.style.background = 'rgba(20, 20, 20, 0.8)';
          }}
          onMouseLeave={(e) => {
            e.target.style.color = '#9ca3af';
            e.target.style.borderColor = 'rgba(77, 208, 225, 0.2)';
            e.target.style.background = 'rgba(20, 20, 20, 0.6)';
          }}
        >
          <Home size={isMobile ? 16 : 18} />
          {!isSmallMobile && <span>Home</span>}
        </button>
      </div>

      {/* Auth Container */}
      <div className={`w-full ${isMobile ? 'max-w-full px-4' : 'max-w-md'} relative z-10 transition-all duration-1000 ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>

        {/* Auth Card */}
        <div className="backdrop-blur-2xl border auth-card relative" style={{ 
          padding: isMobile ? '1.5rem' : '2rem',
          borderRadius: isMobile ? '1.5rem' : '1.875rem',
          background: 'rgba(20, 20, 20, 0.4)',
          borderColor: 'rgba(77, 208, 225, 0.2)',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5), 0 0 1px rgba(77, 208, 225, 0.3)',
          position: 'relative',
          overflow: 'hidden'
        }}>
          <div className="relative z-10" style={{ pointerEvents: (loading || isSubmitting) ? 'none' : 'auto' }}>
            {/* Toggle Buttons */}
            <AuthToggle
              isLogin={isLogin}
              onToggle={(loginState) => {
                if (loading || isSubmitting) return; // Prevent toggle during submission
                setIsLogin(loginState);
                setError('');
                setSuccess('');
                setPasswordErrors({});
                setPasswordStrength({ score: 0, label: '', color: '' });
                setPasswordsMatch(null);
                setIsSubmitting(false);
                setLoading(false);
                submitRef.current = false;
              }}
              disabled={loading || isSubmitting}
            />

            {/* Error/Success Messages */}
            {error && (
              <div className="mb-6 p-4 rounded-xl text-red-400 text-center font-medium text-sm animate-fade-in" style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                animation: 'fadeIn 0.3s ease-in'
              }}>
                <div className="flex items-center justify-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  <span>{error}</span>
                </div>
              </div>
            )}
            {success && (
              <div className="mb-6 p-4 rounded-xl text-green-400 text-center font-medium text-sm animate-fade-in" style={{
                background: 'rgba(34, 197, 94, 0.1)',
                border: '1px solid rgba(34, 197, 94, 0.3)',
                animation: 'fadeIn 0.3s ease-in'
              }}>
                <div className="flex items-center justify-center gap-2">
                  <span>{success}</span>
                </div>
              </div>
            )}
            
            {/* Loading Overlay */}
            {(loading || isSubmitting) && (
              <div className="absolute inset-0 bg-black bg-opacity-50 backdrop-blur-sm rounded-3xl flex items-center justify-center z-20" style={{
                animation: 'fadeIn 0.2s ease-in'
              }}>
                <div className="text-center">
                  <div className="w-12 h-12 border-4 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                  <p className="text-cyan-400 font-medium">
                    {isLogin ? 'Signing you in...' : 'Creating your account...'}
                  </p>
                </div>
              </div>
            )}

            {/* Form Fields */}
            <form className={isMobile ? 'space-y-4' : 'space-y-5'} onSubmit={handleSubmit}>
              {!isLogin && (
                <>
                  <Input
                    label="Full Name"
                    icon={User}
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="Enter your full name"
                    disabled={loading || isSubmitting}
                  />
                  <Input
                    label="Username"
                    icon={User}
                    name="username"
                    value={formData.username}
                    onChange={handleInputChange}
                    placeholder="Choose a username"
                    disabled={loading || isSubmitting}
                  />
                </>
              )}

              <Input
                label={`Email ${isLogin ? 'or Username' : 'Address'}`}
                icon={Mail}
                type={isLogin ? "text" : "email"}
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder={isLogin ? 'Enter your email or username' : 'Enter your email'}
                disabled={loading || isSubmitting}
              />

              <div className="group">
                <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500 transition-colors duration-300 group-focus-within:text-cyan-400" />
                  <input
                    type={showPassword ? "text" : "password"}
                    name="password"
                    value={formData.password}
                    onChange={handleInputChange}
                    disabled={loading || isSubmitting}
                    className={`w-full pl-12 pr-12 py-4 rounded-xl focus:outline-none transition-all duration-300 text-white placeholder-gray-500 ${Object.keys(passwordErrors).length > 0 ? 'border-red-500' : ''} ${(loading || isSubmitting) ? 'opacity-50 cursor-not-allowed' : ''}`}
                    style={{
                      background: 'rgba(0, 0, 0, 0.4)',
                      border: `1px solid ${Object.keys(passwordErrors).length > 0 ? 'rgba(239, 68, 68, 0.5)' : 'rgba(77, 208, 225, 0.2)'}`
                    }}
                    onFocus={(e) => {
                      if (!loading && !isSubmitting) {
                        e.target.style.borderColor = Object.keys(passwordErrors).length > 0 ? 'rgba(239, 68, 68, 0.5)' : 'rgba(77, 208, 225, 0.5)';
                        e.target.style.boxShadow = `0 0 0 3px ${Object.keys(passwordErrors).length > 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(77, 208, 225, 0.1)'}`;
                      }
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = Object.keys(passwordErrors).length > 0 ? 'rgba(239, 68, 68, 0.5)' : 'rgba(77, 208, 225, 0.2)';
                      e.target.style.boxShadow = 'none';
                    }}
                    placeholder={isLogin ? "Enter your password" : "Create a strong password"}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-cyan-400 transition-colors duration-300"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>

                {/* Password Strength Indicator - Only show in signup mode */}
                {!isLogin && formData.password && (
                  <div className="mt-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">Password Strength:</span>
                      <span
                        className="text-xs font-medium px-2 py-1 rounded"
                        style={{ backgroundColor: `${passwordStrength.color}20`, color: passwordStrength.color }}
                      >
                        {passwordStrength.label}
                      </span>
                    </div>

                    {/* Password Requirements */}
                    <div className="space-y-1">
                      {Object.entries({
                        length: 'At least 8 characters',
                        letter: 'At least one letter',
                        number: 'At least one number',
                        special: 'At least one special character'
                      }).map(([key, requirement]) => (
                        <div key={key} className="flex items-center text-xs">
                          {passwordErrors[key] ? (
                            <span className="text-red-400 mr-2">✗</span>
                          ) : (
                            <span className="text-green-400 mr-2">✓</span>
                          )}
                          <span className={passwordErrors[key] ? 'text-red-400' : 'text-green-400'}>
                            {requirement}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {!isLogin && (
                <div className="group">
                  <label className="block text-sm font-medium text-gray-300 mb-2">Confirm Password</label>
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500 transition-colors duration-300 group-focus-within:text-cyan-400" />
                    <input
                      type="password"
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleInputChange}
                      disabled={loading || isSubmitting}
                      className={`w-full pl-12 pr-4 py-4 rounded-xl focus:outline-none transition-all duration-300 text-white placeholder-gray-500 ${passwordsMatch === false ? 'border-red-500' : ''} ${(loading || isSubmitting) ? 'opacity-50 cursor-not-allowed' : ''}`}
                      style={{
                        background: 'rgba(0, 0, 0, 0.4)',
                        border: `1px solid ${passwordsMatch === false ? 'rgba(239, 68, 68, 0.5)' : passwordsMatch === true ? 'rgba(34, 197, 94, 0.5)' : 'rgba(77, 208, 225, 0.2)'}`
                      }}
                      onFocus={(e) => {
                        if (!loading && !isSubmitting) {
                          e.target.style.borderColor = passwordsMatch === false ? 'rgba(239, 68, 68, 0.5)' : passwordsMatch === true ? 'rgba(34, 197, 94, 0.5)' : 'rgba(77, 208, 225, 0.5)';
                          e.target.style.boxShadow = `0 0 0 3px ${passwordsMatch === false ? 'rgba(239, 68, 68, 0.1)' : passwordsMatch === true ? 'rgba(34, 197, 94, 0.1)' : 'rgba(77, 208, 225, 0.1)'}`;
                        }
                      }}
                      onBlur={(e) => {
                        e.target.style.borderColor = passwordsMatch === false ? 'rgba(239, 68, 68, 0.5)' : passwordsMatch === true ? 'rgba(34, 197, 94, 0.5)' : 'rgba(77, 208, 225, 0.2)';
                        e.target.style.boxShadow = 'none';
                      }}
                      placeholder="Confirm your password"
                    />

                    {/* Password Match Indicator */}
                    {formData.confirmPassword && (
                      <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                        {passwordsMatch === true ? (
                          <span className="text-green-400 text-lg">✓</span>
                        ) : passwordsMatch === false ? (
                          <span className="text-red-400 text-lg">✗</span>
                        ) : null}
                      </div>
                    )}
                  </div>

                  {/* Password Match Message */}
                  {formData.confirmPassword && (
                    <div className="mt-2 flex items-center text-xs">
                      {passwordsMatch === true ? (
                        <>
                          <span className="text-green-400 mr-2">✓</span>
                          <span className="text-green-400">Passwords match</span>
                        </>
                      ) : passwordsMatch === false ? (
                        <>
                          <span className="text-red-400 mr-2">✗</span>
                          <span className="text-red-400">Passwords do not match</span>
                        </>
                      ) : (
                        <>
                          <span className="text-gray-400 mr-2">○</span>
                          <span className="text-gray-400">Confirm your password</span>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}

              {isLogin && (
                <div className={`flex ${isSmallMobile ? 'flex-col gap-2' : 'items-center justify-between'} text-sm`}>
                  <label className="flex items-center cursor-pointer group">
                    <input type="checkbox" className="w-4 h-4 rounded border-gray-600 bg-black focus:ring-2 focus:ring-cyan-400 focus:ring-offset-0 text-cyan-400" />
                    <span className="ml-2 text-gray-400 group-hover:text-gray-300 transition-colors">Remember me</span>
                  </label>
                  <a href="#" className={`text-cyan-400 hover:text-cyan-300 transition-colors duration-300 font-medium ${isSmallMobile ? 'self-start' : ''}`}>
                    Forgot password?
                  </a>
                </div>
              )}

              <Button
                type="submit"
                variant="fuze"
                size="lg"
                className="group w-full mt-6"
                disabled={loading || isSubmitting}
              >
                <span className="flex items-center justify-center">
                  {loading || isSubmitting ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                      {isLogin ? 'Signing in...' : 'Creating account...'}
                    </>
                  ) : (
                    <>
                      {isLogin ? 'Sign In to Fuze' : 'Create Your Account'}
                      <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform duration-300" />
                    </>
                  )}
                </span>
              </Button>

            {/* OR - Social Login */}
            {/* Divider + Full-width Google button */}
            <div className="mt-4">
              <div className="flex items-center gap-3 mb-3">
                <div className="flex-1 h-[1px] bg-gray-700" />
                <div className="text-xs text-gray-400 uppercase tracking-wider">or continue with</div>
                <div className="flex-1 h-[1px] bg-gray-700" />
              </div>

              <button
                type="button"
                onClick={() => {
                  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || window.__env?.VITE_SUPABASE_URL
                  if (!supabaseUrl) {
                    setError('Supabase is not configured for OAuth')
                    return
                  }
                  const redirectTo = encodeURIComponent(window.location.origin + '/oauth/callback')
                  // Redirect to Supabase OAuth authorize endpoint
                  window.location.href = `${supabaseUrl.replace(/\/$/, '')}/auth/v1/authorize?provider=google&redirect_to=${redirectTo}`
                }}
                className="group w-full mt-1 py-3 rounded-xl border border-gray-600 bg-transparent text-white font-medium flex items-center justify-center gap-3 hover:bg-white/5 transition-colors"
                disabled={loading || isSubmitting}
                aria-label="Continue with Google"
                title="Continue with Google"
                style={{boxShadow: '0 1px 1px rgba(0,0,0,0.05)'}}
              >
                <i className="fab fa-google" aria-hidden="true" style={{fontSize: 18}} />
                <span>Continue with Google</span>
              </button>
            </div>
            </form>


            {/* Footer Text */}
            <div className="mt-8 text-center text-sm text-gray-400">
              {isLogin ? (
                <>
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={() => { 
                      setIsLogin(false); 
                      setError(''); 
                      setSuccess('');
                      setIsSubmitting(false);
                      setLoading(false);
                      submitRef.current = false;
                    }}
                    className="text-cyan-400 hover:text-cyan-300 transition-colors duration-300 font-semibold"
                    disabled={loading || isSubmitting}
                  >
                    Sign up for free
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => { 
                      setIsLogin(true); 
                      setError(''); 
                      setSuccess('');
                      setIsSubmitting(false);
                      setLoading(false);
                      submitRef.current = false;
                    }}
                    className="text-cyan-400 hover:text-cyan-300 transition-colors duration-300 font-semibold"
                    disabled={loading || isSubmitting}
                  >
                    Sign in
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Security Notice */}
        <div className={`${isMobile ? 'mt-6' : 'mt-8'} text-center text-xs text-gray-600`}>
          <div className={`flex items-center justify-center gap-2 ${isMobile ? 'mb-1' : 'mb-1'}`}>
            <Lock className="w-3 h-3" />
            <p className={isSmallMobile ? 'text-[0.7rem]' : ''}>Protected by enterprise-grade security</p>
          </div>
          <p className={isSmallMobile ? 'text-[0.7rem]' : ''}>Your data is encrypted and secure</p>
        </div>
      </div>
    </div>
    </>
  );
}