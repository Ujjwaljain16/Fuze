import React from 'react';
import maintenanceImg from '../assets/maintenance.png';
import './Maintenance.css';

const Maintenance = () => {
  return (
    <div className="maintenance-container">
      <div className="maintenance-content">
        <div className="illustration-wrapper">
          <img src={maintenanceImg} alt="Maintenance" className="maintenance-illustration" />
          <div className="glow-effect"></div>
        </div>
        
        <h1 className="maintenance-title">Under Construction</h1>
        <p className="maintenance-message">
          We're currently upgrading our core systems to provide you with a more powerful and seamless experience. 
          Fuze will be back online shortly.
        </p>
        
        <div className="status-badge">
          <span className="pulse-dot"></span>
          System Hardening in Progress
        </div>
        
        <div className="social-links">
          <p className="follow-text">Follow our progress</p>
          <div className="links-row">
            <a href="https://twitter.com/itsfuze" target="_blank" rel="noopener noreferrer" className="social-link">Twitter</a>
            <span className="separator">•</span>
            <a href="https://github.com/Ujjwaljain16/Fuze" target="_blank" rel="noopener noreferrer" className="social-link">GitHub</a>
          </div>
        </div>
      </div>
      
      <footer className="maintenance-footer">
        &copy; {new Date().getFullYear()} Fuze AI. All rights reserved.
      </footer>
    </div>
  );
};

export default Maintenance;
