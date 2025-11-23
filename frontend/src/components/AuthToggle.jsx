import React from 'react';

const AuthToggle = ({ isLogin, onToggle, disabled = false }) => {
  return (
    <div 
      className="flex rounded-2xl p-1 mb-8 relative overflow-hidden"
      style={{
        background: 'rgba(0, 0, 0, 0.3)',
        border: '1px solid rgba(77, 208, 225, 0.1)',
        backdropFilter: 'blur(10px)'
      }}
    >
      {/* Animated background for active button */}
      <div
        className="absolute top-1 bottom-1 rounded-xl transition-all duration-300 ease-out"
        style={{
          left: isLogin ? '0.25rem' : '50%',
          right: isLogin ? '50%' : '0.25rem',
          background: 'linear-gradient(135deg, #4DD0E1 0%, #14B8A6 50%, #10B981 100%)',
          boxShadow: '0 4px 20px rgba(77, 208, 225, 0.4), 0 0 20px rgba(16, 185, 129, 0.2)',
          zIndex: 0
        }}
      />
      
      <button
        onClick={() => !disabled && onToggle(true)}
        disabled={disabled}
        className={`flex-1 py-3 px-6 rounded-xl font-semibold transition-all duration-300 relative z-10 ${
          isLogin 
            ? 'text-white' 
            : 'text-gray-400 hover:text-gray-300'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        style={{
          textShadow: isLogin ? '0 2px 8px rgba(0, 0, 0, 0.3)' : 'none'
        }}
      >
        Sign In
      </button>
      <button
        onClick={() => !disabled && onToggle(false)}
        disabled={disabled}
        className={`flex-1 py-3 px-6 rounded-xl font-semibold transition-all duration-300 relative z-10 ${
          !isLogin 
            ? 'text-white' 
            : 'text-gray-400 hover:text-gray-300'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        style={{
          textShadow: !isLogin ? '0 2px 8px rgba(0, 0, 0, 0.3)' : 'none'
        }}
      >
        Sign Up
      </button>
    </div>
  );
};

export default AuthToggle;