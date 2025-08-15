import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import api from '../services/api';
import './linkedin-analyzer-styles.css';

const LinkedInAnalyzer = () => {
  const { user } = useAuth();
  const { showToast } = useToast();
  
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [extractedContent, setExtractedContent] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [isPWAInstalled, setIsPWAInstalled] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [isOffline, setIsOffline] = useState(false);

  // Check PWA installation status
  useEffect(() => {
    const checkPWAStatus = () => {
      if (window.matchMedia('(display-mode: standalone)').matches) {
        setIsPWAInstalled(true);
      }
    };

    checkPWAStatus();
    window.addEventListener('appinstalled', () => setIsPWAInstalled(true));
    
    return () => window.removeEventListener('appinstalled', () => setIsPWAInstalled(true));
  }, []);

  // Check offline status
  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    setIsOffline(!navigator.onLine);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Handle PWA install prompt
  useEffect(() => {
    const handleBeforeInstallPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    
    return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
  }, []);

  // Install PWA
  const installPWA = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      
      if (outcome === 'accepted') {
        console.log('PWA installed successfully');
        setIsPWAInstalled(true);
      }
      
      setDeferredPrompt(null);
    }
  };

  // Extract LinkedIn content
  const extractLinkedInContent = useCallback(async () => {
    if (!linkedinUrl.trim()) {
      showToast('Please enter a LinkedIn URL', 'error');
      return;
    }

    if (!linkedinUrl.includes('linkedin.com')) {
      showToast('Please enter a valid LinkedIn URL', 'error');
      return;
    }

    setIsAnalyzing(true);
    setAnalysisResult(null);
    setExtractedContent(null);
    setRecommendations([]);

    try {
      // Extract content from LinkedIn
      const extractResponse = await api.post('/api/linkedin/extract', {
        url: linkedinUrl,
        user_id: user?.id
      });

      if (extractResponse.data.success) {
        setExtractedContent(extractResponse.data);
        showToast('LinkedIn content extracted successfully!', 'success');
        
        // Automatically analyze the content
        await analyzeContent(extractResponse.data);
      } else {
        showToast('Failed to extract LinkedIn content', 'error');
      }
    } catch (error) {
      console.error('LinkedIn extraction error:', error);
      
      if (error.response?.status === 503) {
        showToast('Offline mode: Content extraction not available', 'warning');
      } else {
        showToast('Failed to extract LinkedIn content. Please try again.', 'error');
      }
    } finally {
      setIsAnalyzing(false);
    }
  }, [linkedinUrl, user?.id, showToast]);

  // Analyze extracted content
  const analyzeContent = async (content) => {
    try {
      const analysisResponse = await api.post('/api/linkedin/analyze', {
        content: content.content,
        title: content.title,
        meta_description: content.meta_description,
        url: linkedinUrl,
        user_id: user?.id,
        project_context: user?.current_project || null
      });

      if (analysisResponse.data.success) {
        setAnalysisResult(analysisResponse.data);
        showToast('Content analysis completed!', 'success');
        
        // Get recommendations based on analysis
        await getRecommendations(analysisResponse.data);
      } else {
        showToast('Failed to analyze content', 'error');
      }
    } catch (error) {
      console.error('Content analysis error:', error);
      
      if (error.response?.status === 503) {
        showToast('Offline mode: Content analysis not available', 'warning');
      } else {
        showToast('Failed to analyze content. Please try again.', 'error');
      }
    }
  };

  // Get recommendations based on analysis
  const getRecommendations = async (analysis) => {
    try {
      const recommendationsResponse = await api.post('/api/recommendations/unified', {
        user_id: user?.id,
        project_description: analysis.summary,
        technologies: analysis.technologies,
        content_type: analysis.content_type,
        difficulty_level: analysis.difficulty_level,
        learning_goals: analysis.learning_goals,
        enhance_with_gemini: true
      });

      if (recommendationsResponse.data.success) {
        setRecommendations(recommendationsResponse.data.recommendations || []);
        showToast('Recommendations generated successfully!', 'success');
      } else {
        showToast('Failed to generate recommendations', 'error');
      }
    } catch (error) {
      console.error('Recommendations error:', error);
      
      if (error.response?.status === 503) {
        showToast('Offline mode: Recommendations not available', 'warning');
      } else {
        showToast('Failed to generate recommendations. Please try again.', 'error');
      }
    }
  };

  // Save content to bookmarks
  const saveToBookmarks = async () => {
    if (!extractedContent) return;

    try {
      const saveResponse = await api.post('/api/bookmarks', {
        title: extractedContent.title,
        url: linkedinUrl,
        content: extractedContent.content,
        user_id: user?.id,
        tags: analysisResult?.technologies || [],
        category: 'linkedin',
        analysis_data: analysisResult
      });

      if (saveResponse.data.success) {
        showToast('Content saved to bookmarks!', 'success');
      } else {
        showToast('Failed to save content', 'error');
      }
    } catch (error) {
      console.error('Save to bookmarks error:', error);
      showToast('Failed to save content. Please try again.', 'error');
    }
  };

  // Share content
  const shareContent = async () => {
    if (navigator.share && extractedContent) {
      try {
        await navigator.share({
          title: extractedContent.title,
          text: extractedContent.content.substring(0, 100) + '...',
          url: linkedinUrl
        });
      } catch (error) {
        console.error('Share error:', error);
      }
    } else {
      // Fallback: copy to clipboard
      try {
        await navigator.clipboard.writeText(linkedinUrl);
        showToast('URL copied to clipboard!', 'success');
      } catch (error) {
        showToast('Failed to copy URL', 'error');
      }
    }
  };

  // Handle file input for LinkedIn URLs
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const urls = e.target.result.split('\n').filter(url => url.trim());
        if (urls.length > 0) {
          setLinkedinUrl(urls[0].trim());
          showToast(`Loaded ${urls.length} LinkedIn URLs`, 'info');
        }
      };
      reader.readAsText(file);
    }
  };

  return (
    <div className="linkedin-analyzer">
      {/* PWA Install Banner */}
      {!isPWAInstalled && deferredPrompt && (
        <div className="pwa-install-banner">
          <div className="pwa-content">
            <div className="pwa-info">
              <h3>🚀 Install Fuze as PWA</h3>
              <p>Get the full experience with offline support and push notifications!</p>
            </div>
            <div className="pwa-actions">
              <button onClick={installPWA} className="btn-install">
                Install App
              </button>
              <button onClick={() => setDeferredPrompt(null)} className="btn-dismiss">
                Maybe Later
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Offline Status */}
      {isOffline && (
        <div className="offline-banner">
          <span>📱 Offline Mode - Some features may be limited</span>
        </div>
      )}

      <div className="analyzer-container">
        <div className="analyzer-header">
          <h1>🔗 LinkedIn Content Analyzer</h1>
          <p>Extract, analyze, and get AI-powered recommendations from LinkedIn posts</p>
        </div>

        {/* URL Input Section */}
        <div className="input-section">
          <div className="url-input-container">
            <input
              type="url"
              value={linkedinUrl}
              onChange={(e) => setLinkedinUrl(e.target.value)}
              placeholder="Paste LinkedIn post URL here..."
              className="url-input"
              disabled={isAnalyzing}
            />
            <button
              onClick={extractLinkedInContent}
              disabled={isAnalyzing || !linkedinUrl.trim()}
              className="btn-analyze"
            >
              {isAnalyzing ? '🔍 Analyzing...' : '🔍 Analyze Content'}
            </button>
          </div>

          {/* File Upload */}
          <div className="file-upload-section">
            <label htmlFor="url-file" className="file-upload-label">
              📁 Upload URL List (Optional)
            </label>
            <input
              id="url-file"
              type="file"
              accept=".txt,.csv"
              onChange={handleFileUpload}
              className="file-input"
            />
            <small>Upload a text file with one LinkedIn URL per line</small>
          </div>
        </div>

        {/* Analysis Results */}
        {extractedContent && (
          <div className="results-section">
            <div className="content-preview">
              <h3>📄 Extracted Content</h3>
              <div className="content-card">
                <h4>{extractedContent.title}</h4>
                <p className="meta-info">
                  <span>Quality Score: {extractedContent.quality_score}/10</span>
                  <span>Method: {extractedContent.method_used}</span>
                </p>
                <div className="content-text">
                  {extractedContent.content.substring(0, 300)}...
                </div>
                <div className="content-actions">
                  <button onClick={saveToBookmarks} className="btn-save">
                    💾 Save to Bookmarks
                  </button>
                  <button onClick={shareContent} className="btn-share">
                    📤 Share Content
                  </button>
                </div>
              </div>
            </div>

            {/* AI Analysis */}
            {analysisResult && (
              <div className="ai-analysis">
                <h3>🤖 AI Analysis</h3>
                <div className="analysis-grid">
                  <div className="analysis-card">
                    <h4>Technologies</h4>
                    <div className="tech-tags">
                      {analysisResult.technologies?.map((tech, index) => (
                        <span key={index} className="tech-tag">{tech}</span>
                      ))}
                    </div>
                  </div>
                  
                  <div className="analysis-card">
                    <h4>Content Type</h4>
                    <p>{analysisResult.content_type}</p>
                  </div>
                  
                  <div className="analysis-card">
                    <h4>Difficulty Level</h4>
                    <p>{analysisResult.difficulty_level}</p>
                  </div>
                  
                  <div className="analysis-card">
                    <h4>Learning Goals</h4>
                    <p>{analysisResult.learning_goals}</p>
                  </div>
                </div>
                
                <div className="summary-section">
                  <h4>AI Summary</h4>
                  <p>{analysisResult.summary}</p>
                </div>
              </div>
            )}

            {/* Recommendations */}
            {recommendations.length > 0 && (
              <div className="recommendations-section">
                <h3>💡 Personalized Recommendations</h3>
                <div className="recommendations-grid">
                  {recommendations.slice(0, 6).map((rec, index) => (
                    <div key={index} className="recommendation-card">
                      <h4>{rec.title}</h4>
                      <p className="rec-url">{rec.url}</p>
                      <p className="rec-reason">{rec.reason}</p>
                      <div className="rec-meta">
                        <span className="rec-score">Score: {rec.score?.toFixed(2)}</span>
                        <span className="rec-tech">{rec.technologies?.join(', ')}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* PWA Features Info */}
        <div className="pwa-features">
          <h3>📱 PWA Features</h3>
          <div className="features-grid">
            <div className="feature-card">
              <span className="feature-icon">🔒</span>
              <h4>Offline Support</h4>
              <p>Access your saved content and analysis even without internet</p>
            </div>
            
            <div className="feature-card">
              <span className="feature-icon">📲</span>
              <h4>Install as App</h4>
              <p>Add to home screen for quick access like a native app</p>
            </div>
            
            <div className="feature-card">
              <span className="feature-icon">🔔</span>
              <h4>Push Notifications</h4>
              <p>Get notified when analysis is complete</p>
            </div>
            
            <div className="feature-card">
              <span className="feature-icon">🔄</span>
              <h4>Background Sync</h4>
              <p>Content analysis continues even when app is closed</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LinkedInAnalyzer;





