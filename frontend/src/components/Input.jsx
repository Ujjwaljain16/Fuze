import React from 'react';

const Input = ({ 
  label, 
  icon: Icon, 
  type = 'text', 
  placeholder, 
  className = '',
  error,
  name,
  value,
  onChange,
  ...props 
}) => {
  return (
    <div className="group">
      {label && (
        <label className="block text-sm font-medium text-gray-300 mb-2">
          {label}
        </label>
      )}
      <div className="relative">
        {Icon && (
          <Icon className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-cyan-400 transition-colors duration-300" />
        )}
        <input
          type={type}
          name={name}
          value={value}
          onChange={onChange}
          className={`w-full ${Icon ? 'pl-12' : 'pl-4'} pr-4 py-4 rounded-xl focus:outline-none transition-all duration-300 text-white placeholder-gray-500 ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20' : ''} ${className}`}
          style={{
            background: 'rgba(0, 0, 0, 0.4)',
            border: `1px solid ${error ? 'rgba(239, 68, 68, 0.2)' : 'rgba(77, 208, 225, 0.2)'}`
          }}
          onFocus={(e) => {
            if (!error) {
              e.target.style.borderColor = 'rgba(77, 208, 225, 0.5)';
              e.target.style.boxShadow = '0 0 0 3px rgba(77, 208, 225, 0.1)';
            }
          }}
          onBlur={(e) => {
            if (!error) {
              e.target.style.borderColor = 'rgba(77, 208, 225, 0.2)';
              e.target.style.boxShadow = 'none';
            }
          }}
          placeholder={placeholder}
          {...props}
        />
      </div>
      {error && (
        <p className="mt-2 text-sm text-red-400">{error}</p>
      )}
    </div>
  );
};

export default Input;