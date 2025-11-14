import React, { useState, useEffect } from 'react';
import { Zap, Mail, Lock, User, Eye, EyeOff, ArrowRight, Github, Chrome } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Button from '../components/Button';
import Input from '../components/Input';
import AuthToggle from '../components/AuthToggle';

export default function FuzeAuth() {
  const [isLogin, setIsLogin] = useState(true);
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
  const navigate = useNavigate();
  const { login, register } = useAuth();

  useEffect(() => {
    setIsVisible(true);
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e && e.preventDefault && e.preventDefault();
    setError('');
    setSuccess('');
    if (isLogin) {
      // Login: send email or username and password
      if (!formData.email && !formData.username) {
        setError('Please enter your email or username.');
        return;
      }
      if (!formData.password) {
        setError('Please enter your password.');
        return;
      }
      // Prefer email, fallback to username
      const identifier = formData.email || formData.username;
      const result = await login(identifier, formData.password);
      if (result.success) {
        setSuccess('Login successful! Redirecting...');
        setTimeout(() => navigate('/app/dashboard'), 1000);
      } else {
        setError(result.error || 'Login failed.');
      }
    } else {
      // Register: send username, email, password, name
      if (!formData.username || !formData.email || !formData.password || !formData.confirmPassword || !formData.name) {
        setError('Please fill in all fields.');
        return;
      }
      if (formData.password !== formData.confirmPassword) {
        setError('Passwords do not match.');
        return;
      }
      const result = await register(formData.username, formData.email, formData.password, formData.name);
      if (result.success) {
        setSuccess('Registration successful! Redirecting to dashboard...');
        // Navigate to dashboard - onboarding modal will show automatically
        setTimeout(() => navigate('/dashboard'), 1500);
      } else {
        setError(result.error || 'Registration failed.');
      }
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 opacity-20">
        <div 
          className="absolute w-96 h-96 rounded-full"
          style={{
            background: 'radial-gradient(circle, rgba(59, 130, 246, 0.4) 0%, transparent 70%)',
            left: mousePos.x - 192,
            top: mousePos.y - 192,
            transition: 'all 0.3s ease-out'
          }}
        />
      </div>
      {/* Lightning Grid Background */}
      <div className="fixed inset-0 opacity-5">
        <div className="grid grid-cols-20 grid-rows-20 h-full w-full">
          {Array.from({ length: 400 }).map((_, i) => (
            <div
              key={i}
              className="border border-blue-500/20 animate-pulse"
              style={{
                animationDelay: `${Math.random() * 5}s`,
                animationDuration: `${3 + Math.random() * 3}s`
              }}
            />
          ))}
        </div>
      </div>
      {/* Auth Container */}
      <div className={`w-full max-w-md relative z-10 transition-all duration-1000 ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <div className="relative">
              <Zap className="w-10 h-10 text-blue-400" />
              <div className="absolute inset-0 blur-lg bg-blue-400 opacity-50 animate-pulse" />
            </div>
            <div>
              <span className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                Fuze
              </span>
              <div className="text-xs text-blue-300 font-medium tracking-wider uppercase opacity-80">
                Strike Through the Chaos
              </div>
            </div>
          </div>
        </div>
        {/* Auth Card */}
        <div className="bg-gradient-to-br from-gray-900/80 to-black/80 backdrop-blur-xl border border-gray-800 rounded-3xl p-8 relative overflow-hidden">
          {/* Animated Border */}
          <div className="absolute inset-0 rounded-3xl">
            <div className="absolute inset-0 rounded-3xl border border-transparent bg-gradient-to-r from-blue-500/20 to-purple-500/20" />
          </div>
          <div className="relative z-10">
            {/* Toggle Buttons */}
            <AuthToggle 
              isLogin={isLogin} 
              onToggle={(loginState) => { 
                setIsLogin(loginState); 
                setError(''); 
                setSuccess(''); 
              }} 
            />
            {/* Error/Success Messages */}
            {error && <div className="mb-4 text-red-400 text-center font-medium">{error}</div>}
            {success && <div className="mb-4 text-green-400 text-center font-medium">{success}</div>}
            {/* Form Fields */}
            <form className="space-y-6" onSubmit={handleSubmit}>
              {!isLogin && (
                <>
                  <Input
                    label="Full Name"
                    icon={User}
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="Enter your full name"
                  />
                  <Input
                    label="Username"
                    icon={User}
                    name="username"
                    value={formData.username}
                    onChange={handleInputChange}
                    placeholder="Choose a username"
                  />
                </>
              )}
              <Input
                label={`Email ${isLogin ? 'or Username' : 'Address'}`}
                icon={Mail}
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder={isLogin ? 'Enter your email or username' : 'Enter your email'}
              />
              <div className="group">
                <label className="block text-sm font-medium text-gray-300 mb-2">Password</label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-blue-400 transition-colors duration-300" />
                  <input
                    type={showPassword ? "text" : "password"}
                    name="password"
                    value={formData.password}
                    onChange={handleInputChange}
                    className="w-full pl-12 pr-12 py-4 bg-gray-800/50 border border-gray-700 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all duration-300 text-white placeholder-gray-400"
                    placeholder="Enter your password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-blue-400 transition-colors duration-300"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
              {!isLogin && (
                <Input
                  label="Confirm Password"
                  icon={Lock}
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleInputChange}
                  placeholder="Confirm your password"
                />
              )}
              {isLogin && (
                <div className="flex items-center justify-between text-sm">
                  <label className="flex items-center">
                    <input type="checkbox" className="w-4 h-4 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500 focus:ring-2" />
                    <span className="ml-2 text-gray-300">Remember me</span>
                  </label>
                  <a href="#" className="text-blue-400 hover:text-blue-300 transition-colors duration-300">
                    Forgot password?
                  </a>
                </div>
              )}
              <Button
                type="submit"
                variant="fuze"
                size="lg"
                className="group w-full"
              >
                <span className="flex items-center justify-center">
                  {isLogin ? 'Sign In to Fuze' : 'Create Your Account'}
                  <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform duration-300" />
                </span>
              </Button>
            </form>
            {/* Divider */}
            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-700"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-gray-900 text-gray-400">Or continue with</span>
              </div>
            </div>
            {/* Social Login */}
            <div className="grid grid-cols-2 gap-4">
              <Button variant="outline" className="flex items-center justify-center">
                <Github className="w-5 h-5 mr-2" />
                GitHub
              </Button>
              <Button variant="outline" className="flex items-center justify-center">
                <Chrome className="w-5 h-5 mr-2" />
                Google
              </Button>
            </div>
            {/* Footer Text */}
            <div className="mt-8 text-center text-sm text-gray-400">
              {isLogin ? (
                <>
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={() => { setIsLogin(false); setError(''); setSuccess(''); }}
                    className="text-blue-400 hover:text-blue-300 transition-colors duration-300 font-semibold"
                  >
                    Sign up for free
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => { setIsLogin(true); setError(''); setSuccess(''); }}
                    className="text-blue-400 hover:text-blue-300 transition-colors duration-300 font-semibold"
                  >
                    Sign in
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
        {/* Security Notice */}
        <div className="mt-6 text-center text-xs text-gray-500">
          <p>Protected by enterprise-grade security</p>
          <p className="mt-1">Your data is encrypted and secure</p>
        </div>
      </div>
      <style>{`
        @keyframes lightning {
          0%, 100% { opacity: 0.1; }
          50% { opacity: 0.3; }
        }
        .animate-lightning {
          animation: lightning 3s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}