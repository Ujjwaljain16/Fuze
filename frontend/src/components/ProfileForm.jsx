import React from 'react';
import { Save, User, Tag } from 'lucide-react';
import Input from './Input';

const ProfileForm = ({ formData, onInputChange, onSubmit, loading }) => {
  return (
    <div className="bg-gradient-to-br from-gray-900/60 to-black/60 backdrop-blur-xl border border-gray-700/50 rounded-2xl p-6 md:p-8 hover:border-blue-500/30 transition-all duration-300">
      <div className="flex items-center space-x-3 mb-6">
        <div className="p-3 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl">
          <User className="w-6 h-6 text-blue-400" />
        </div>
        <h2 className="text-xl font-semibold text-white">Profile Information</h2>
      </div>
      
      <form onSubmit={onSubmit} className="space-y-6">
        <Input
          label="Username"
          icon={User}
          name="username"
          value={formData.username}
          onChange={onInputChange}
          placeholder="Enter your username"
          required
        />

        <div className="group">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Technology Interests
          </label>
          <div className="relative">
            <Tag className="absolute left-4 top-4 w-5 h-5 text-gray-400 group-focus-within:text-blue-400 transition-colors duration-300" />
            <textarea
              name="technology_interests"
              value={formData.technology_interests}
              onChange={onInputChange}
              placeholder="e.g., React, Python, Machine Learning, Web Development"
              className="w-full pl-12 pr-4 py-4 bg-gray-800/50 border border-gray-700 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all duration-300 text-white placeholder-gray-400 resize-none"
              rows={4}
            />
          </div>
          <p className="mt-2 text-sm text-gray-400">
            This helps us provide better recommendations for you
          </p>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-3 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 flex items-center justify-center space-x-2 group relative overflow-hidden whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
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
            <Save className="w-5 h-5" />
            <span>{loading ? 'Updating...' : 'Update Profile'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};

export default ProfileForm;