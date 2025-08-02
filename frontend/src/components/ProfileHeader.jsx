import React from 'react';
import { User, Zap } from 'lucide-react';

const ProfileHeader = ({ user }) => {
  const displayName = user?.username || user?.name || 'User';
  const cleanDisplayName = displayName.replace(/[^\w\s]/g, '').trim() || 'User';

  return (
    <div className="mt-8 mb-8 bg-gradient-to-br from-gray-900/60 to-black/60 backdrop-blur-xl rounded-2xl p-6 md:p-8 border border-gray-700/50 shadow-2xl hover:border-blue-500/30 transition-all duration-300">
      <div className="flex items-center space-x-4 mb-4">
        <div className="relative">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
            <User className="w-8 h-8 text-white" />
          </div>
          <div className="absolute inset-0 blur-lg bg-blue-400 opacity-30 animate-pulse rounded-full" />
        </div>
        <div className="flex-1">
          <h1 className="text-2xl md:text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent leading-tight">
            {cleanDisplayName}'s Profile
          </h1>
          <p className="text-gray-300 text-lg md:text-xl leading-relaxed mt-2">
            Manage your account settings and preferences
          </p>
        </div>
      </div>
    </div>
  );
};

export default ProfileHeader;