# 🚀 FUZE - Complete Application Workflow

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [User Onboarding Flow](#user-onboarding-flow)
3. [Extension Integration](#extension-integration)
4. [Content Processing Pipeline](#content-processing-pipeline)
5. [Recommendation Generation](#recommendation-generation)
6. [Complete User Journey](#complete-user-journey)
7. [Technical Architecture](#technical-architecture)

---

## 🎯 System Overview

**FUZE** is an AI-powered learning companion that:
- Collects user's bookmarks via Chrome extension
- Analyzes content using Gemini AI
- Generates personalized learning recommendations
- Tracks user progress and adapts to learning patterns

**Core Technologies:**
- **Backend**: Flask (Python) + PostgreSQL + Redis
- **AI**: Gemini 2.0 Flash (Google AI)
- **ML/NLP**: Sentence Transformers, TF-IDF
- **Frontend**: React + Vite
- **Extension**: Chrome Extension (Manifest V3)

---

## 👤 User Onboarding Flow

### **Step 1: Registration**

```mermaid
User → Frontend → Backend → Database
```

**Frontend** (`frontend/src/pages/Login.jsx`):
```javascript
// User fills registration form
{
  username: "john_doe",
  email: "john@example.com",
  password: "securepassword",
  name: "John Doe"
}

// POST to /api/auth/register
const result = await register(username, email, password, name);
```

**Backend** (`blueprints/auth.py`):
```python
@auth_bp.route('/register', methods=['POST'])
def register():
    # 1. Validate input
    if not username or not email or not password:
        return error
    
    # 2. Check for duplicates
    if User.query.filter_by(username=username).first():
        return 'Username exists', 409
    
    # 3. Create user
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password)
    )
    
    # 4. Save to database
    db.session.add(user)
    db.session.commit()
    
    return 'User registered', 201
```

**Database** (`models.py`):
```python
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True)
    email = Column(String(120), unique=True)
    password_hash = Column(String(256))
    technology_interests = Column(TEXT)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    saved_content = relationship('SavedContent')
    projects = relationship('Project')
```

### **Step 2: Login & Authentication**

**Frontend**:
```javascript
// POST to /api/auth/login
const result = await login(email, password);

// Receives JWT tokens
{
  access_token: "eyJ0eXAiOiJKV1QiLCJhbGc...",
  user: { id: 1, username: "john_doe", email: "..." }
}

// Store in AuthContext for future requests
```

**Backend**:
```python
@auth_bp.route('/login', methods=['POST'])
def login():
    # 1. Validate credentials
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return 'Invalid credentials', 401
    
    # 2. Create JWT tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    # 3. Return tokens + user info
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }
```

### **Step 3: Dashboard Access**

User lands on `/app/dashboard` with:
- ✅ Authenticated session (JWT token)
- ✅ Access to all features
- ✅ Ready to create projects and save content

---

## 🔌 Extension Integration

### **Extension Setup**

**User Actions**:
1. Install Chrome Extension from `BookmarkExtension/`
2. Click extension icon
3. Configure API URL (e.g., `http://localhost:5000`)
4. Login with credentials

**Extension Login** (`BookmarkExtension/popup/popup.js`):
```javascript
// User enters credentials in extension popup
const authToken = await loginToFuze(email, password);

// Store token in Chrome storage
await chrome.storage.local.set({ 
  authToken: authToken,
  apiUrl: API_URL 
});

// Enable auto-sync
await chrome.storage.local.set({ autoSync: true });
```

### **Bookmark Sync Process**

#### **Method 1: Auto-Sync (Background)**

**Trigger**: User creates bookmark in Chrome

**Extension** (`BookmarkExtension/background.js`):
```javascript
// Chrome listens for new bookmarks
chrome.bookmarks.onCreated.addListener(async (id) => {
  // 1. Get bookmark details
  const [bookmark] = await chrome.bookmarks.get(id);
  
  // 2. Get parent folder for category
  const [parent] = await chrome.bookmarks.get(bookmark.parentId);
  const category = parent.title.toLowerCase();
  
  // 3. Prepare data
  const bookmarkData = {
    url: bookmark.url,
    title: bookmark.title,
    description: '',
    category: category,
    tags: []
  };
  
  // 4. Get auth token
  const authToken = await getAuthToken();
  
  // 5. Send to backend
  const response = await fetch(`${apiUrl}/api/bookmarks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify(bookmarkData)
  });
  
  // 6. Show notification
  if (response.ok) {
    chrome.notifications.create({
      type: 'basic',
      title: 'Bookmark Saved',
      message: `"${bookmark.title}" synced to Fuze`
    });
  }
});
```

#### **Method 2: Manual Save (Extension Popup)**

**Extension** (`BookmarkExtension/popup/popup.js`):
```javascript
// User clicks "Save Current Page" button
document.getElementById('saveButton').addEventListener('click', async () => {
  // 1. Get current tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  // 2. Send to backend
  await processBookmarkFromExtension({
    title: tab.title,
    url: tab.url,
    description: '', // User can add later
    category: 'other',
    tags: ''
  });
  
  // 3. Show success message
  alert('Page saved to Fuze!');
});
```

#### **Method 3: Bulk Import**

**Extension**:
```javascript
// User clicks "Sync All Bookmarks"
const allBookmarks = await getAllBookmarks();

// Send bulk to backend
await fetch(`${apiUrl}/api/bookmarks/import`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${authToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(allBookmarks) // Array of bookmarks
});
```

---

## 🔄 Content Processing Pipeline

When a bookmark arrives at the backend, it goes through a **5-step processing pipeline**:

### **Step 1: Save Bookmark**

**Backend** (`blueprints/bookmarks.py`):
```python
@bookmarks_bp.route('', methods=['POST'])
@jwt_required()
def save_bookmark():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # Extract data
    url = data.get('url')
    title = data.get('title', '')
    description = data.get('description', '')
    category = data.get('category', 'other')
    tags = data.get('tags', [])
    
    # Check for duplicates
    existing = SavedContent.query.filter_by(
        user_id=user_id, 
        url=url
    ).first()
    
    if existing:
        return {'message': 'Already saved'}, 200
    
    # Continue to Step 2...
```

### **Step 2: Content Extraction & Scraping**

```python
    # Extract content from URL
    scraped = extract_article_content(url)
    
    # scraped contains:
    {
        'content': "Full article text...",
        'title': "Scraped title",
        'headings': ["H1", "H2", "H3"],
        'meta_description': "Meta description",
        'quality_score': 8  # 0-10 quality rating
    }
    
    # Reject low-quality content
    if quality_score < 5:
        return {'message': 'Content quality too low'}, 400
```

**Scraping Function** (`blueprints/bookmarks.py`):
```python
def extract_article_content(url):
    """Scrape and extract content from URL"""
    from url_scraper import scrape_url
    
    return scrape_url(url)
    # Uses BeautifulSoup + Readability
    # Extracts: title, content, headings, meta
    # Calculates quality score
```

### **Step 3: Generate Embedding**

```python
    # Prepare text for embedding
    content_for_embedding = f"""
    {title} 
    {description} 
    {meta_description} 
    {' '.join(headings)} 
    {extracted_text}
    """
    
    # Generate 384-dimensional vector
    embedding = get_embedding(content_for_embedding)
    # Uses: sentence-transformers/all-MiniLM-L6-v2
    # Vector stored in PostgreSQL with pgvector
```

### **Step 4: Save to Database**

```python
    # Create SavedContent record
    new_bookmark = SavedContent(
        user_id=user_id,
        url=url.strip(),
        title=title.strip(),
        notes=description.strip(),
        extracted_text=extracted_text,
        embedding=embedding,  # 384-dim vector
        quality_score=quality_score,
        category=category,
        tags=','.join(tags),
        saved_at=datetime.now()
    )
    
    db.session.add(new_bookmark)
    db.session.commit()
    
    # Invalidate user's content cache
    cache_invalidator.after_content_save(new_bookmark.id, user_id)
```

**Database Schema**:
```sql
CREATE TABLE saved_content (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    url TEXT NOT NULL,
    title VARCHAR(200) NOT NULL,
    extracted_text TEXT,
    embedding vector(384),  -- pgvector
    quality_score INTEGER DEFAULT 10,
    category VARCHAR(100),
    tags TEXT,
    notes TEXT,
    saved_at TIMESTAMP DEFAULT NOW()
);
```

### **Step 5: Background Analysis (Async)**

**Trigger**: Background job runs periodically

**Service** (`background_analysis_service.py`):
```python
class BackgroundAnalysisService:
    def analyze_unprocessed_content(self):
        """Find and analyze content without ContentAnalysis"""
        
        # 1. Find unanalyzed content
        unanalyzed = SavedContent.query.outerjoin(
            ContentAnalysis
        ).filter(
            ContentAnalysis.id == None
        ).limit(50).all()
        
        # 2. Analyze each with Gemini
        for content in unanalyzed:
            analysis = self.gemini_analyzer.analyze_bookmark_content(
                title=content.title,
                description=content.notes,
                content=content.extracted_text,
                url=content.url
            )
            
            # 3. Save analysis
            content_analysis = ContentAnalysis(
                content_id=content.id,
                analysis_data=analysis,  # Full JSON
                key_concepts=', '.join(analysis['key_concepts']),
                content_type=analysis['content_type'],
                difficulty_level=analysis['difficulty'],
                technology_tags=', '.join(analysis['technologies']),
                relevance_score=analysis['relevance_score']
            )
            
            db.session.add(content_analysis)
            db.session.commit()
```

**Gemini Analysis** (`gemini_utils.py`):
```python
def analyze_bookmark_content(self, title, description, content, url):
    """Analyze content using Gemini AI"""
    
    prompt = f"""
    Analyze this technical bookmark content:
    
    Title: {title}
    Description: {description}
    Content: {content[:2000]}
    
    Provide JSON response with:
    {{
        "technologies": ["python", "flask", "react"],
        "content_type": "tutorial|documentation|article",
        "difficulty": "beginner|intermediate|advanced",
        "key_concepts": ["concept1", "concept2"],
        "relevance_score": 85,
        "summary": "Brief summary",
        "learning_objectives": ["objective1"],
        "target_audience": "intermediate",
        "prerequisites": ["prereq1"]
    }}
    """
    
    response = self._make_gemini_request(prompt)
    return json.loads(response)
```

**ContentAnalysis Table**:
```sql
CREATE TABLE content_analysis (
    id SERIAL PRIMARY KEY,
    content_id INTEGER REFERENCES saved_content(id),
    analysis_data JSONB,  -- Full Gemini response
    key_concepts TEXT,
    content_type VARCHAR(100),
    difficulty_level VARCHAR(50),
    technology_tags TEXT,
    relevance_score INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(content_id)
);
```

---

## 🎯 Recommendation Generation

### **Trigger Point**: User Opens Project

**Frontend** (`frontend/src/pages/Projects.jsx`):
```javascript
// User clicks on a project
const handleViewProject = (project) => {
  navigate(`/app/projects/${project.id}`);
  
  // Project page loads and fetches recommendations
};
```

**Project Page** (`frontend/src/pages/ProjectDetail.jsx`):
```javascript
useEffect(() => {
  // Fetch recommendations for this project
  const fetchRecommendations = async () => {
    const response = await fetch(`/api/recommendations/unified-orchestrator`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: user.id,
        title: project.title,
        description: project.description,
        technologies: project.technologies,
        project_id: project.id,
        max_recommendations: 10
      })
    });
    
    const data = await response.json();
    setRecommendations(data.recommendations);
  };
  
  fetchRecommendations();
}, [project.id]);
```

### **Backend: Recommendation Generation**

**Endpoint** (`blueprints/recommendations.py`):
```python
@recommendations_bp.route('/unified-orchestrator', methods=['POST'])
@jwt_required()
def get_unified_recommendations():
    data = request.get_json()
    
    # Create recommendation request
    request_obj = UnifiedRecommendationRequest(
        user_id=data['user_id'],
        title=data['title'],
        description=data['description'],
        technologies=data['technologies'],
        project_id=data.get('project_id'),
        max_recommendations=data.get('max_recommendations', 10)
    )
    
    # Get recommendations from orchestrator
    orchestrator = get_unified_orchestrator()
    result = orchestrator.get_recommendations(request_obj)
    
    return jsonify({
        'recommendations': [asdict(rec) for rec in result.recommendations],
        'engine_used': result.engine_used,
        'performance_metrics': result.performance_metrics
    })
```

### **Orchestrator Flow** (`unified_recommendation_orchestrator.py`):

```python
class UnifiedRecommendationOrchestrator:
    def get_recommendations(self, request):
        """
        Main recommendation generation flow
        """
        
        # === STEP 1: Check Cache ===
        cache_key = self._generate_cache_key(request)
        cached = redis_cache.get(cache_key)
        if cached:
            return cached  # Return instantly (<100ms)
        
        # === STEP 2: Intent Analysis ===
        intent = analyze_user_intent(
            user_input=f"{request.title} {request.description}",
            project_id=request.project_id
        )
        # Gemini analyzes: primary_goal, learning_stage, project_type,
        # urgency_level, complexity_preference, focus_areas
        
        # === STEP 3: Get User's Content ===
        content_list = self.data_layer.get_content(request.user_id)
        # Fetches all user's SavedContent + ContentAnalysis
        # JOIN saved_content WITH content_analysis
        
        # === STEP 4: Choose Engine ===
        if request.engine_preference == 'fast':
            engine = self.fast_engine
        elif len(content_list) > 50:
            engine = self.context_engine  # Better for large datasets
        else:
            engine = self.context_engine  # Default
        
        # === STEP 5: Generate Recommendations ===
        recommendations = engine.get_recommendations(content_list, request)
        
        # === STEP 6: ML Enhancement ===
        enhanced_recs = self._apply_ml_enhancement(
            recommendations,
            request,
            intent
        )
        # Uses TF-IDF to boost relevance scores
        
        # === STEP 7: Gemini Explanations ===
        for rec in enhanced_recs:
            rec.reason = self._generate_gemini_explanation(
                recommendation=rec,
                context=intent,
                user_query=request
            )
        # AI-powered natural language explanations
        
        # === STEP 8: Sort & Filter ===
        final_recs = self._sort_and_filter(
            enhanced_recs,
            min_score=25,
            max_count=request.max_recommendations
        )
        
        # === STEP 9: Cache Result ===
        redis_cache.set(cache_key, final_recs, ttl=300)  # 5 min
        
        # === STEP 10: Return ===
        return UnifiedRecommendationResult(
            recommendations=final_recs,
            engine_used="ContextAwareEngine+ML+Gemini",
            total_count=len(final_recs),
            performance_metrics={...}
        )
```

### **Context-Aware Engine** (Most Advanced):

```python
class ContextAwareEngine:
    def get_recommendations(self, content_list, request):
        """
        Generate intelligent recommendations
        """
        
        # 1. Extract context from request + intent
        context = {
            'technologies': request.technologies.split(','),
            'content_type': intent.preferred_content_type,
            'difficulty': intent.learning_stage,
            'intent_goal': intent.primary_goal,
            'project_type': intent.project_type
        }
        
        # 2. BATCH calculate semantic similarities (10x faster!)
        request_text = f"{context['title']} {context['description']} {' '.join(context['technologies'])}"
        content_texts = [f"{c['title']} {c['extracted_text']}" for c in content_list]
        
        batch_similarities = self.data_layer.calculate_batch_similarity(
            request_text,
            content_texts
        )
        # Uses sentence-transformers to calculate cosine similarity
        
        # 3. Calculate comprehensive scores
        recommendations = []
        for idx, content in enumerate(content_list):
            # Score components:
            score_components = {
                'semantic': batch_similarities[idx],      # 25%
                'technology': self._calc_tech_match(content, context),  # 35%
                'content_type': self._calc_type_match(content, context),  # 15%
                'difficulty': self._calc_difficulty_match(content, context),  # 10%
                'quality': content['quality_score'] / 10.0,  # 5%
                'intent_alignment': self._calc_intent_match(content, context)  # 10%
            }
            
            # Weighted final score
            final_score = (
                score_components['technology'] * 0.35 +
                score_components['semantic'] * 0.25 +
                score_components['content_type'] * 0.15 +
                score_components['difficulty'] * 0.10 +
                score_components['quality'] * 0.05 +
                score_components['intent_alignment'] * 0.10
            )
            
            # Apply user content boost (all content is user's own)
            final_score += 0.1
            
            # Apply relevance score boost from ContentAnalysis
            if content.get('relevance_score', 0) > 0:
                final_score += (content['relevance_score'] * 0.15)
            
            # Create recommendation
            rec = UnifiedRecommendationResult(
                id=content['id'],
                title=content['title'],
                url=content['url'],
                score=final_score * 100,  # 0-100 scale
                reason="",  # Filled by Gemini later
                content_type=content['content_type'],
                difficulty=content['difficulty'],
                technologies=content['technologies'],
                key_concepts=content['key_concepts'],
                quality_score=content['quality_score'],
                confidence=score_components['semantic'],
                metadata={
                    'score_components': score_components,
                    'context_used': context
                }
            )
            
            recommendations.append(rec)
        
        # 4. Sort by score
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        # 5. Filter low-quality
        filtered = [r for r in recommendations if r.score >= 25]
        
        return filtered[:request.max_recommendations]
```

### **ML Enhancement** (TF-IDF Boost):

```python
def _apply_ml_enhancement(self, recommendations, request, intent):
    """
    Apply ML-based score boosting using TF-IDF
    """
    from simple_ml_enhancer import enhance_unified_recommendations
    
    enhanced = enhance_unified_recommendations(
        recommendations=recommendations,
        user_query=f"{request.title} {request.description}",
        user_context={
            'intent_goal': intent.primary_goal,
            'technologies': request.technologies,
            'difficulty': intent.learning_stage
        }
    )
    
    return enhanced
```

### **Gemini Explanations**:

```python
def _generate_gemini_explanation(self, recommendation, context, user_query):
    """
    Generate AI-powered natural language explanation
    """
    from explainability_engine import RecommendationExplainer
    
    explainer = RecommendationExplainer()
    
    explanation = explainer.explain_recommendation(
        recommendation=recommendation,
        query_context=context,
        score_components=recommendation.metadata['score_components']
    )
    
    # Returns natural language like:
    # "This comprehensive Java tutorial perfectly aligns with your DSA 
    #  visualizer project, covering byte code manipulation with Byte Buddy 
    #  and JVM instrumentation—exactly what you need for runtime code 
    #  analysis. The intermediate difficulty matches your skill level."
    
    return explanation['why_recommended']
```

---

## 🔄 Complete User Journey

### **Day 1: New User**

```
1. User signs up → User(id=1) created in database

2. Installs Chrome extension → Configures API URL + Login

3. Extension syncs 50 bookmarks → 50 SavedContent records created
   → Each gets embedding generated
   → Queued for background analysis

4. Background service runs → Gemini analyzes all 50 bookmarks
   → ContentAnalysis records created with:
     - Technologies extracted
     - Content type identified
     - Difficulty assessed
     - Key concepts found
```

### **Day 2: Creating First Project**

```
5. User creates project "Build a REST API"
   → Project created in database
   → Intent analysis runs automatically via Gemini
   → Intent saved: {
       primary_goal: "build",
       project_type: "backend",
       learning_stage: "intermediate",
       specific_technologies: ["python", "flask", "rest"],
       complexity_preference: "moderate"
     }

6. User clicks project → Frontend requests recommendations
   → Backend orchestrator:
     a) Checks cache (miss - first time)
     b) Loads intent analysis (from Step 5)
     c) Fetches all 50 user bookmarks + their analysis
     d) Calculates semantic similarity (batch, fast!)
     e) Scores each bookmark based on:
        - Tech match (Flask, Python, REST)
        - Content type (tutorials preferred for "build")
        - Difficulty (intermediate)
        - Semantic relevance
        - Intent alignment
     f) Applies ML enhancement (TF-IDF boost)
     g) Generates Gemini explanations for top 10
     h) Caches result for 5 minutes
     i) Returns recommendations

7. User sees 10 personalized recommendations with:
   - Smart sorting (most relevant first)
   - Natural language explanations
   - Score breakdown
   - Quality indicators

8. User clicks recommendation → Tracked as feedback
   → UserFeedback record created
   → System learns user preferences
```

### **Day 3: Improved Recommendations**

```
9. User saves 20 more bookmarks → Now has 70 total
   → All analyzed by Gemini
   → More diverse content = better recommendations

10. Opens same project again
    → Recommendation request
    → Cache hit (if < 5 min) = instant response
    → OR fresh generation with:
      - More content to choose from (70 vs 50)
      - User feedback incorporated
      - Improved intent understanding
```

---

## 🏗️ Technical Architecture

### **System Components**

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  React + Vite + TailwindCSS                                 │
│  - Authentication (JWT)                                      │
│  - Project Management                                        │
│  - Recommendation Display                                    │
│  - User Feedback Tracking                                    │
└──────────────┬──────────────────────────────────────────────┘
               │ REST API (HTTPS)
               │ Authorization: Bearer <JWT>
┌──────────────┴──────────────────────────────────────────────┐
│                      Flask Backend                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Blueprints (API Routes)                              │  │
│  │ - auth.py: Registration, Login, JWT                  │  │
│  │ - bookmarks.py: Save, Import, Scrape                 │  │
│  │ - projects.py: CRUD, Intent Analysis                 │  │
│  │ - recommendations.py: Unified Orchestrator           │  │
│  │ - enhanced_recommendations.py: Feedback, Insights    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Core Engines                                          │  │
│  │ - unified_recommendation_orchestrator.py             │  │
│  │   ├─ UnifiedDataLayer (DB + Embeddings)              │  │
│  │   ├─ FastSemanticEngine (Quick matches)              │  │
│  │   └─ ContextAwareEngine (Advanced scoring)           │  │
│  │                                                        │  │
│  │ - intent_analysis_engine.py (Gemini Intent)          │  │
│  │ - explainability_engine.py (Gemini Explanations)     │  │
│  │ - simple_ml_enhancer.py (TF-IDF Boost)               │  │
│  │ - user_feedback_system.py (Learning Loop)            │  │
│  │ - skill_gap_analyzer.py (Learning Paths)             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ External Services                                     │  │
│  │ - gemini_utils.py (Gemini AI Client)                 │  │
│  │ - embedding_utils.py (Sentence Transformers)         │  │
│  │ - url_scraper.py (Content Extraction)                │  │
│  │ - redis_utils.py (Caching)                            │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────┬───────────────────┬─────────────┬───────────┘
               │                   │             │
               │                   │             │
┌──────────────┴──────┐  ┌────────┴─────┐  ┌───┴──────────┐
│   PostgreSQL DB      │  │    Redis     │  │  Gemini AI   │
│  + pgvector          │  │    Cache     │  │  (Google)    │
│                      │  │              │  │              │
│  Tables:             │  │  Keys:       │  │  Models:     │
│  - users             │  │  - recs:*    │  │  - 2.0-flash │
│  - saved_content     │  │  - intent:*  │  │              │
│  - content_analysis  │  │  - bookmarks │  │  Features:   │
│  - projects          │  │              │  │  - Analysis  │
│  - user_feedback     │  │              │  │  - Intent    │
│  - tasks             │  │              │  │  - Explain   │
└─────────────────────┘  └──────────────┘  └──────────────┘
```

### **Data Flow**

```
1. BOOKMARK SAVE
   Extension → Flask → Scraper → DB (SavedContent)
                                ↓
                           Background Service
                                ↓
                           Gemini Analysis
                                ↓
                           DB (ContentAnalysis)

2. RECOMMENDATION REQUEST
   Frontend → Flask → Orchestrator → Cache? (Redis)
                           ↓           ↓
                          NO          YES → Return cached
                           ↓
                    Intent Analysis (Gemini)
                           ↓
                    Get User Content (DB)
                           ↓
                    Context-Aware Engine
                           ↓
                    ML Enhancement (TF-IDF)
                           ↓
                    Gemini Explanations
                           ↓
                    Cache → Return to Frontend

3. USER FEEDBACK
   Frontend → Flask → DB (UserFeedback)
                           ↓
                    Update User Preferences
                           ↓
                    Improve Future Recommendations
```

### **Database Schema**

```sql
-- Users
users (id, username, email, password_hash, created_at)

-- User Content
saved_content (
    id, user_id, url, title, 
    extracted_text, 
    embedding vector(384),  -- Semantic search
    quality_score, category, tags, notes,
    saved_at
)

-- AI Analysis
content_analysis (
    id, content_id,
    analysis_data JSONB,     -- Full Gemini response
    key_concepts TEXT,
    content_type VARCHAR,    -- tutorial, doc, article
    difficulty_level VARCHAR, -- beginner, intermediate, advanced
    technology_tags TEXT,
    relevance_score INTEGER,
    created_at, updated_at,
    UNIQUE(content_id)
)

-- Projects
projects (
    id, user_id, title, description, technologies,
    intent_analysis JSONB,   -- Cached intent analysis
    intent_analysis_updated,
    created_at
)

-- Learning Feedback
user_feedback (
    id, user_id, content_id, recommendation_id,
    feedback_type,  -- clicked, saved, dismissed, completed
    context_data JSONB,
    timestamp
)

-- Tasks
tasks (
    id, project_id, title, description,
    embedding vector(384),
    created_at
)
```

### **Caching Strategy**

```python
# Redis Keys
"unified_recommendations:{hash}"  # Recommendation results (5 min TTL)
"unified_recommendations_intent:{project_id}"  # Intent analysis (1 hour)
"user_bookmarks:{user_id}"  # User's content list (10 min)
"content_analysis:{content_id}"  # Analysis results (1 day)
"user_preferences:{user_id}"  # Learned preferences (1 week)
```

### **API Endpoints Summary**

```
Authentication:
POST   /api/auth/register         - Create account
POST   /api/auth/login            - Get JWT token
POST   /api/auth/refresh          - Refresh token

Content Management:
POST   /api/bookmarks             - Save single bookmark
POST   /api/bookmarks/import      - Bulk import
GET    /api/bookmarks             - Get user's bookmarks
DELETE /api/bookmarks/:id         - Delete bookmark

Projects:
GET    /api/projects              - List projects
POST   /api/projects              - Create project (+ auto intent analysis)
GET    /api/projects/:id          - Get project details
PUT    /api/projects/:id          - Update project
DELETE /api/projects/:id          - Delete project

Recommendations:
POST   /api/recommendations/unified-orchestrator  - Get recommendations
GET    /api/recommendations/status                - System status

Enhanced Features:
POST   /api/enhanced/feedback                     - Track user interaction
GET    /api/enhanced/user-insights                - Get learning patterns
POST   /api/enhanced/skill-gaps                   - Analyze skill gaps
POST   /api/enhanced/explain-recommendation/:id   - Get detailed explanation
POST   /api/enhanced/personalized-recommendations - AI-personalized recs
```

---

## 🎯 Key Features

### **1. Intelligent Content Analysis**
- ✅ Automatic extraction from URLs
- ✅ Gemini AI analysis (technologies, concepts, difficulty)
- ✅ Quality scoring
- ✅ Semantic embeddings for search

### **2. Intent-Aware Recommendations**
- ✅ Understands user goals (learn, build, troubleshoot)
- ✅ Adapts to learning stage (beginner to advanced)
- ✅ Project-type specific recommendations
- ✅ Time-sensitive urgency handling

### **3. Multi-Layer Scoring**
- ✅ Semantic similarity (NLP)
- ✅ Technology matching
- ✅ Content type alignment
- ✅ Difficulty matching
- ✅ Quality indicators
- ✅ Intent alignment
- ✅ ML enhancement (TF-IDF)

### **4. AI-Powered Explanations**
- ✅ Gemini-generated natural language
- ✅ Context-aware reasoning
- ✅ Personalized insights
- ✅ Graceful fallback to templates

### **5. Learning Loop**
- ✅ Tracks user interactions
- ✅ Learns preferences
- ✅ Improves over time
- ✅ Skill gap analysis

### **6. Performance Optimizations**
- ✅ Redis caching (instant cached responses)
- ✅ Batch embedding generation (10x faster)
- ✅ Smart cache invalidation
- ✅ Connection pooling
- ✅ Background processing

---

## 📊 Performance Metrics

| Operation | First Time | Cached | Notes |
|-----------|-----------|--------|-------|
| User Registration | 200-500ms | N/A | Includes password hashing |
| Login | 150-300ms | N/A | JWT generation |
| Save Bookmark | 2-5s | N/A | Includes scraping + embedding |
| Bulk Import (50 items) | 60-120s | N/A | Parallel processing |
| Content Analysis | 3-5s per item | N/A | Gemini API call |
| Intent Analysis | 2-4s | <50ms | Cached per project |
| Recommendations | 3-5s | <100ms | Includes Gemini explanations |
| User Feedback | 50-100ms | N/A | Simple DB insert |

---

## 🚀 Quick Start for Developers

### **1. Setup Backend**
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Run server
python run_production.py
```

### **2. Setup Frontend**
```bash
cd frontend
npm install
npm run dev
```

### **3. Install Extension**
```
1. Open Chrome → chrome://extensions
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select BookmarkExtension/ folder
5. Configure API URL in extension popup
```

### **4. Test Flow**
```
1. Register account
2. Login to extension
3. Save a few bookmarks
4. Create a project
5. View recommendations!
```

---

## 🎉 Summary

**FUZE** provides an end-to-end AI-powered learning platform:

1. **Collects** user's bookmarks automatically
2. **Analyzes** content with Gemini AI
3. **Understands** user's intent and goals
4. **Recommends** most relevant learning materials
5. **Explains** why each recommendation matters
6. **Learns** from user interactions
7. **Improves** over time

**All powered by cutting-edge AI, NLP, and ML techniques, with production-ready performance and scalability!** 🚀


