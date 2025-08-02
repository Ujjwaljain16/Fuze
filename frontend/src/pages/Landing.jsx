import React, { useState, useEffect, useRef } from 'react'; 
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
  FolderRoot,
  Hourglass,
  CircleDashed,
  Compass,
  GitFork,
  ArrowRight,
  ChevronDown
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function FuzeLanding() {
  const [isVisible, setIsVisible] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [particles, setParticles] = useState([]);
  const canvasRef = useRef(null);

  useEffect(() => {
    setIsVisible(true);
    
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Generate floating particles
  useEffect(() => {
    const generateParticles = () => {
      const newParticles = Array.from({ length: 50 }, (_, i) => ({
        id: i,
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
        size: Math.random() * 3 + 1,
        speedX: (Math.random() - 0.5) * 0.5,
        speedY: (Math.random() - 0.5) * 0.5,
        opacity: Math.random() * 0.5 + 0.1,
        color: Math.random() > 0.5 ? '#60a5fa' : '#a855f7'
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

  const navigate = useNavigate();

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'black', color: 'white', overflow: 'hidden', position: 'relative' }}>
      {/* Interactive Background Effects */}
      
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
              transition: 'all 0.1s ease'
            }}
          />
        ))}
      </div>

      {/* Mouse-following gradient orbs */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 2, pointerEvents: 'none' }}>
        <div 
          style={{
            position: 'absolute',
            width: '300px',
            height: '300px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(96, 165, 250, 0.15) 0%, rgba(168, 85, 247, 0.1) 50%, transparent 70%)',
            left: mousePos.x - 150,
            top: mousePos.y - 150,
            transition: 'all 0.3s ease-out',
            filter: 'blur(20px)'
          }}
        />
        <div 
          style={{
            position: 'absolute',
            width: '200px',
            height: '200px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(236, 72, 153, 0.1) 0%, rgba(168, 85, 247, 0.05) 50%, transparent 70%)',
            left: mousePos.x - 100,
            top: mousePos.y - 100,
            transition: 'all 0.2s ease-out',
            filter: 'blur(15px)'
          }}
        />
      </div>

      {/* Dynamic Grid Background */}
      <div style={{ position: 'fixed', inset: 0, opacity: 0.05, zIndex: 0 }}>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(20, 1fr)', 
          gridTemplateRows: 'repeat(20, 1fr)', 
          height: '100%', 
          width: '100%',
          transform: `translate(${mousePos.x * 0.01}px, ${mousePos.y * 0.01}px)`,
          transition: 'transform 0.5s ease-out'
        }}>
          {Array.from({ length: 400 }).map((_, i) => (
            <div
              key={i}
              style={{
                border: '1px solid rgba(96, 165, 250, 0.1)',
                animation: `gridPulse ${3 + Math.random() * 2}s ease-in-out infinite`,
                animationDelay: `${Math.random() * 3}s`
              }}
            />
          ))}
        </div>
      </div>

      {/* Animated Background */}
      <div style={{ position: 'fixed', inset: 0, opacity: 0.2, zIndex: 0 }}>
        <div 
          style={{
            position: 'absolute',
            width: '24rem',
            height: '24rem',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, transparent 70%)',
            left: mousePos.x - 192,
            top: mousePos.y - 192,
            transition: 'all 0.3s ease-out'
          }}
        />
      </div>

      {/* Lightning Grid Background */}
      <div style={{ position: 'fixed', inset: 0, opacity: 0.1, zIndex: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gridTemplateRows: 'repeat(12, 1fr)', height: '100%', width: '100%' }}>
          {Array.from({ length: 144 }).map((_, i) => (
            <div
              key={i}
              style={{
                border: '1px solid rgba(59, 130, 246, 0.2)',
                animation: `pulse ${2 + Math.random() * 2}s ease-in-out infinite`,
                animationDelay: `${Math.random() * 3}s`
              }}
            />
          ))}
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ 
        position: 'fixed', 
        top: 0,
        left: 0,
        right: 0,
        zIndex: 50, 
        padding: '1.5rem', 
        background: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid rgba(59, 130, 246, 0.2)',
        transition: 'all 1s',
        transform: isVisible ? 'translateY(0)' : 'translateY(-2.5rem)',
        opacity: isVisible ? 1 : 0
      }}>
        <div style={{ maxWidth: '80rem', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ position: 'relative' }}>
              <Zap style={{ width: '2rem', height: '2rem', color: '#60a5fa' }} />
              <div style={{ 
                position: 'absolute', 
                inset: 0, 
                filter: 'blur(0.5rem)', 
                backgroundColor: '#60a5fa', 
                opacity: 0.5,
                animation: 'pulse 2s ease-in-out infinite'
              }} />
            </div>
            <div>
              <span style={{ 
                fontSize: '1.5rem', 
                fontWeight: 'bold',
                background: 'linear-gradient(to right, #60a5fa, #a855f7)',
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                color: 'transparent'
              }}>
                Fuze
              </span>
              <div style={{ fontSize: '0.75rem', color: '#93c5fd', fontWeight: 500, letterSpacing: '0.05em', textTransform: 'uppercase', opacity: 0.8 }}>
                Strike Through the Chaos
              </div>
            </div>
          </div>
          <div style={{ display: 'none', gap: '2rem' }} className="md:flex">
            <button 
              onClick={() => scrollToSection('problems')}
              style={{ color: 'white', background: 'none', border: 'none', cursor: 'pointer', transition: 'color 0.3s' }} 
              onMouseEnter={(e) => e.target.style.color = '#60a5fa'} 
              onMouseLeave={(e) => e.target.style.color = 'white'}
            >
              Problems
            </button>
            <button 
              onClick={() => scrollToSection('how-it-works')}
              style={{ color: 'white', background: 'none', border: 'none', cursor: 'pointer', transition: 'color 0.3s' }} 
              onMouseEnter={(e) => e.target.style.color = '#60a5fa'} 
              onMouseLeave={(e) => e.target.style.color = 'white'}
            >
              How It Works
            </button>
            <button 
              onClick={() => scrollToSection('features')}
              style={{ color: 'white', background: 'none', border: 'none', cursor: 'pointer', transition: 'color 0.3s' }} 
              onMouseEnter={(e) => e.target.style.color = '#60a5fa'} 
              onMouseLeave={(e) => e.target.style.color = 'white'}
            >
              Features
            </button>
          </div>
          <button className="btn-primary" onClick={() => navigate('/login')}>
            Start for Free
          </button>
        </div>
      </nav>

      {/* Section 1: Hero Section */}
      <section style={{ position: 'relative', zIndex: 40, padding: '0 1.5rem', paddingTop: '8rem', paddingBottom: '4rem', minHeight: '90vh', display: 'flex', alignItems: 'center' }}>
        <div style={{ maxWidth: '80rem', margin: '0 auto', width: '100%' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4rem', alignItems: 'center' }} className="md:grid-cols-2">
            {/* Left: Content */}
            <div style={{ 
              transition: 'all 1.5s',
              transitionDelay: '0.3s',
              transform: isVisible ? 'translateY(0)' : 'translateY(5rem)',
              opacity: isVisible ? 1 : 0
            }}>
              <h1 style={{ 
                fontSize: '3.5rem', 
                fontWeight: 'bold', 
                marginBottom: '1.5rem', 
                lineHeight: 1.1,
                background: 'linear-gradient(to right, white, #bfdbfe, #c084fc)',
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                color: 'transparent'
              }}>
                Unleash Your Dev Potential.
                <br />
                <span style={{ 
                  background: 'linear-gradient(to right, #60a5fa, #a855f7, #ec4899)',
                  WebkitBackgroundClip: 'text',
                  backgroundClip: 'text',
                  color: 'transparent'
                }}>
                  Conquer Project Chaos.
                </span>
              </h1>
              
              <p style={{ 
                fontSize: '1.25rem', 
                color: '#d1d5db', 
                marginBottom: '3rem', 
                lineHeight: 1.6
              }}>
                Fuze intelligently connects your scattered knowledge to your projects, eliminating stagnation, FOMO, and information overload.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', justifyContent: 'flex-start', alignItems: 'flex-start' }} className="sm:flex-row">
                <button className="btn-primary" style={{ fontSize: '1.125rem', padding: '1rem 2rem' }} onClick={() => navigate('/login')}>
                  <span style={{ display: 'flex', alignItems: 'center' }}>
                    Start for Free
                    <ArrowRight style={{ marginLeft: '0.5rem', width: '1.25rem', height: '1.25rem' }} />
                  </span>
                </button>
                
                <button 
                  onClick={() => scrollToSection('problems')}
                  className="btn-secondary" 
                  style={{ fontSize: '1.125rem', padding: '1rem 2rem' }}
                >
                  Learn More
                </button>
              </div>
            </div>

            {/* Right: Mockup/Illustration */}
            <div style={{ 
              transition: 'all 1.5s',
              transitionDelay: '0.6s',
              transform: isVisible ? 'translateY(0)' : 'translateY(5rem)',
              opacity: isVisible ? 1 : 0,
              position: 'relative'
            }}>
              <div className="card" style={{ 
                background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.8), rgba(0, 0, 0, 0.8))',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                borderRadius: '1rem',
                padding: '2rem',
                position: 'relative',
                overflow: 'hidden'
              }}>
                {/* Mockup Content */}
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1.5rem' }}>
                  <div style={{ width: '0.5rem', height: '0.5rem', borderRadius: '50%', backgroundColor: '#ef4444', marginRight: '0.5rem' }} />
                  <div style={{ width: '0.5rem', height: '0.5rem', borderRadius: '50%', backgroundColor: '#f59e0b', marginRight: '0.5rem' }} />
                  <div style={{ width: '0.5rem', height: '0.5rem', borderRadius: '50%', backgroundColor: '#10b981' }} />
                </div>
                
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ height: '0.5rem', backgroundColor: '#374151', borderRadius: '0.25rem', marginBottom: '0.5rem', width: '60%' }} />
                  <div style={{ height: '0.5rem', backgroundColor: '#4b5563', borderRadius: '0.25rem', width: '80%' }} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div className="card" style={{ padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <Sparkles style={{ width: '1rem', height: '1rem', color: '#60a5fa', marginRight: '0.5rem' }} />
                      <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#60a5fa' }}>AI Recommendation</div>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>React Best Practices</div>
                  </div>
                  <div className="card" style={{ padding: '1rem', background: 'rgba(124, 58, 237, 0.1)', border: '1px solid rgba(124, 58, 237, 0.2)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <Link style={{ width: '1rem', height: '1rem', color: '#a855f7', marginRight: '0.5rem' }} />
                      <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#a855f7' }}>Connected</div>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>TypeScript Guide</div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <div style={{ width: '2rem', height: '2rem', borderRadius: '50%', background: 'linear-gradient(45deg, #60a5fa, #a855f7)', marginRight: '0.75rem' }} />
                    <div>
                      <div style={{ fontSize: '0.875rem', fontWeight: '600', color: 'white' }}>Project: E-commerce App</div>
                      <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>3 resources connected</div>
                    </div>
                  </div>
                  <div style={{ 
                    width: '2rem', 
                    height: '2rem', 
                    borderRadius: '50%', 
                    background: 'linear-gradient(45deg, #10b981, #06b6d4)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <ChevronDown style={{ width: '1rem', height: '1rem', color: 'white' }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: Problems We Solve */}
      <section id="problems" style={{ position: 'relative', zIndex: 40, padding: '0 1.5rem', paddingTop: '4rem', paddingBottom: '4rem', backgroundColor: 'rgba(0, 0, 0, 0.5)' }}>
        <div style={{ maxWidth: '80rem', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '5rem' }}>
            <h2 style={{ 
              fontSize: '3rem', 
              fontWeight: 'bold', 
              marginBottom: '1.5rem',
              background: 'linear-gradient(to right, white, #d1d5db)',
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text',
              color: 'transparent'
            }}>
              Your Biggest Challenges, Solved.
            </h2>
          </div>

          <div style={{ display: 'grid', gap: '2rem' }} className="md:grid-cols-3">
            {problems.map((problem, index) => (
                             <div 
                 key={index}
                 className="card"
                 style={{
                   animationDelay: `${index * 200}ms`,
                   position: 'relative',
                   overflow: 'hidden',
                   cursor: 'pointer',
                   transition: 'all 0.3s ease'
                 }}
                 onMouseEnter={(e) => {
                   const overlay = e.currentTarget.querySelector('.problem-overlay');
                   if (overlay) overlay.style.opacity = '1';
                 }}
                 onMouseLeave={(e) => {
                   const overlay = e.currentTarget.querySelector('.problem-overlay');
                   if (overlay) overlay.style.opacity = '0';
                 }}
               >
                                 <div 
                   className="problem-overlay"
                   style={{ 
                     position: 'absolute', 
                     inset: 0, 
                     borderRadius: '1.5rem', 
                     background: 'linear-gradient(135deg, rgba(96, 165, 250, 0.1), rgba(168, 85, 247, 0.1))', 
                     opacity: 0,
                     transition: 'opacity 0.5s'
                   }} 
                 />
                
                                 <div style={{ position: 'relative', zIndex: 10 }}>
                   <div style={{ 
                     color: '#60a5fa', 
                     marginBottom: '1.5rem',
                     transition: 'all 0.3s ease',
                     transform: 'scale(1)'
                   }} 
                   onMouseEnter={(e) => {
                     e.target.style.color = '#a855f7';
                     e.target.style.transform = 'scale(1.1)';
                   }}
                   onMouseLeave={(e) => {
                     e.target.style.color = '#60a5fa';
                     e.target.style.transform = 'scale(1)';
                   }}>
                     {problem.icon}
                   </div>
                   <h3 style={{ 
                     fontSize: '1.5rem', 
                     fontWeight: 'bold', 
                     marginBottom: '1rem', 
                     color: 'white',
                     transition: 'color 0.3s ease'
                   }}
                   onMouseEnter={(e) => e.target.style.color = '#60a5fa'}
                   onMouseLeave={(e) => e.target.style.color = 'white'}>
                     {problem.title}
                   </h3>
                   <p style={{ color: '#9ca3af', lineHeight: 1.6 }}>
                     {problem.body}
                   </p>
                 </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 3: How Fuze Works */}
      <section id="how-it-works" style={{ position: 'relative', zIndex: 40, padding: '0 1.5rem', paddingTop: '4rem', paddingBottom: '4rem' }}>
        <div style={{ maxWidth: '80rem', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '5rem' }}>
            <h2 style={{ 
              fontSize: '3rem', 
              fontWeight: 'bold', 
              marginBottom: '1.5rem',
              background: 'linear-gradient(to right, #60a5fa, #a855f7)',
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text',
              color: 'transparent'
            }}>
              How Fuze Empowers Your Development
            </h2>
          </div>

          <div style={{ display: 'grid', gap: '2rem' }} className="md:grid-cols-3">
            {steps.map((step, index) => (
                             <div 
                 key={index}
                 className="card"
                 style={{
                   animationDelay: `${index * 300}ms`,
                   position: 'relative',
                   textAlign: 'center',
                   cursor: 'pointer',
                   transition: 'all 0.3s ease'
                 }}
                 onMouseEnter={(e) => {
                   e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)';
                   e.currentTarget.style.boxShadow = '0 20px 40px rgba(96, 165, 250, 0.2)';
                   const overlay = e.currentTarget.querySelector('.step-overlay');
                   if (overlay) overlay.style.opacity = '1';
                 }}
                 onMouseLeave={(e) => {
                   e.currentTarget.style.transform = 'translateY(0) scale(1)';
                   e.currentTarget.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
                   const overlay = e.currentTarget.querySelector('.step-overlay');
                   if (overlay) overlay.style.opacity = '0';
                 }}
               >
                 <div 
                   className="step-overlay"
                   style={{ 
                     position: 'absolute', 
                     inset: 0, 
                     borderRadius: '1.5rem', 
                     background: 'linear-gradient(135deg, rgba(96, 165, 250, 0.1), rgba(168, 85, 247, 0.1))', 
                     opacity: 0,
                     transition: 'opacity 0.3s ease'
                   }} 
                 />
                 
                 <div style={{ position: 'relative', zIndex: 10, padding: '2rem' }}>
                   <div style={{ 
                     color: '#60a5fa', 
                     marginBottom: '1.5rem', 
                     display: 'flex', 
                     justifyContent: 'center',
                     transition: 'all 0.3s ease',
                     transform: 'scale(1)'
                   }}
                   onMouseEnter={(e) => {
                     e.target.style.color = '#a855f7';
                     e.target.style.transform = 'scale(1.1)';
                   }}
                   onMouseLeave={(e) => {
                     e.target.style.color = '#60a5fa';
                     e.target.style.transform = 'scale(1)';
                   }}>
                     {step.icon}
                   </div>
                   <h3 style={{ 
                     fontSize: '1.5rem', 
                     fontWeight: 'bold', 
                     marginBottom: '1rem', 
                     color: 'white',
                     transition: 'color 0.3s ease'
                   }}
                   onMouseEnter={(e) => e.target.style.color = '#60a5fa'}
                   onMouseLeave={(e) => e.target.style.color = 'white'}>
                     {step.title}
                   </h3>
                   <p style={{ color: '#9ca3af', lineHeight: 1.6 }}>
                     {step.body}
                   </p>
                 </div>
               </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 4: Key Features */}
      <section id="features" style={{ position: 'relative', zIndex: 40, padding: '0 1.5rem', paddingTop: '4rem', paddingBottom: '4rem', backgroundColor: 'rgba(0, 0, 0, 0.5)' }}>
        <div style={{ maxWidth: '80rem', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '5rem' }}>
            <h2 style={{ 
              fontSize: '3rem', 
              fontWeight: 'bold', 
              marginBottom: '1.5rem',
              background: 'linear-gradient(to right, white, #d1d5db)',
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text',
              color: 'transparent'
            }}>
              Features Designed for Your Success
            </h2>
          </div>

          <div style={{ display: 'grid', gap: '2rem' }} className="md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature, index) => (
              <div 
                key={index}
                className="card"
                style={{
                  animationDelay: `${index * 150}ms`,
                  position: 'relative',
                  overflow: 'hidden'
                }}
              >
                <div style={{ 
                  position: 'absolute', 
                  inset: 0, 
                  borderRadius: '1.5rem', 
                  background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(124, 58, 237, 0.1))', 
                  opacity: 0,
                  transition: 'opacity 0.5s'
                }} />
                
                <div style={{ position: 'relative', zIndex: 10 }}>
                  <div style={{ color: '#60a5fa', marginBottom: '1.5rem' }}>
                    {feature.icon}
                  </div>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '1rem', color: 'white' }}>
                    {feature.title}
                  </h3>
                  <p style={{ color: '#9ca3af', lineHeight: 1.6 }}>
                    {feature.body}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Section 5: Call to Action */}
      <section style={{ position: 'relative', zIndex: 40, padding: '0 1.5rem', paddingTop: '4rem', paddingBottom: '4rem' }}>
        <div style={{ maxWidth: '64rem', margin: '0 auto', textAlign: 'center', position: 'relative' }}>
          <div style={{ position: 'relative', zIndex: 1 }}>
            <h2 style={{ 
              fontSize: '3rem', 
              fontWeight: 'bold', 
              marginBottom: '2rem',
              background: 'linear-gradient(to right, #60a5fa, #a855f7, #ec4899)',
              WebkitBackgroundClip: 'text',
              backgroundClip: 'text',
              color: 'transparent'
            }}>
              Ready to Transform Your Learning & Building Process?
            </h2>
            
            <p style={{ fontSize: '1.25rem', color: '#d1d5db', marginBottom: '3rem', maxWidth: '32rem', margin: '0 auto 3rem auto' }}>
              Join Fuze today and take control of your developer journey.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <button className="btn-primary" style={{ fontSize: '1.25rem', padding: '1.25rem 3rem' }} onClick={() => navigate('/login')}>
                <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Zap style={{ marginRight: '0.75rem', width: '1.5rem', height: '1.5rem' }} />
                  Get Started with Fuze
                  <ArrowRight style={{ marginLeft: '0.75rem', width: '1.5rem', height: '1.5rem' }} />
                </span>
              </button>
              
              <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>No credit card required • Set up in 30 seconds</p>
            </div>
          </div>
        </div>
      </section>

      {/* Section 6: Footer */}
      <footer style={{ position: 'relative', zIndex: 40, borderTop: '1px solid #374151', padding: '0 1.5rem', paddingTop: '3rem', paddingBottom: '3rem' }}>
        <div style={{ maxWidth: '80rem', margin: '0 auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Zap style={{ width: '2rem', height: '2rem', color: '#60a5fa' }} />
              <div>
                <span style={{ 
                  fontSize: '1.5rem', 
                  fontWeight: 'bold',
                  background: 'linear-gradient(to right, #60a5fa, #a855f7)',
                  WebkitBackgroundClip: 'text',
                  backgroundClip: 'text',
                  color: 'transparent'
                }}>
                  Fuze
                </span>
                <div style={{ fontSize: '0.75rem', color: '#93c5fd', fontWeight: 500, letterSpacing: '0.05em', textTransform: 'uppercase', opacity: 0.8 }}>
                  Strike Through the Chaos
                </div>
              </div>
            </div>
            
            <div style={{ color: '#9ca3af', fontSize: '0.875rem' }}>
              © 2024 Fuze. All rights reserved.
            </div>
            
            <div style={{ display: 'flex', gap: '2rem', color: '#6b7280' }}>
              <a href="#" style={{ color: '#6b7280', textDecoration: 'none', transition: 'color 0.3s' }} onMouseEnter={(e) => e.target.style.color = '#60a5fa'} onMouseLeave={(e) => e.target.style.color = '#6b7280'}>Privacy Policy</a>
              <a href="#" style={{ color: '#6b7280', textDecoration: 'none', transition: 'color 0.3s' }} onMouseEnter={(e) => e.target.style.color = '#60a5fa'} onMouseLeave={(e) => e.target.style.color = '#6b7280'}>Terms of Service</a>
              <a href="mailto:contact@fuze.dev" style={{ color: '#6b7280', textDecoration: 'none', transition: 'color 0.3s' }} onMouseEnter={(e) => e.target.style.color = '#60a5fa'} onMouseLeave={(e) => e.target.style.color = '#6b7280'}>Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}