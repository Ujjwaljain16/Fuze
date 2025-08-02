import React from 'react';

const AuthToggle = ({ isLogin, onToggle }) => {
  return (
    <div className="flex bg-gray-800/50 rounded-2xl p-1 mb-8">
      <button
        onClick={() => onToggle(true)}
        className={`flex-1 py-3 px-6 rounded-xl font-semibold transition-all duration-300 ${
          isLogin 
            ? 'bg-gradient-to-r from-blue-400 to-purple-500 text-white shadow-lg' 
            : 'text-gray-400 hover:text-white'
        }`}
      >
        Sign In
      </button>
      <button
        onClick={() => onToggle(false)}
        className={`flex-1 py-3 px-6 rounded-xl font-semibold transition-all duration-300 ${
          !isLogin 
            ? 'bg-gradient-to-r from-blue-400 to-purple-500 text-white shadow-lg' 
            : 'text-gray-400 hover:text-white'
        }`}
      >
        Sign Up
      </button>
    </div>
  );
};

export default AuthToggle;