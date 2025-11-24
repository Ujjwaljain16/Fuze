import React, { useState, useEffect } from 'react'; 
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  Zap, 
  BookmarkPlus, 
  Link, 
  Sparkles, 
  SearchCheck, 
  Lightbulb, 
  Globe, 
  FolderTree, 
  LayoutDashboard, 
  Lock,
  Library,
  Hourglass,
  Compass,
  ArrowRight,
  ChevronDown,
  Github,
  Linkedin,
  Mail,
  Menu,
  X
} from 'lucide-react';
import logo1 from '../assets/logo1.svg';

export default function FuzeLanding() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [isVisible, setIsVisible] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [particles, setParticles] = useState([]);
  const [showLogo, setShowLogo] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [isSmallMobile, setIsSmallMobile] = useState(window.innerWidth <= 480);

  // Handle "Start for Free" button click - redirect to dashboard if logged in
  const handleStartForFree = () => {
    if (isAuthenticated) {
      navigate('/dashboard');
    } else {
      navigate('/login?mode=signup');
    }
  };

  useEffect(() => {
    setIsVisible(true);
    
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    
    const handleScroll = () => {
      // Show logo only when at the top of the page (within 50px)
      setShowLogo(window.scrollY < 50);
    };
    
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
      setIsSmallMobile(window.innerWidth <= 480);
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('scroll', handleScroll);
    window.addEventListener('resize', handleResize);
    
    // Check initial scroll position and screen size
    handleScroll();
    handleResize();
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  useEffect(() => {
    const generateParticles = () => {
      const newParticles = Array.from({ length: 30 }, (_, i) => ({
        id: i,
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
        size: Math.random() * 3 + 1,
        speedX: (Math.random() - 0.5) * 0.5,
        speedY: (Math.random() - 0.5) * 0.5,
        opacity: Math.random() * 0.5 + 0.1,
        color: Math.random() > 0.5 ? '#4DD0E1' : '#10B981'
      }));
      setParticles(newParticles);
    };

    generateParticles();
    const interval = setInterval(() => {
      setParticles(prev => prev.map(particle => {
        const newX = particle.x + particle.speedX;
        const newY = particle.y + particle.speedY;
        return {
          ...particle,
          x: newX > window.innerWidth ? 0 : newX < 0 ? window.innerWidth : newX,
          y: newY > window.innerHeight ? 0 : newY < 0 ? window.innerHeight : newY
        };
      }));
    }, 50);

    return () => clearInterval(interval);
  }, []);

  const problems = [
    {
      icon: <Library className="w-8 h-8" />,
      title: "The Information Overload Trap",
      body: "LinkedIn posts, Daily.dev articles, YouTube tutorials, scattered bookmarks... your valuable insights are everywhere but nowhere when you need them. Stop losing track of what you've learned."
    },
    {
      icon: <Hourglass className="w-8 h-8" />,
      title: "The Unfinished Project Graveyard",
      body: "Too many ideas, too little momentum. Side projects die because you can't find the right resources, get stuck, or simply lose the thread. Turn ideas into completed masterpieces."
    },
    {
      icon: <Compass className="w-8 h-8" />,
      title: "Navigating the Ever-Changing Tech Landscape",
      body: "New frameworks every week, endless choices. It's hard to pick the right tools and stay updated without feeling overwhelmed or falling behind. Make confident tech decisions."
    }
  ];

  const steps = [
    {
      icon: <BookmarkPlus className="w-8 h-8" />,
      title: "Save Anything, Anywhere",
      body: "Use our intelligent Chrome Extension or mobile share features to capture LinkedIn posts, articles, videos, and bookmarks in seconds."
    },
    {
      icon: <Link className="w-8 h-8" />,
      title: "Link Knowledge to Your Projects",
      body: "Define your projects and interests. Fuze's AI automatically connects your saved content to your active goals, building a personalized knowledge graph."
    },
    {
      icon: <Sparkles className="w-8 h-8" />,
      title: "Get Instant, Relevant Suggestions",
      body: "Receive AI-powered recommendations tailored to your current project or search query. Stop searching, start building."
    }
  ];

  const features = [
    {
      icon: <SearchCheck className="w-8 h-8" />,
      title: "AI-Powered Semantic Search",
      body: "Go beyond keywords. Find content based on its true meaning, instantly surfacing the most relevant resources for any query."
    },
    {
      icon: <Lightbulb className="w-8 h-8" />,
      title: "Project-Contextual Recommendations",
      body: "Never get stuck again. Fuze recommends saved content directly related to your active projects and their tech stacks."
    },
    {
      icon: <Globe className="w-8 h-8" />,
      title: "Cross-Platform Content Capture",
      body: "Seamlessly save from LinkedIn (mobile & desktop), Chrome bookmarks, and any URL. Your knowledge, centralized."
    },
    {
      icon: <FolderTree className="w-8 h-8" />,
      title: "Organized Knowledge Hub",
      body: "Tag, categorize, and add notes to your saved content. Build a personalized, searchable library of insights."
    },
    {
      icon: <LayoutDashboard className="w-8 h-8" />,
      title: "Intuitive Project Management",
      body: "Define your side projects, track progress, and see all related resources in one clean dashboard."
    },
    {
      icon: <Lock className="w-8 h-8" />,
      title: "Secure & Private",
      body: "Your data is yours. Fuze uses robust authentication and encryption to keep your learning journey private and secure."
    }
  ];

  const scrollToSection = (sectionId) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      height: '100%',
      width: '100vw', 
      backgroundColor: '#0F0F1E', 
      color: 'white', 
      position: 'relative', 
      margin: 0, 
      padding: 0,
      overflowX: 'hidden'
    }}>
      <style>{`
        @keyframes gridPulse {
          0%, 100% { opacity: 0.1; border-color: rgba(77, 208, 225, 0.1); }
          50% { opacity: 0.3; border-color: rgba(77, 208, 225, 0.2); }
        }
        
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-20px); }
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.1); }
        }
        
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        
        .hover-lift {
          transition: all 0.3s ease;
        }
        
        .hover-lift:hover {
          transform: translateY(-8px);
          box-shadow: 0 20px 40px rgba(77, 208, 225, 0.2);
        }
        
        .gradient-border {
          position: relative;
          background: linear-gradient(135deg, rgba(26, 26, 46, 0.8), rgba(37, 37, 64, 0.6));
          border-radius: 1.5rem;
        }
        
        .gradient-border::before {
          content: '';
          position: absolute;
          inset: 0;
          border-radius: 1.5rem;
          padding: 2px;
          background: linear-gradient(135deg, #4DD0E1, #14B8A6, #10B981);
          -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
          -webkit-mask-composite: xor;
          mask-composite: exclude;
          opacity: 0.3;
          transition: opacity 0.3s;
        }
        
        .gradient-border:hover::before {
          opacity: 0.6;
        }
        
        .logo-container {
          width: auto;
          height: auto;
          max-width: 200px;
          max-height: 80px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: transparent;
          border: none;
          box-shadow: none;
          transition: transform 0.3s ease;
          padding: 0;
          position: relative;
        }
        
        .logo-container:hover {
          transform: scale(1.05) !important;
        }
        
        .logo-container img {
          width: auto;
          height: auto;
          max-width: 200px;
          max-height: 80px;
          object-fit: contain;
          mix-blend-mode: normal;
        }
        
        @media (max-width: 768px) {
          .logo-container {
            max-width: 150px;
            max-height: 60px;
            padding: 0;
          }
          
          .logo-container img {
            max-width: 150px;
            max-height: 60px;
          }
        }
        
        @media (max-width: 480px) {
          .logo-container {
            max-width: 120px;
            max-height: 50px;
            padding: 0;
          }
          
          .logo-container img {
            max-width: 120px;
            max-height: 50px;
          }
        }
        
        /* Mobile Navigation */
        @media (max-width: 768px) {
          .mobile-nav {
            display: flex !important;
            flex-direction: row;
            gap: 1rem;
            align-items: center;
          }
          
          .desktop-nav {
            display: none !important;
          }
        }
        
        @media (min-width: 769px) {
          .mobile-nav {
            display: none !important;
          }
          
          .desktop-nav {
            display: flex !important;
          }
        }
        
        /* Responsive Navigation */
        @media (max-width: 768px) {
          nav {
            padding: 0.5rem 1rem !important;
            max-width: 95% !important;
          }
        }
        
        /* Responsive Hero Mockup */
        @media (max-width: 768px) {
          .gradient-border {
            padding: 1.5rem !important;
          }
        }
        
        @media (max-width: 480px) {
          .gradient-border {
            padding: 1rem !important;
          }
        }
      `}</style>

      {/* Floating Particles */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 1, pointerEvents: 'none' }}>
        {particles.map(particle => (
          <div
            key={particle.id}
            style={{
              position: 'absolute',
              left: particle.x,
              top: particle.y,
              width: particle.size,
              height: particle.size,
              backgroundColor: particle.color,
              borderRadius: '50%',
              opacity: particle.opacity,
              filter: 'blur(1px)',
              boxShadow: `0 0 ${particle.size * 2}px ${particle.color}`
            }}
          />
        ))}
      </div>

      {/* Mouse Glow */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 2, pointerEvents: 'none' }}>
        <div 
          style={{
            position: 'absolute',
            width: '400px',
            height: '400px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(77, 208, 225, 0.15) 0%, rgba(92, 107, 192, 0.08) 50%, transparent 70%)',
            left: mousePos.x - 200,
            top: mousePos.y - 200,
            transition: 'all 0.3s ease-out',
            filter: 'blur(40px)'
          }}
        />
      </div>

      {/* Grid Background */}
      <div style={{ position: 'fixed', inset: 0, opacity: 0.03, zIndex: 0 }}>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(20, 1fr)', 
          gridTemplateRows: 'repeat(20, 1fr)', 
          height: '100%', 
          width: '100%'
        }}>
          {Array.from({ length: 400 }).map((_, i) => (
            <div
              key={i}
              style={{
                border: '1px solid rgba(77, 208, 225, 0.2)',
                animation: `gridPulse ${3 + Math.random() * 2}s ease-in-out infinite`,
                animationDelay: `${Math.random() * 3}s`
              }}
            />
          ))}
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ 
        position: 'fixed', 
        top: '1.5rem',
        left: '50%',
        transform: isVisible ? 'translateX(-50%) translateY(0)' : 'translateX(-50%) translateY(-2.5rem)',
        zIndex: 50, 
        padding: '0.75rem 2rem', 
        background: 'rgba(26, 26, 46, 0.7)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(77, 208, 225, 0.2)',
        borderRadius: '50px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
        transition: 'all 1s',
        opacity: isVisible ? 1 : 0,
        maxWidth: '90%',
        width: 'auto'
      }}>
          {/* Desktop Navigation */}
          <div className="desktop-nav" style={{ alignItems: 'center', gap: '2rem' }}>
            <button 
              onClick={() => { scrollToSection('problems'); setMobileMenuOpen(false); }}
              style={{ 
                color: '#E5E7EB', 
                background: 'none', 
                border: 'none', 
                cursor: 'pointer', 
                fontSize: '0.9rem', 
                fontWeight: '500',
                transition: 'color 0.3s'
              }} 
              onMouseEnter={(e) => e.target.style.color = '#4DD0E1'} 
              onMouseLeave={(e) => e.target.style.color = '#E5E7EB'}
            >
              Problems
            </button>
            <button 
              onClick={() => { scrollToSection('how-it-works'); setMobileMenuOpen(false); }}
              style={{ 
                color: '#E5E7EB', 
                background: 'none', 
                border: 'none', 
                cursor: 'pointer', 
                fontSize: '0.9rem', 
                fontWeight: '500',
                transition: 'color 0.3s'
              }} 
              onMouseEnter={(e) => e.target.style.color = '#4DD0E1'} 
              onMouseLeave={(e) => e.target.style.color = '#E5E7EB'}
            >
              How It Works
            </button>
            <button 
              onClick={() => { scrollToSection('features'); setMobileMenuOpen(false); }}
              style={{ 
                color: '#E5E7EB', 
                background: 'none', 
                border: 'none', 
                cursor: 'pointer', 
                fontSize: '0.9rem', 
                fontWeight: '500',
                transition: 'color 0.3s'
              }} 
              onMouseEnter={(e) => e.target.style.color = '#4DD0E1'} 
              onMouseLeave={(e) => e.target.style.color = '#E5E7EB'}
            >
              Features
            </button>
            <button 
              onClick={handleStartForFree}
              style={{
                background: 'linear-gradient(135deg, #4DD0E1 0%, #14B8A6 50%, #10B981 100%)',
                color: '#fff',
                padding: '0.625rem 1.75rem',
                border: 'none',
                borderRadius: '25px',
                fontWeight: '600',
                fontSize: '0.9rem',
                cursor: 'pointer',
                boxShadow: '0 4px 15px rgba(77, 208, 225, 0.3)',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.target.style.transform = 'translateY(-2px)';
                e.target.style.boxShadow = '0 6px 20px rgba(77, 208, 225, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.target.style.transform = 'translateY(0)';
                e.target.style.boxShadow = '0 4px 15px rgba(77, 208, 225, 0.3)';
              }}
            >
              {isAuthenticated ? 'Go to Dashboard' : 'Start for Free'}
            </button>
          </div>
          
          {/* Mobile Navigation */}
          <div className="mobile-nav" style={{ alignItems: 'center', gap: '1rem' }}>
            <button 
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              style={{
                background: 'none',
                border: 'none',
                color: '#E5E7EB',
                cursor: 'pointer',
                padding: '0.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
            <button 
              onClick={handleStartForFree}
              style={{
                background: 'linear-gradient(135deg, #4DD0E1 0%, #14B8A6 50%, #10B981 100%)',
                color: '#fff',
                padding: '0.5rem 1.25rem',
                border: 'none',
                borderRadius: '25px',
                fontWeight: '600',
                fontSize: '0.85rem',
                cursor: 'pointer',
                boxShadow: '0 4px 15px rgba(77, 208, 225, 0.3)',
                transition: 'all 0.3s ease'
              }}
            >
              {isAuthenticated ? 'Dashboard' : 'Start Free'}
            </button>
          </div>
          
          {/* Mobile Menu Dropdown */}
          {mobileMenuOpen && (
            <div style={{
              position: 'absolute',
              top: 'calc(100% + 0.5rem)',
              left: '50%',
              transform: 'translateX(-50%)',
              background: 'rgba(26, 26, 46, 0.95)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(77, 208, 225, 0.2)',
              borderRadius: '1rem',
              padding: '1rem',
              minWidth: '200px',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
              zIndex: 1000
            }}>
              <button 
                onClick={() => { scrollToSection('problems'); setMobileMenuOpen(false); }}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '0.75rem 1rem',
                  color: '#E5E7EB',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: '500',
                  borderRadius: '0.5rem',
                  transition: 'all 0.3s',
                  marginBottom: '0.5rem'
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = 'rgba(77, 208, 225, 0.1)';
                  e.target.style.color = '#4DD0E1';
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = 'none';
                  e.target.style.color = '#E5E7EB';
                }}
              >
                Problems
              </button>
              <button 
                onClick={() => { scrollToSection('how-it-works'); setMobileMenuOpen(false); }}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '0.75rem 1rem',
                  color: '#E5E7EB',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: '500',
                  borderRadius: '0.5rem',
                  transition: 'all 0.3s',
                  marginBottom: '0.5rem'
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = 'rgba(77, 208, 225, 0.1)';
                  e.target.style.color = '#4DD0E1';
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = 'none';
                  e.target.style.color = '#E5E7EB';
                }}
              >
                How It Works
              </button>
              <button 
                onClick={() => { scrollToSection('features'); setMobileMenuOpen(false); }}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '0.75rem 1rem',
                  color: '#E5E7EB',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: '500',
                  borderRadius: '0.5rem',
                  transition: 'all 0.3s'
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = 'rgba(77, 208, 225, 0.1)';
                  e.target.style.color = '#4DD0E1';
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = 'none';
                  e.target.style.color = '#E5E7EB';
                }}
              >
                Features
              </button>
            </div>
          )}
      </nav>

      {/* Hero Section */}
      <section style={{ 
        position: 'relative', 
        zIndex: 10, 
        paddingTop: isMobile ? '8rem' : '12rem',
        paddingBottom: isMobile ? '4rem' : '6rem',
        paddingLeft: '0',
        paddingRight: isMobile ? '1rem' : '1rem',
        minHeight: isMobile ? 'auto' : '100vh', 
        display: 'flex', 
        alignItems: 'flex-start',
        justifyContent: 'flex-start'
      }}>
        {/* Logo - Top Left - Only visible at top */}
        {showLogo && (
          <div 
            className="logo-container"
            style={{ 
              position: 'absolute',
              top: '1.5rem',
              left: isMobile ? '1rem' : '6rem',
              zIndex: 1000,
              cursor: 'pointer',
              display: isMobile ? 'none' : 'block'
            }}
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          >
            <img 
              src={logo1}
              alt="FUZE Logo"
              style={{
                backgroundColor: 'transparent',
                mixBlendMode: 'normal'
              }}
            />
          </div>
        )}
        <div style={{ maxWidth: '1280px', width: '100%', paddingLeft: '0', paddingRight: '0', marginLeft: isMobile ? '1rem' : '2rem' }}>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', 
            gap: isMobile ? '2rem' : '4rem', 
            alignItems: 'center'
          }}>
            {/* Left Content */}
            <div style={{ 
              transition: 'all 1.5s',
              transitionDelay: '0.2s',
              transform: isVisible ? 'translateY(0)' : 'translateY(5rem)',
              opacity: isVisible ? 1 : 0,
              marginTop: '2rem',
              paddingLeft: '0'
            }}>
              <h1 style={{ 
                fontSize: window.innerWidth <= 480 ? '2rem' : window.innerWidth <= 768 ? '2.5rem' : '3.75rem', 
                fontWeight: 'bold', 
                marginBottom: '1.5rem', 
                lineHeight: 1.1,
                background: 'linear-gradient(to right, #E5E7EB, #4DD0E1)',
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                color: 'transparent'
              }}>
                Unleash Your Dev Potential.
              </h1>
              
              <h1 style={{ 
                fontSize: window.innerWidth <= 480 ? '2rem' : window.innerWidth <= 768 ? '2.5rem' : '3.75rem', 
                fontWeight: 'bold', 
                marginBottom: '2rem', 
                lineHeight: 1.1,
                background: 'linear-gradient(135deg, #4DD0E1, #14B8A6, #10B981)',
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                color: 'transparent'
              }}>
                Conquer Project Chaos.
              </h1>
              
              <p style={{ 
                fontSize: isSmallMobile ? '1rem' : isMobile ? '1.125rem' : '1.25rem', 
                color: '#d1d5db', 
                marginBottom: '3rem', 
                lineHeight: 1.7
              }}>
                Fuze intelligently connects your scattered knowledge to your projects, eliminating stagnation, FOMO, and information overload.
              </p>

              <div style={{ 
                display: 'flex', 
                flexDirection: isSmallMobile ? 'column' : 'row',
                gap: '1rem', 
                alignItems: 'center',
                width: isSmallMobile ? '100%' : 'auto'
              }}>
                <button 
                  onClick={handleStartForFree}
                  style={{
                  background: 'linear-gradient(135deg, #4DD0E1 0%, #14B8A6 50%, #10B981 100%)',
                  color: '#fff',
                  padding: isSmallMobile ? '0.875rem 1.75rem' : '1rem 2.5rem',
                  border: 'none',
                  borderRadius: '50px',
                  fontWeight: '600',
                  fontSize: isSmallMobile ? '0.95rem' : '1.125rem',
                  cursor: 'pointer',
                  boxShadow: '0 8px 24px rgba(77, 208, 225, 0.4)',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  width: isSmallMobile ? '100%' : 'auto',
                  justifyContent: 'center'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 12px 32px rgba(77, 208, 225, 0.5)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 8px 24px rgba(77, 208, 225, 0.4)';
                }}>
                  {isAuthenticated ? 'Go to Dashboard' : 'Start for Free'}
                  <ArrowRight size={20} />
                </button>
                
                <button 
                  onClick={() => scrollToSection('problems')}
                  style={{
                    background: 'transparent',
                    color: '#4DD0E1',
                    padding: isSmallMobile ? '0.875rem 1.75rem' : '1rem 2.5rem',
                    border: '2px solid #4DD0E1',
                    borderRadius: '50px',
                    fontWeight: '600',
                    fontSize: isSmallMobile ? '0.95rem' : '1.125rem',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    width: isSmallMobile ? '100%' : 'auto'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(77, 208, 225, 0.1)';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                >
                  Learn More
                </button>
              </div>
            </div>

            {/* Right Mockup */}
            <div style={{ 
              transition: 'all 1.5s',
              transitionDelay: '0.4s',
              transform: isVisible ? 'translateY(0)' : 'translateY(5rem)',
              opacity: isVisible ? 1 : 0,
              position: 'relative'
            }}>
              <div className="gradient-border hover-lift" style={{ 
                padding: isMobile ? '1.5rem' : '2rem',
                position: 'relative',
                overflow: 'hidden',
                animation: 'float 6s ease-in-out infinite',
                background: 'linear-gradient(135deg, rgba(26, 26, 46, 0.95), rgba(37, 37, 64, 0.85))',
                backdropFilter: 'blur(10px)',
                boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(77, 208, 225, 0.1)'
              }}>
                {/* Animated background glow */}
                <div style={{
                  position: 'absolute',
                  top: '-50%',
                  right: '-50%',
                  width: '200%',
                  height: '200%',
                  background: 'radial-gradient(circle, rgba(77, 208, 225, 0.1) 0%, transparent 70%)',
                  animation: 'pulse 4s ease-in-out infinite',
                  pointerEvents: 'none'
                }} />
                
                {/* Window controls */}
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  marginBottom: '1.5rem', 
                  gap: '0.5rem',
                  position: 'relative',
                  zIndex: 1
                }}>
                  <div style={{ 
                    width: '12px', 
                    height: '12px', 
                    borderRadius: '50%', 
                    backgroundColor: '#ef4444',
                    boxShadow: '0 0 8px rgba(239, 68, 68, 0.5)'
                  }} />
                  <div style={{ 
                    width: '12px', 
                    height: '12px', 
                    borderRadius: '50%', 
                    backgroundColor: '#f59e0b',
                    boxShadow: '0 0 8px rgba(245, 158, 11, 0.5)'
                  }} />
                  <div style={{ 
                    width: '12px', 
                    height: '12px', 
                    borderRadius: '50%', 
                    backgroundColor: '#10b981',
                    boxShadow: '0 0 8px rgba(16, 185, 129, 0.5)'
                  }} />
                </div>
                
                {/* Header placeholder */}
                <div style={{ 
                  marginBottom: '1.5rem',
                  position: 'relative',
                  zIndex: 1
                }}>
                  <div style={{ 
                    height: '14px', 
                    background: 'linear-gradient(90deg, rgba(77, 208, 225, 0.4), rgba(77, 208, 225, 0.2))', 
                    borderRadius: '7px', 
                    marginBottom: '0.75rem', 
                    width: '65%',
                    boxShadow: '0 2px 8px rgba(77, 208, 225, 0.2)'
                  }} />
                  <div style={{ 
                    height: '14px', 
                    background: 'linear-gradient(90deg, rgba(77, 208, 225, 0.3), rgba(77, 208, 225, 0.15))', 
                    borderRadius: '7px', 
                    width: '85%',
                    boxShadow: '0 2px 8px rgba(77, 208, 225, 0.15)'
                  }} />
                </div>

                {/* Feature cards */}
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', 
                  gap: '1rem', 
                  marginBottom: '1.5rem',
                  position: 'relative',
                  zIndex: 1
                }}>
                  <div style={{ 
                    padding: '1.25rem', 
                    background: 'linear-gradient(135deg, rgba(77, 208, 225, 0.2), rgba(77, 208, 225, 0.08))', 
                    border: '1px solid rgba(77, 208, 225, 0.4)',
                    borderRadius: '1rem',
                    transition: 'all 0.3s',
                    boxShadow: '0 4px 16px rgba(77, 208, 225, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
                    position: 'relative',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: '2px',
                      background: 'linear-gradient(90deg, transparent, #4DD0E1, transparent)',
                      animation: 'shimmer 2s ease-in-out infinite'
                    }} />
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.75rem', gap: '0.5rem' }}>
                      <div style={{
                        padding: '0.25rem',
                        background: 'rgba(77, 208, 225, 0.2)',
                        borderRadius: '0.5rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}>
                        <Sparkles style={{ width: '18px', height: '18px', color: '#4DD0E1' }} />
                      </div>
                      <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#4DD0E1' }}>AI Recommendation</div>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#d1d5db', lineHeight: 1.4 }}>React Best Practices</div>
                  </div>
                  <div style={{ 
                    padding: '1.25rem', 
                    background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(16, 185, 129, 0.08))', 
                    border: '1px solid rgba(16, 185, 129, 0.4)',
                    borderRadius: '1rem',
                    boxShadow: '0 4px 16px rgba(16, 185, 129, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
                    position: 'relative',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: '2px',
                      background: 'linear-gradient(90deg, transparent, #10B981, transparent)',
                      animation: 'shimmer 2s ease-in-out infinite 0.5s'
                    }} />
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.75rem', gap: '0.5rem' }}>
                      <div style={{
                        padding: '0.25rem',
                        background: 'rgba(16, 185, 129, 0.2)',
                        borderRadius: '0.5rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}>
                        <Link style={{ width: '18px', height: '18px', color: '#10B981' }} />
                      </div>
                      <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#10B981' }}>Connected</div>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#d1d5db', lineHeight: 1.4 }}>TypeScript Guide</div>
                  </div>
                </div>

                {/* Project card */}
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between', 
                  padding: '1.25rem', 
                  background: 'linear-gradient(135deg, rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.2))', 
                  borderRadius: '1rem',
                  border: '1px solid rgba(77, 208, 225, 0.2)',
                  boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
                  position: 'relative',
                  zIndex: 1
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{ 
                      width: '52px', 
                      height: '52px', 
                      borderRadius: '50%', 
                      background: 'linear-gradient(135deg, #4DD0E1, #10B981)',
                      boxShadow: '0 4px 16px rgba(77, 208, 225, 0.4), 0 0 20px rgba(16, 185, 129, 0.3)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      position: 'relative'
                    }}>
                      <Zap style={{ width: '24px', height: '24px', color: 'white' }} />
                    </div>
                    <div>
                      <div style={{ fontSize: '1rem', fontWeight: '600', color: 'white', marginBottom: '0.25rem' }}>Project: E-commerce App</div>
                      <div style={{ fontSize: '0.875rem', color: '#9ca3af' }}>3 resources connected</div>
                    </div>
                  </div>
                  <ChevronDown style={{ color: '#4DD0E1', opacity: 0.7 }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Problems Section */}
      <section id="problems" style={{ 
        position: 'relative', 
        zIndex: 10, 
        padding: isMobile ? '4rem 1rem' : '6rem 1.5rem',
        background: 'transparent'
      }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: isMobile ? '2rem' : '4rem' }}>
            <h2 style={{ 
              fontSize: isSmallMobile ? '1.75rem' : isMobile ? '2.25rem' : '3rem', 
              fontWeight: 'bold', 
              marginBottom: '1rem',
              color: 'white'
            }}>
              Your Biggest Challenges, Solved.
            </h2>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: isSmallMobile ? '1fr' : isMobile ? '1fr' : 'repeat(3, 1fr)', 
            gap: isMobile ? '1.5rem' : '2rem' 
          }}>
            {problems.map((problem, index) => (
              <div 
                key={index}
                className="gradient-border hover-lift"
                style={{ padding: '2rem' }}
              >
                <div style={{ color: '#4DD0E1', marginBottom: '1.5rem' }}>
                  {problem.icon}
                </div>
                <h3 style={{ 
                  fontSize: isSmallMobile ? '1.125rem' : isMobile ? '1.25rem' : '1.5rem', 
                  fontWeight: 'bold', 
                  marginBottom: '1rem', 
                  color: 'white' 
                }}>
                  {problem.title}
                </h3>
                <p style={{ 
                  color: '#9ca3af', 
                  lineHeight: 1.6,
                  fontSize: isSmallMobile ? '0.875rem' : '1rem'
                }}>
                  {problem.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" style={{ 
        position: 'relative', 
        zIndex: 10, 
        padding: isMobile ? '4rem 1rem' : '6rem 1.5rem' 
      }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: isMobile ? '2rem' : '4rem' }}>
            <h2 style={{ 
              fontSize: isSmallMobile ? '1.75rem' : isMobile ? '2.25rem' : '3rem', 
              fontWeight: 'bold',
              background: 'linear-gradient(135deg, #4DD0E1, #14B8A6, #10B981)',
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text',
              color: 'transparent'
            }}>
              How Fuze Empowers Your Development
            </h2>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: isSmallMobile ? '1fr' : isMobile ? '1fr' : 'repeat(3, 1fr)', 
            gap: isMobile ? '1.5rem' : '2rem' 
          }}>
            {steps.map((step, index) => (
              <div 
                key={index}
                className="gradient-border hover-lift"
                style={{ padding: isMobile ? '1.5rem' : '2rem', textAlign: 'center' }}
              >
                <div style={{ color: '#4DD0E1', marginBottom: '1.5rem', display: 'flex', justifyContent: 'center' }}>
                  {step.icon}
                </div>
                <h3 style={{ 
                  fontSize: isSmallMobile ? '1.125rem' : isMobile ? '1.25rem' : '1.5rem', 
                  fontWeight: 'bold', 
                  marginBottom: '1rem', 
                  color: 'white' 
                }}>
                  {step.title}
                </h3>
                <p style={{ 
                  color: '#9ca3af', 
                  lineHeight: 1.6,
                  fontSize: isSmallMobile ? '0.875rem' : '1rem'
                }}>
                  {step.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" style={{ 
        position: 'relative', 
        zIndex: 10, 
        padding: isMobile ? '4rem 1rem' : '6rem 1.5rem',
        background: 'transparent'
      }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: isMobile ? '2rem' : '4rem' }}>
            <h2 style={{ 
              fontSize: isSmallMobile ? '1.75rem' : isMobile ? '2.25rem' : '3rem', 
              fontWeight: 'bold', 
              color: 'white' 
            }}>
              Features Designed for Your Success
            </h2>
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: isSmallMobile ? '1fr' : isMobile ? '1fr' : 'repeat(3, 1fr)', 
            gap: isMobile ? '1.5rem' : '2rem' 
          }}>
            {features.map((feature, index) => (
              <div 
                key={index}
                className="gradient-border hover-lift"
                style={{ padding: '2rem' }}
              >
                <div style={{ color: '#4DD0E1', marginBottom: '1.5rem' }}>
                  {feature.icon}
                </div>
                <h3 style={{ 
                  fontSize: isSmallMobile ? '1rem' : isMobile ? '1.125rem' : '1.25rem', 
                  fontWeight: 'bold', 
                  marginBottom: '1rem', 
                  color: 'white' 
                }}>
                  {feature.title}
                </h3>
                <p style={{ 
                  color: '#9ca3af', 
                  lineHeight: 1.6,
                  fontSize: isSmallMobile ? '0.875rem' : '0.95rem'
                }}>
                  {feature.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ 
        position: 'relative', 
        zIndex: 10, 
        padding: isMobile ? '4rem 1rem' : '6rem 1.5rem' 
      }}>
        <div style={{ maxWidth: '900px', margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ 
            fontSize: isSmallMobile ? '1.5rem' : isMobile ? '2rem' : '3rem', 
            fontWeight: 'bold', 
            marginBottom: '1.5rem',
            background: 'linear-gradient(135deg, #4DD0E1, #14B8A6, #10B981)',
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            color: 'transparent',
            lineHeight: 1.2
          }}>
            Ready to Transform Your Learning & Building Process?
          </h2>
          
          <p style={{ 
            fontSize: isSmallMobile ? '1rem' : isMobile ? '1.125rem' : '1.25rem', 
            color: '#d1d5db', 
            marginBottom: isMobile ? '2rem' : '3rem' 
          }}>
            Join Fuze today and take control of your developer journey.
          </p>

          <button 
            onClick={handleStartForFree}
            style={{
            background: 'linear-gradient(135deg, #4DD0E1 0%, #14B8A6 50%, #10B981 100%)',
            color: '#fff',
            padding: isSmallMobile ? '1rem 2rem' : isMobile ? '1.125rem 2.5rem' : '1.25rem 3rem',
            border: 'none',
            borderRadius: '50px',
            fontWeight: '600',
            fontSize: isSmallMobile ? '1rem' : isMobile ? '1.125rem' : '1.25rem',
            cursor: 'pointer',
            boxShadow: '0 12px 40px rgba(77, 208, 225, 0.4)',
            transition: 'all 0.3s ease',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.75rem',
            width: isSmallMobile ? '100%' : 'auto'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-4px) scale(1.05)';
            e.currentTarget.style.boxShadow = '0 16px 48px rgba(77, 208, 225, 0.6)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0) scale(1)';
            e.currentTarget.style.boxShadow = '0 12px 40px rgba(77, 208, 225, 0.4)';
          }}>
            <Zap size={24} />
            {isAuthenticated ? 'Go to Dashboard' : 'Get Started with Fuze'}
            <ArrowRight size={24} />
          </button>
          
          <p style={{ 
            fontSize: isSmallMobile ? '0.75rem' : '0.875rem', 
            color: '#6b7280', 
            marginTop: '1.5rem' 
          }}>
            No credit card required • Set up in 30 seconds
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ 
        position: 'relative', 
        zIndex: 10, 
        borderTop: '1px solid rgba(77, 208, 225, 0.1)', 
        padding: isMobile ? '3rem 1rem 2rem' : '4rem 1.5rem 2rem',
        background: 'transparent',
        marginTop: '4rem'
      }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', width: '100%' }}>
          {/* Main Footer Content */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: isSmallMobile ? '1fr' : isMobile ? 'repeat(2, 1fr)' : 'repeat(auto-fit, minmax(200px, 1fr))', 
            gap: isMobile ? '2rem' : '3rem',
            marginBottom: isMobile ? '2rem' : '3rem'
          }}>
            {/* Brand Section */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                <Zap 
                  size={28}
                  style={{ 
                    color: '#4DD0E1',
                    flexShrink: 0
                  }} 
                />
                <span style={{ 
                  fontSize: '1.25rem', 
                  fontWeight: '700', 
                  background: 'linear-gradient(135deg, #4DD0E1 0%, #7C3AED 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text'
                }}>
                  Fuze
                </span>
              </div>
              <p style={{ 
                color: '#6b7280', 
                fontSize: '0.875rem', 
                lineHeight: '1.6',
                maxWidth: '280px'
              }}>
                Intelligently connect your scattered knowledge to your projects, eliminating stagnation and information overload.
              </p>
            </div>
            
            {/* Quick Links */}
            <div>
              <h3 style={{ 
                color: '#e5e7eb', 
                fontSize: '0.875rem', 
                fontWeight: '600', 
                marginBottom: '1rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                Legal
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <a href="#" style={{ 
                color: '#9ca3af', 
                textDecoration: 'none', 
                fontSize: '0.875rem',
                  transition: 'all 0.3s ease',
                  width: 'fit-content'
                }} 
                onMouseEnter={(e) => {
                  e.target.style.color = '#4DD0E1';
                  e.target.style.transform = 'translateX(4px)';
                }} 
                onMouseLeave={(e) => {
                  e.target.style.color = '#9ca3af';
                  e.target.style.transform = 'translateX(0)';
                }}>
                Privacy Policy
              </a>
              <a href="#" style={{ 
                color: '#9ca3af', 
                textDecoration: 'none', 
                fontSize: '0.875rem',
                  transition: 'all 0.3s ease',
                  width: 'fit-content'
                }} 
                onMouseEnter={(e) => {
                  e.target.style.color = '#4DD0E1';
                  e.target.style.transform = 'translateX(4px)';
                }} 
                onMouseLeave={(e) => {
                  e.target.style.color = '#9ca3af';
                  e.target.style.transform = 'translateX(0)';
                }}>
                Terms of Service
              </a>
              </div>
            </div>

            {/* Contact Section */}
            <div>
              <h3 style={{ 
                color: '#e5e7eb', 
                fontSize: '0.875rem', 
                fontWeight: '600', 
                marginBottom: '1rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                Contact
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <a href="mailto:jainujjwal1609@gmail.com" style={{
                color: '#9ca3af',
                textDecoration: 'none',
                fontSize: '0.875rem',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  width: 'fit-content'
                }}
                onMouseEnter={(e) => {
                  e.target.style.color = '#4DD0E1';
                  e.target.style.transform = 'translateX(4px)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.color = '#9ca3af';
                  e.target.style.transform = 'translateX(0)';
                }}>
                  <Mail size={16} />
                  <span>jainujjwal1609@gmail.com</span>
                </a>
              </div>
            </div>
          </div>

          {/* Bottom Bar */}
          <div style={{ 
            borderTop: '1px solid rgba(77, 208, 225, 0.1)', 
            paddingTop: '2rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            {/* Social Links */}
            <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
              <a
                href="https://github.com/ujjwaljain16"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: '#6b7280',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                onMouseEnter={(e) => {
                  e.target.style.color = '#4DD0E1';
                  e.target.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.color = '#6b7280';
                  e.target.style.transform = 'translateY(0)';
                }}
              >
                <Github size={20} />
              </a>
              <a
                href="https://www.linkedin.com/in/ujjwal-jain-306b60323/"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: '#6b7280',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                onMouseEnter={(e) => {
                  e.target.style.color = '#4DD0E1';
                  e.target.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.color = '#6b7280';
                  e.target.style.transform = 'translateY(0)';
                }}
              >
                <Linkedin size={20} />
              </a>
            </div>

            {/* Copyright */}
            <div style={{ 
              color: '#6b7280', 
              fontSize: '0.875rem',
              textAlign: 'center'
            }}>
              © {new Date().getFullYear()} Fuze. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}