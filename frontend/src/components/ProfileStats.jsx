import React from 'react';
import { User, Settings, Calendar, Shield } from 'lucide-react';

const ProfileStats = ({ user }) => {
  const stats = [
    {
      label: 'Member Since',
      value: user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A',
      icon: Calendar,
      color: 'blue'
    },
    {
      label: 'Account Status',
      value: 'Active',
      icon: Shield,
      color: 'green'
    },
    {
      label: 'Username',
      value: user?.username || 'Not set',
      icon: User,
      color: 'purple'
    },
    {
      label: 'Interests',
      value: user?.technology_interests ? 'Set' : 'Not set',
      icon: Settings,
      color: 'orange'
    }
  ];

  const getColorClasses = (color) => {
    const colors = {
      blue: 'from-cyan-600/20 to-cyan-600/10 text-cyan-400',
      green: 'from-teal-600/20 to-teal-600/10 text-teal-400',
      purple: 'from-cyan-600/20 to-teal-600/10 text-cyan-400',
      orange: 'from-orange-600/20 to-orange-600/10 text-orange-400'
    };
    return colors[color] || colors.blue;
  };

  const isMobile = window.innerWidth <= 768

  return (
    <div className={`grid grid-cols-1 ${isMobile ? 'md:grid-cols-2' : 'md:grid-cols-2 lg:grid-cols-4'} ${isMobile ? 'gap-4 mb-6' : 'gap-6 mb-8'}`}>
      {stats.map((stat, index) => (
        <div key={index} className={`bg-gradient-to-br from-gray-900/60 to-black/60 backdrop-blur-xl border border-gray-700/50 rounded-2xl ${isMobile ? 'p-4' : 'p-6'} hover:border-cyan-500/40 hover:shadow-lg hover:shadow-cyan-500/10 transition-all duration-300 group`}>
          <div className={`flex items-center justify-between ${isMobile ? 'mb-3' : 'mb-4'}`}>
            <div className={`${isMobile ? 'p-2' : 'p-3'} bg-gradient-to-r ${getColorClasses(stat.color)} rounded-xl group-hover:scale-110 transition-all duration-300`}>
              <stat.icon className={`${isMobile ? 'w-5 h-5' : 'w-6 h-6'}`} />
            </div>
          </div>
          <div className={`${isMobile ? 'text-lg' : 'text-xl'} font-bold text-white ${isMobile ? 'mb-1' : 'mb-2'} group-hover:text-cyan-100 transition-colors duration-300`}>
            {stat.value}
          </div>
          <div className={`text-gray-400 ${isMobile ? 'text-xs' : 'text-sm'} font-medium`}>{stat.label}</div>
        </div>
      ))}
    </div>
  );
};

export default ProfileStats;