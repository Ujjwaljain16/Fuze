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
  return (
    <div className="bg-gradient-to-br from-gray-900/60 to-black/60 backdrop-blur-xl border border-gray-700/50 rounded-2xl p-6 md:p-8 hover:border-purple-500/30 transition-all duration-300">
      <div className="flex items-center space-x-3 mb-6">
        <div className="p-3 bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-xl">
          <Shield className="w-6 h-6 text-purple-400" />
        </div>
        <h2 className="text-xl font-semibold text-white">Change Password</h2>
      </div>
      
      <form onSubmit={onSubmit} className="space-y-6">
        <div className="group">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Current Password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-purple-400 transition-colors duration-300" />
            <input
              type={showPassword ? "text" : "password"}
              name="current_password"
              value={formData.current_password}
              onChange={onInputChange}
              className="w-full pl-12 pr-12 py-4 bg-gray-800/50 border border-gray-700 rounded-xl focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 text-white placeholder-gray-400"
              placeholder="Enter current password"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-purple-400 transition-colors duration-300"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
        </div>

        <div className="group">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            New Password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-purple-400 transition-colors duration-300" />
            <input
              type={showPassword ? "text" : "password"}
              name="new_password"
              value={formData.new_password}
              onChange={onInputChange}
              className="w-full pl-12 pr-4 py-4 bg-gray-800/50 border border-gray-700 rounded-xl focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 text-white placeholder-gray-400"
              placeholder="Enter new password"
              required
              minLength={6}
            />
          </div>
        </div>

        <div className="group">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Confirm New Password
          </label>
          <div className="relative">
            <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 group-focus-within:text-purple-400 transition-colors duration-300" />
            <input
              type={showPassword ? "text" : "password"}
              name="confirm_password"
              value={formData.confirm_password}
              onChange={onInputChange}
              className="w-full pl-12 pr-4 py-4 bg-gray-800/50 border border-gray-700 rounded-xl focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300 text-white placeholder-gray-400"
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
            className="px-6 py-3 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 flex items-center justify-center space-x-2 group relative overflow-hidden whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
            style={{
              background: 'rgba(20, 20, 20, 0.6)',
              border: '1px solid rgba(168, 85, 247, 0.2)',
              backdropFilter: 'blur(10px)',
              color: '#9ca3af'
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                e.currentTarget.style.borderColor = 'rgba(168, 85, 247, 0.5)'
                e.currentTarget.style.background = 'rgba(20, 20, 20, 0.8)'
                e.currentTarget.style.color = '#a855f7'
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(168, 85, 247, 0.3)'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(168, 85, 247, 0.2)'
              e.currentTarget.style.background = 'rgba(20, 20, 20, 0.6)'
              e.currentTarget.style.color = '#9ca3af'
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            <Shield className="w-5 h-5" />
            <span>{loading ? 'Changing...' : 'Change Password'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};

export default PasswordForm;