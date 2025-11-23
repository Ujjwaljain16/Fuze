import React from 'react';
import { User, Zap } from 'lucide-react';

const ProfileHeader = ({ user }) => {
  const displayName = user?.username || user?.name || 'User';
  const cleanDisplayName = displayName.replace(/[^\w\s]/g, '').trim() || 'User';

  const isMobile = window.innerWidth <= 768
  const isSmallMobile = window.innerWidth <= 480

  return (
    <div className={`${isMobile ? 'mt-6 mb-6 p-4' : 'mt-8 mb-8 p-6 md:p-8'} bg-gradient-to-br from-gray-900/60 to-black/60 backdrop-blur-xl rounded-2xl border border-gray-700/50 shadow-2xl hover:border-cyan-500/30 transition-all duration-300`}>
      <div className={`flex items-center ${isSmallMobile ? 'gap-3' : 'space-x-4'} ${isMobile ? 'mb-3' : 'mb-4'}`}>
        <div className="relative">
          <div className={`${isMobile ? 'w-12 h-12' : 'w-16 h-16'} bg-gradient-to-r from-cyan-500 to-teal-500 rounded-full flex items-center justify-center`}>
            <User className={`${isMobile ? 'w-6 h-6' : 'w-8 h-8'} text-white`} />
          </div>
          <div className="absolute inset-0 blur-lg bg-cyan-400 opacity-30 animate-pulse rounded-full" />
        </div>
        <div className="flex-1">
          <h1 
            className={`${isSmallMobile ? 'text-xl' : isMobile ? 'text-2xl' : 'text-2xl md:text-4xl'} font-bold leading-tight`}
            style={{
              background: 'linear-gradient(to right, #4DD0E1, #14B8A6, #10B981)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              color: '#4DD0E1'
            }}
          >
            {cleanDisplayName}'s Profile
          </h1>
          <p className={`text-gray-300 ${isMobile ? 'text-base mt-1' : 'text-lg md:text-xl leading-relaxed mt-2'}`}>
            Manage your account settings and preferences
          </p>
        </div>
      </div>
    </div>
  );
};

export default ProfileHeader;