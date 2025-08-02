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
      blue: 'from-blue-600/20 to-blue-600/10 text-blue-400',
      green: 'from-green-600/20 to-green-600/10 text-green-400',
      purple: 'from-purple-600/20 to-purple-600/10 text-purple-400',
      orange: 'from-orange-600/20 to-orange-600/10 text-orange-400'
    };
    return colors[color] || colors.blue;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {stats.map((stat, index) => (
        <div key={index} className="bg-gradient-to-br from-gray-900/60 to-black/60 backdrop-blur-xl border border-gray-700/50 rounded-2xl p-6 hover:border-blue-500/40 hover:shadow-lg hover:shadow-blue-500/10 transition-all duration-300 group">
          <div className="flex items-center justify-between mb-4">
            <div className={`p-3 bg-gradient-to-r ${getColorClasses(stat.color)} rounded-xl group-hover:scale-110 transition-all duration-300`}>
              <stat.icon className="w-6 h-6" />
            </div>
          </div>
          <div className="text-xl font-bold text-white mb-2 group-hover:text-blue-100 transition-colors duration-300">
            {stat.value}
          </div>
          <div className="text-gray-400 text-sm font-medium">{stat.label}</div>
        </div>
      ))}
    </div>
  );
};

export default ProfileStats;