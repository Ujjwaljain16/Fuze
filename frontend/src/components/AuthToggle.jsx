import React from 'react';

const AuthToggle = ({ isLogin, onToggle, disabled = false }) => {
  return (
    <div className="flex bg-gray-800/50 rounded-2xl p-1 mb-8">
      <button
        onClick={() => !disabled && onToggle(true)}
        disabled={disabled}
        className={`flex-1 py-3 px-6 rounded-xl font-semibold transition-all duration-300 ${
          isLogin 
            ? 'bg-gradient-to-r from-blue-400 to-purple-500 text-white shadow-lg' 
            : 'text-gray-400 hover:text-white'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        Sign In
      </button>
      <button
        onClick={() => !disabled && onToggle(false)}
        disabled={disabled}
        className={`flex-1 py-3 px-6 rounded-xl font-semibold transition-all duration-300 ${
          !isLogin 
            ? 'bg-gradient-to-r from-blue-400 to-purple-500 text-white shadow-lg' 
            : 'text-gray-400 hover:text-white'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        Sign Up
      </button>
    </div>
  );
};

export default AuthToggle;