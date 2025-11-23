import React from 'react';
import { LogOut, Settings } from 'lucide-react';
import Button from './Button';

const AccountActions = ({ onLogout }) => {
  const actions = [
    {
      label: 'Logout',
      icon: LogOut,
      variant: 'outline',
      onClick: onLogout,
      description: 'Sign out of your account',
      danger: true
    }
  ];

  return (
    <div className="bg-gradient-to-br from-gray-900/60 to-black/60 backdrop-blur-xl border border-gray-700/50 rounded-2xl p-6 md:p-8 hover:border-red-500/30 transition-all duration-300">
      <div className="flex items-center space-x-3 mb-6">
        <div className="p-3 bg-gradient-to-r from-red-600/20 to-orange-600/20 rounded-xl">
          <Settings className="w-6 h-6 text-red-400" />
        </div>
        <h2 className="text-xl font-semibold text-white">Account Actions</h2>
      </div>
      
      <div className="flex justify-center">
        {actions.map((action, index) => (
          <div key={index} className="group">
            <Button
              variant={action.danger ? 'outline' : action.variant}
              onClick={action.onClick}
              className={`px-8 py-3 flex items-center justify-center space-x-2 ${
                action.danger 
                  ? 'hover:border-red-500/50 hover:bg-red-500/10 hover:text-red-400' 
                  : 'hover:border-cyan-500/50'
              }`}
            >
              <action.icon className="w-5 h-5" />
              <span>{action.label}</span>
            </Button>
            <p className="text-xs text-gray-400 mt-2 text-center">
              {action.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AccountActions;