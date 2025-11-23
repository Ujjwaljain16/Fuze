import React from 'react';

const Button = ({ 
  variant = 'primary', 
  size = 'md', 
  children, 
  className = '', 
  disabled = false,
  ...props 
}) => {
  const baseClasses = 'font-semibold transition-all duration-300 flex items-center justify-center relative overflow-hidden';
  
  const variants = {
    primary: 'bg-gradient-to-r from-cyan-600 to-teal-600 text-white shadow-lg hover:shadow-2xl hover:shadow-cyan-500/25 transform hover:scale-[1.02]',
    secondary: 'bg-gradient-to-r from-cyan-600 to-teal-600 text-white shadow-lg hover:shadow-2xl hover:shadow-cyan-500/25 transform hover:scale-[1.02]',
    fuze: 'bg-gradient-to-r from-cyan-600 to-teal-600 text-white shadow-lg hover:shadow-2xl hover:shadow-cyan-500/25 transform hover:scale-[1.02]',
    outline: 'border border-gray-700 text-gray-400 hover:text-white hover:bg-gray-800/50 hover:border-gray-600',
    ghost: 'text-gray-400 hover:text-white hover:bg-gray-800/50'
  };
  
  const sizes = {
    sm: 'py-2 px-4 text-sm rounded-lg',
    md: 'py-3 px-6 text-base rounded-xl',
    lg: 'py-4 px-8 text-lg rounded-xl'
  };
  
  const disabledClasses = disabled ? 'opacity-50 cursor-not-allowed hover:scale-100 hover:shadow-none' : '';
  
  return (
    <button
      className={`${baseClasses} ${variants[variant]} ${sizes[size]} ${disabledClasses} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;