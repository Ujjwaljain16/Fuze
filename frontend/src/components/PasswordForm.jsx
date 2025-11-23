import React from 'react';
import { Lock, Eye, EyeOff, Shield } from 'lucide-react';

const PasswordForm = ({ 
  formData, 
  onInputChange, 
  onSubmit, 
  loading, 
  showPassword, 
  setShowPassword 
}) => {
  const isMobile = window.innerWidth <= 768
  const isSmallMobile = window.innerWidth <= 480

  return (
    <div className={`bg-gradient-to-br from-gray-900/60 to-black/60 backdrop-blur-xl border border-gray-700/50 rounded-2xl ${isMobile ? 'p-4' : 'p-6 md:p-8'} hover:border-cyan-500/30 transition-all duration-300`}>
      <div className={`flex items-center ${isSmallMobile ? 'gap-2' : 'space-x-3'} ${isMobile ? 'mb-4' : 'mb-6'}`}>
        <div className={`${isMobile ? 'p-2' : 'p-3'} bg-gradient-to-r from-cyan-600/20 to-teal-600/20 rounded-xl`}>
          <Shield className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'} text-cyan-400`} />
        </div>
        <h2 className={`${isMobile ? 'text-lg' : 'text-xl'} font-semibold text-white`}>Change Password</h2>
      </div>
      
      <form onSubmit={onSubmit} className={`${isMobile ? 'space-y-4' : 'space-y-6'}`}>
        <div className="group">
          <label className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-medium text-gray-300 ${isMobile ? 'mb-1.5' : 'mb-2'}`}>
            Current Password
          </label>
          <div className="relative">
            <Lock className={`absolute left-4 top-1/2 transform -translate-y-1/2 ${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 group-focus-within:text-cyan-400 transition-colors duration-300`} />
            <input
              type={showPassword ? "text" : "password"}
              name="current_password"
              value={formData.current_password}
              onChange={onInputChange}
              className={`w-full pl-12 pr-12 ${isMobile ? 'py-3 text-sm' : 'py-4'} bg-gray-800/50 border border-gray-700 rounded-xl focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300 text-white placeholder-gray-400`}
              placeholder="Enter current password"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-cyan-400 transition-colors duration-300"
            >
              {showPassword ? <EyeOff className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} /> : <Eye className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />}
            </button>
          </div>
        </div>

        <div className="group">
          <label className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-medium text-gray-300 ${isMobile ? 'mb-1.5' : 'mb-2'}`}>
            New Password
          </label>
          <div className="relative">
            <Lock className={`absolute left-4 top-1/2 transform -translate-y-1/2 ${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 group-focus-within:text-cyan-400 transition-colors duration-300`} />
            <input
              type={showPassword ? "text" : "password"}
              name="new_password"
              value={formData.new_password}
              onChange={onInputChange}
              className={`w-full pl-12 pr-4 ${isMobile ? 'py-3 text-sm' : 'py-4'} bg-gray-800/50 border border-gray-700 rounded-xl focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300 text-white placeholder-gray-400`}
              placeholder="Enter new password"
              required
              minLength={6}
            />
          </div>
        </div>

        <div className="group">
          <label className={`block ${isMobile ? 'text-xs' : 'text-sm'} font-medium text-gray-300 ${isMobile ? 'mb-1.5' : 'mb-2'}`}>
            Confirm New Password
          </label>
          <div className="relative">
            <Lock className={`absolute left-4 top-1/2 transform -translate-y-1/2 ${isMobile ? 'w-4 h-4' : 'w-5 h-5'} text-gray-400 group-focus-within:text-cyan-400 transition-colors duration-300`} />
            <input
              type={showPassword ? "text" : "password"}
              name="confirm_password"
              value={formData.confirm_password}
              onChange={onInputChange}
              className={`w-full pl-12 pr-4 ${isMobile ? 'py-3 text-sm' : 'py-4'} bg-gray-800/50 border border-gray-700 rounded-xl focus:outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500/20 transition-all duration-300 text-white placeholder-gray-400`}
              placeholder="Confirm new password"
              required
              minLength={6}
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className={`${isMobile ? 'px-4 py-2 text-sm' : 'px-6 py-3'} rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 flex items-center justify-center ${isSmallMobile ? 'gap-1.5' : 'space-x-2'} group relative overflow-hidden whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100`}
            style={{
              background: 'rgba(20, 20, 20, 0.6)',
              border: '1px solid rgba(77, 208, 225, 0.2)',
              backdropFilter: 'blur(10px)',
              color: '#9ca3af'
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                e.currentTarget.style.borderColor = 'rgba(77, 208, 225, 0.5)'
                e.currentTarget.style.background = 'rgba(20, 20, 20, 0.8)'
                e.currentTarget.style.color = '#4DD0E1'
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(77, 208, 225, 0.3)'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(77, 208, 225, 0.2)'
              e.currentTarget.style.background = 'rgba(20, 20, 20, 0.6)'
              e.currentTarget.style.color = '#9ca3af'
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            <Shield className={`${isMobile ? 'w-4 h-4' : 'w-5 h-5'}`} />
            <span>{loading ? 'Changing...' : 'Change Password'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};

export default PasswordForm;