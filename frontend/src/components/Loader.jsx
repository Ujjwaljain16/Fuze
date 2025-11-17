import React from 'react';
import { Zap } from 'lucide-react';
import './Loader.css';

const Loader = ({ 
  size = 'medium', 
  fullScreen = false, 
  message = 'Loading...',
  variant = 'default' 
}) => {
  const sizeClasses = {
    small: 'loader-small',
    medium: 'loader-medium',
    large: 'loader-large'
  };

  const variantClasses = {
    default: 'loader-default',
    minimal: 'loader-minimal',
    full: 'loader-full'
  };

  if (fullScreen) {
    return (
      <div className="loader-fullscreen">
        <div className="loader-background">
          <div className="loader-orb loader-orb-1"></div>
          <div className="loader-orb loader-orb-2"></div>
          <div className="loader-orb loader-orb-3"></div>
        </div>
        <div className="loader-content">
          <div className={`loader-container ${sizeClasses[size]} ${variantClasses[variant]}`}>
            <div className="loader-icon-wrapper">
              <Zap className="loader-icon" size={size === 'small' ? 32 : size === 'large' ? 80 : 48} />
              <div className="loader-pulse-ring"></div>
              <div className="loader-pulse-ring loader-pulse-ring-delayed"></div>
              <div className="loader-glow"></div>
            </div>
            {message && (
              <p className="loader-message">{message}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`loader-inline ${sizeClasses[size]}`}>
      <div className="loader-icon-wrapper">
        <Zap className="loader-icon" size={size === 'small' ? 24 : size === 'large' ? 48 : 32} />
        <div className="loader-pulse-ring"></div>
        <div className="loader-pulse-ring loader-pulse-ring-delayed"></div>
        <div className="loader-glow"></div>
      </div>
      {message && (
        <p className="loader-message-inline">{message}</p>
      )}
    </div>
  );
};

export default Loader;

