# User Flow Documentation

Complete user journey and system flows for Fuze - Intelligent Bookmark Manager.

## Table of Contents

1. [Complete User Onboarding Flow](#complete-user-onboarding-flow)
2. [Bookmark Saving Flow](#bookmark-saving-flow)
3. [Chrome Extension Import Flow](#chrome-extension-import-flow)
4. [Content Analysis Flow](#content-analysis-flow)
5. [Recommendation Generation Flow](#recommendation-generation-flow)
6. [Project-Based Recommendations Flow](#project-based-recommendations-flow)
7. [Search Flow](#search-flow)
8. [Extension Authentication Flow](#extension-authentication-flow)

---

## Complete User Onboarding Flow

This diagram shows the complete journey from landing page to fully set up account.

```mermaid
flowchart TD
    Start([User visits Landing Page]) --> Landing{User Authenticated?}
    Landing -->|No| ViewLanding[View Landing Page Features]
    Landing -->|Yes| Dashboard[Redirect to Dashboard]
    
    ViewLanding --> ClickSignup[Click 'Start for Free']
    ClickSignup --> LoginPage[Login Page - Signup Mode]
    
    LoginPage --> FillForm[Fill Registration Form]
    FillForm --> ValidateForm{Form Valid?}
    ValidateForm -->|No| ShowErrors[Show Validation Errors]
    ShowErrors --> FillForm
    
    ValidateForm -->|Yes| CheckUsername[Check Username Availability]
    CheckUsername --> UsernameAvailable{Available?}
    UsernameAvailable -->|No| ShowSuggestions[Show Username Suggestions]
    ShowSuggestions --> FillForm
    
    UsernameAvailable -->|Yes| SubmitRegistration[POST /api/auth/register]
    SubmitRegistration --> CreateUser[Create User Account]
    CreateUser --> GenerateToken[Generate JWT Token]
    GenerateToken --> SetOnboarding[Set show_onboarding = true]
    SetOnboarding --> RedirectDashboard[Redirect to Dashboard]
    
    RedirectDashboard --> CheckOnboarding{Onboarding Modal?}
    CheckOnboarding -->|Yes| OnboardingStep1[Step 1: API Key Setup]
    CheckOnboarding -->|No| DashboardView[View Dashboard]
    
    OnboardingStep1 --> HasAPIKey{Has API Key?}
    HasAPIKey -->|No| ShowAPIKeyInstructions[Show Gemini API Key Instructions]
    ShowAPIKeyInstructions --> UserAddsKey[User adds API key in Profile]
    UserAddsKey --> SaveAPIKey[Save API Key to Database]
    SaveAPIKey --> OnboardingStep2
    
    HasAPIKey -->|Yes| OnboardingStep2[Step 2: Install Extension]
    OnboardingStep2 --> ShowExtensionInstructions[Show Extension Installation Guide]
    ShowExtensionInstructions --> UserInstallsExtension[User installs Chrome Extension]
    UserInstallsExtension --> ExtensionLogin[Extension: Login with Credentials]
    ExtensionLogin --> SyncToken[Sync Auth Token to Extension]
    SyncToken --> OnboardingStep3
    
    OnboardingStep3[Step 3: Import Bookmarks] --> ShowImportInstructions[Show Import Instructions]
    ShowImportInstructions --> UserClicksImport[User clicks 'Import All Bookmarks']
    UserClicksImport --> ImportFlow[Start Import Flow]
    ImportFlow --> OnboardingComplete[Mark Onboarding Complete]
    
    OnboardingComplete --> DashboardView
    DashboardView --> End([User Ready to Use Fuze])
    
    style Start fill:#4a90e2
    style End fill:#50c878
    style OnboardingStep1 fill:#cd853f
    style OnboardingStep2 fill:#cd853f
    style OnboardingStep3 fill:#cd853f
```

---

## Bookmark Saving Flow

This shows how bookmarks are saved from the extension or web interface.

```mermaid
sequenceDiagram
    participant User
    participant Extension as Chrome Extension
    participant Frontend as Web Frontend
    participant Backend as Flask Backend
    participant Scraper as Content Scraper
    participant DB as Database
    participant Analysis as Background Analysis
    participant Redis as Redis Cache
    
    User->>Extension: Click 'Save to Fuze' button
    Extension->>Extension: Get current tab URL & title
    Extension->>Extension: Get auth token from storage
    Extension->>Backend: POST /api/bookmarks<br/>{url, title, description, category, tags}
    
    Backend->>Backend: Validate JWT token
    Backend->>Backend: Sanitize inputs
    Backend->>DB: Check for duplicate URL (normalized)
    
    alt Duplicate Found
        DB-->>Backend: Existing bookmark
        Backend->>DB: Update existing bookmark
        Backend->>Redis: Invalidate cache
        Backend-->>Extension: 200 OK (updated)
    else New Bookmark
        Backend->>Scraper: Extract content from URL
        Scraper->>Scraper: Scrape webpage content
        Scraper->>Scraper: Extract text, headings, meta
        Scraper->>Scraper: Calculate quality score
        Scraper-->>Backend: {content, title, headings, quality_score}
        
        Backend->>Backend: Generate embedding<br/>(title + content)
        Backend->>DB: Save bookmark with embedding
        DB-->>Backend: Bookmark ID
        
        Backend->>Redis: Invalidate user bookmarks cache
        Backend->>Analysis: Trigger background analysis (async)
        Backend-->>Extension: 201 Created {bookmark_id}
        
        Note over Analysis: Background Process
        Analysis->>Analysis: Get user's API key
        Analysis->>Analysis: Analyze with Gemini AI
        Analysis->>DB: Save ContentAnalysis record
        Analysis->>Redis: Cache analysis results
    end
    
    Extension->>Extension: Show success notification
    Extension-->>User: Bookmark saved successfully
```

---

## Chrome Extension Import Flow

Complete flow for importing all Chrome bookmarks.

```mermaid
flowchart TD
    Start([User clicks 'Import All Bookmarks']) --> CheckAuth{Authenticated?}
    CheckAuth -->|No| ShowLogin[Show Login Prompt]
    ShowLogin --> End1([End])
    
    CheckAuth -->|Yes| GetBookmarks[Extension: getAllBookmarks API]
    GetBookmarks --> FilterBookmarks[Filter & Prepare Bookmarks]
    FilterBookmarks --> CheckServer[Test Server Connection]
    
    CheckServer --> ServerOK{Server OK?}
    ServerOK -->|No| ShowError[Show Connection Error]
    ShowError --> End2([End])
    
    ServerOK -->|Yes| CheckProgress[Check Existing Import Progress]
    CheckProgress --> HasProgress{Import in Progress?}
    HasProgress -->|Yes| ShowProgress[Show Progress Modal]
    ShowProgress --> MonitorProgress[Monitor via SSE Stream]
    MonitorProgress --> WaitComplete{Complete?}
    WaitComplete -->|No| MonitorProgress
    WaitComplete -->|Yes| ShowResults[Show Import Results]
    
    HasProgress -->|No| StartImport[POST /api/bookmarks/import<br/>Array of bookmarks]
    StartImport --> InitProgress[Initialize Progress in Redis]
    InitProgress --> StartSSE[Start SSE Stream for Progress]
    
    StartSSE --> ProcessBatch[Backend: Process Bookmarks in Parallel]
    ProcessBatch --> ForEachBookmark{For Each Bookmark}
    
    ForEachBookmark --> CheckDuplicate[Check if Duplicate]
    CheckDuplicate --> IsDuplicate{Duplicate?}
    IsDuplicate -->|Yes| SkipBookmark[Skip - Increment skipped_count]
    IsDuplicate -->|No| ScrapeContent[Scrape & Extract Content]
    
    ScrapeContent --> QualityCheck{Quality Score >= 5?}
    QualityCheck -->|No| SkipBookmark
    QualityCheck -->|Yes| GenerateEmbedding[Generate Embedding]
    GenerateEmbedding --> AddToBatch[Add to Batch]
    
    SkipBookmark --> UpdateProgress[Update Progress in Redis]
    AddToBatch --> UpdateProgress
    
    UpdateProgress --> MoreBookmarks{More Bookmarks?}
    MoreBookmarks -->|Yes| ForEachBookmark
    MoreBookmarks -->|No| SaveBatch[Save Batch to Database]
    
    SaveBatch --> TriggerAnalysis[Trigger Background Analysis]
    TriggerAnalysis --> MarkComplete[Mark Import Complete]
    MarkComplete --> SendSSE[Send Final Progress via SSE]
    SendSSE --> ShowResults
    
    ShowResults --> DisplayStats[Display Statistics:<br/>- Total<br/>- Added<br/>- Skipped<br/>- Errors]
    DisplayStats --> End3([Import Complete])
    
    style Start fill:#4a90e2
    style End1 fill:#ff6b6b
    style End2 fill:#ff6b6b
    style End3 fill:#50c878
    style ProcessBatch fill:#cd853f
    style ShowResults fill:#50c878
```

---

## Content Analysis Flow

Background analysis of saved bookmarks using Gemini AI.

```mermaid
sequenceDiagram
    participant Bookmark as Bookmark Saved
    participant Backend as Flask Backend
    participant Thread as Background Thread
    participant AnalysisService as Analysis Service
    participant Gemini as Gemini AI
    participant DB as Database
    participant Redis as Redis Cache
    participant User as User Dashboard
    
    Bookmark->>Backend: Bookmark saved with ID
    Backend->>Thread: Trigger async analysis thread
    Note over Thread: Non-blocking background process
    
    Thread->>AnalysisService: analyze_content(bookmark_id, user_id)
    AnalysisService->>DB: Get bookmark & user data
    DB-->>AnalysisService: Bookmark + User API Key
    
    AnalysisService->>AnalysisService: Check if already analyzed
    alt Already Analyzed
        AnalysisService-->>Thread: Skip (already done)
    else Needs Analysis
        AnalysisService->>Gemini: Analyze content with user's API key
        Note over Gemini: Uses user's own Gemini API key<br/>for quota isolation
        
        Gemini->>Gemini: Extract:<br/>- Technologies<br/>- Key Concepts<br/>- Difficulty Level<br/>- Content Type<br/>- Learning Insights
        Gemini-->>AnalysisService: Analysis results
        
        AnalysisService->>DB: Save ContentAnalysis record
        AnalysisService->>Redis: Cache analysis (24h TTL)
        AnalysisService->>Redis: Invalidate recommendation cache
        
        Note over User: User can see analysis status<br/>on Dashboard
        AnalysisService->>User: Update analysis progress
    end
    
    Note over Thread: Runs continuously every 30s<br/>for unanalyzed content
    Thread->>Thread: Check for more unanalyzed content
    Thread->>AnalysisService: Process next batch
```

---

## Recommendation Generation Flow

Complete flow for generating AI-powered recommendations.

```mermaid
flowchart TD
    Start([User requests recommendations]) --> SelectContext[Select Context:<br/>- General Learning<br/>- Project<br/>- Task<br/>- Subtask]
    
    SelectContext --> BuildRequest[Build Recommendation Request]
    BuildRequest --> CheckCache{Check Redis Cache}
    
    CheckCache -->|Hit| ReturnCached[Return Cached Results]
    ReturnCached --> End1([Display Recommendations])
    
    CheckCache -->|Miss| POSTRequest[POST /api/recommendations/unified-orchestrator]
    POSTRequest --> ValidateAuth{Validate JWT}
    ValidateAuth -->|Invalid| Error1[Return 401 Unauthorized]
    
    ValidateAuth -->|Valid| GetOrchestrator[Get Unified Orchestrator Instance]
    GetOrchestrator --> AnalyzeIntent[Analyze User Intent]
    
    AnalyzeIntent --> IntentEngine{Intent Analysis Engine}
    IntentEngine -->|Success| GetIntent[Get Intent:<br/>- Goal: learn/build/explore<br/>- Technologies<br/>- Difficulty]
    IntentEngine -->|Failed| FallbackIntent[Use Fallback Intent]
    
    GetIntent --> EnhanceRequest[Enhance Request with Intent]
    FallbackIntent --> EnhanceRequest
    
    EnhanceRequest --> GetCandidates[Get Candidate Content from DB]
    GetCandidates --> FilterCandidates[Filter by:<br/>- Quality Score >= 7<br/>- Has embeddings<br/>- User's content + Global]
    
    FilterCandidates --> SelectEngine[Select Engine Strategy]
    SelectEngine --> EngineChoice{Engine Selection}
    
    EngineChoice -->|Fast Path| FastSemantic[Fast Semantic Engine]
    EngineChoice -->|Context Path| ContextAware[Context-Aware Engine]
    EngineChoice -->|ML Path| MLEngine[ML-Enhanced Engine]
    
    FastSemantic --> CalculateScores[Calculate Similarity Scores]
    ContextAware --> CalculateScores
    MLEngine --> CalculateScores
    
    CalculateScores --> ApplyFilters[Apply Filters:<br/>- Quality threshold<br/>- Relevance threshold<br/>- Confidence threshold]
    
    ApplyFilters --> DiversityFilter{Diversity Enabled?}
    DiversityFilter -->|Yes| ApplyDiversity[Apply Diversity Filtering]
    DiversityFilter -->|No| SortResults
    
    ApplyDiversity --> SortResults[Sort by Combined Score]
    SortResults --> LimitResults[Limit to max_recommendations]
    
    LimitResults --> GenerateSummaries[Generate Context Summaries]
    GenerateSummaries --> GeminiSummaries[Use Gemini for summaries<br/>if available]
    GeminiSummaries --> FormatResults[Format Results]
    
    FormatResults --> CacheResults[Cache Results in Redis]
    CacheResults --> ReturnResults[Return Recommendations]
    ReturnResults --> End2([Display Recommendations])
    
    Error1 --> End3([Show Error])
    
    style Start fill:#4a90e2
    style End1 fill:#50c878
    style End2 fill:#50c878
    style End3 fill:#ff6b6b
    style AnalyzeIntent fill:#cd853f
    style SelectEngine fill:#cd853f
    style GenerateSummaries fill:#cd853f
```

---

## Project-Based Recommendations Flow

Recommendations specific to a project context.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Orchestrator as Unified Orchestrator
    participant ProjectEmbedding as Project Embedding Manager
    participant DB as Database
    participant Redis as Redis Cache
    
    User->>Frontend: Create/Select Project
    Frontend->>Backend: POST /api/projects
    Backend->>DB: Save Project
    Backend->>ProjectEmbedding: Generate Project Embedding
    ProjectEmbedding->>ProjectEmbedding: Combine:<br/>- Title embedding<br/>- Description embedding<br/>- Technologies embedding
    ProjectEmbedding->>DB: Save project_embedding
    DB-->>Backend: Project created
    
    User->>Frontend: Request Project Recommendations
    Frontend->>Backend: POST /api/recommendations/unified-orchestrator<br/>{project_id, title, description, technologies}
    
    Backend->>Orchestrator: get_recommendations(request)
    Orchestrator->>DB: Get project with embedding
    Orchestrator->>DB: Get candidate content
    
    Orchestrator->>Orchestrator: Layer 1: Technology Overlap
    Orchestrator->>Orchestrator: Layer 2: Semantic Similarity<br/>(project embedding vs content embedding)
    Orchestrator->>Orchestrator: Layer 3: Content Analysis Score
    
    Orchestrator->>Orchestrator: Combine Scores:<br/>tech_score * 0.4 +<br/>semantic_score * 0.4 +<br/>analysis_score * 0.2
    
    Orchestrator->>Orchestrator: Filter by min_score threshold
    Orchestrator->>Orchestrator: Sort by final_score DESC
    Orchestrator->>Orchestrator: Generate reasoning for each
    
    Orchestrator-->>Backend: List of recommendations
    Backend->>Redis: Cache results
    Backend-->>Frontend: Recommendations with scores
    Frontend-->>User: Display project-specific recommendations
```

---

## Search Flow

Semantic and text-based search functionality.

```mermaid
flowchart TD
    Start([User enters search query]) --> SearchType{Search Type?}
    
    SearchType -->|Text Search| TextSearch[Text Search Flow]
    SearchType -->|Semantic Search| SemanticSearch[Semantic Search Flow]
    
    TextSearch --> QueryDB[Query Database:<br/>- Title LIKE<br/>- Notes LIKE<br/>- Extracted text LIKE]
    QueryDB --> TextResults[Return Text Matches]
    TextResults --> End1([Display Results])
    
    SemanticSearch --> GenerateQueryEmbedding[Generate Query Embedding]
    GenerateQueryEmbedding --> VectorSearch[Vector Similarity Search<br/>using pgvector]
    
    VectorSearch --> CalculateSimilarity[Calculate Cosine Similarity<br/>query_embedding vs content_embedding]
    CalculateSimilarity --> FilterByUser[Filter by User ID]
    FilterByUser --> SortBySimilarity[Sort by Similarity Score DESC]
    SortBySimilarity --> LimitResults[Limit Results]
    LimitResults --> SemanticResults[Return Semantic Matches]
    SemanticResults --> End2([Display Results])
    
    style Start fill:#4a90e2
    style End1 fill:#50c878
    style End2 fill:#50c878
    style GenerateQueryEmbedding fill:#cd853f
    style VectorSearch fill:#cd853f
```

---

## Extension Authentication Flow

How the Chrome extension authenticates and syncs with the web platform.

```mermaid
sequenceDiagram
    participant User
    participant WebApp as Web Application
    participant Extension as Chrome Extension
    participant Backend as Flask Backend
    participant Storage as Chrome Storage
    
    Note over User,WebApp: User logs in on web
    User->>WebApp: Login with credentials
    WebApp->>Backend: POST /api/auth/login
    Backend-->>WebApp: JWT Token + User Data
    WebApp->>WebApp: Store token in localStorage
    
    Note over WebApp,Extension: Token sync to extension
    WebApp->>Extension: Send message: syncAuthToken<br/>{token, apiUrl}
    Extension->>Storage: Store authToken & apiUrl
    
    Note over Extension,Backend: Extension uses token
    User->>Extension: Click extension icon
    Extension->>Storage: Get authToken
    Extension->>Backend: GET /api/auth/verify<br/>Header: Bearer {token}
    
    Backend->>Backend: Verify JWT token
    alt Token Valid
        Backend-->>Extension: 200 OK + User Info
        Extension->>Extension: Show authenticated UI
    else Token Invalid/Expired
        Backend-->>Extension: 401 Unauthorized
        Extension->>Extension: Show login prompt
        Extension->>User: Request login credentials
        User->>Extension: Enter credentials
        Extension->>Backend: POST /api/auth/login
        Backend-->>Extension: New JWT Token
        Extension->>Storage: Update authToken
    end
    
    Note over Extension: Extension can now make<br/>authenticated API calls
    Extension->>Backend: API calls with Bearer token
    Backend-->>Extension: Authenticated responses
```

---

## Complete System Architecture Flow

High-level view of how all components interact.

```mermaid
graph TB
    subgraph "User Interface Layer"
        WebApp[Web Application<br/>React + Vite]
        Extension[Chrome Extension<br/>Manifest V3]
    end
    
    subgraph "API Layer"
        AuthAPI[Auth Blueprint<br/>JWT Authentication]
        BookmarksAPI[Bookmarks Blueprint<br/>CRUD Operations]
        ProjectsAPI[Projects Blueprint<br/>Project Management]
        RecommendationsAPI[Recommendations Blueprint<br/>AI Recommendations]
        SearchAPI[Search Blueprint<br/>Semantic Search]
    end
    
    subgraph "Business Logic Layer"
        Orchestrator[Unified Recommendation<br/>Orchestrator]
        AnalysisService[Background Analysis<br/>Service]
        ScraperService[Content Scraper<br/>Service]
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL<br/>+ pgvector)]
        Redis[(Redis Cache)]
    end
    
    subgraph "External Services"
        Gemini[Google Gemini AI<br/>User's API Key]
        WebContent[Web Content<br/>Scraping]
    end
    
    WebApp --> AuthAPI
    WebApp --> BookmarksAPI
    WebApp --> ProjectsAPI
    WebApp --> RecommendationsAPI
    WebApp --> SearchAPI
    
    Extension --> AuthAPI
    Extension --> BookmarksAPI
    
    AuthAPI --> PostgreSQL
    BookmarksAPI --> ScraperService
    BookmarksAPI --> PostgreSQL
    BookmarksAPI --> AnalysisService
    
    ProjectsAPI --> PostgreSQL
    ProjectsAPI --> Orchestrator
    
    RecommendationsAPI --> Orchestrator
    RecommendationsAPI --> Redis
    
    SearchAPI --> PostgreSQL
    
    Orchestrator --> PostgreSQL
    Orchestrator --> Redis
    Orchestrator --> Gemini
    
    AnalysisService --> PostgreSQL
    AnalysisService --> Redis
    AnalysisService --> Gemini
    
    ScraperService --> WebContent
    ScraperService --> PostgreSQL
    
    style WebApp fill:#4a90e2
    style Extension fill:#4a90e2
    style Orchestrator fill:#cd853f
    style AnalysisService fill:#cd853f
    style PostgreSQL fill:#50c878
    style Redis fill:#ff6b6b
    style Gemini fill:#9b59b6
```

---

## Key User Journeys Summary

### Journey 1: New User Onboarding
1. Visit landing page → Sign up → Set API key → Install extension → Import bookmarks → Start using

### Journey 2: Saving a Bookmark
1. Browse web → Click extension → Save bookmark → Content extracted → Background analysis → Ready for recommendations

### Journey 3: Getting Recommendations
1. Go to Recommendations page → Select context → Request recommendations → View personalized results → Save useful ones

### Journey 4: Project-Based Learning
1. Create project → Add tasks → Get project recommendations → Save relevant content → Track progress

### Journey 5: Content Discovery
1. Use semantic search → Find related content → View recommendations → Discover new resources

---

## Notes

- **Background Processing**: Content analysis runs asynchronously to avoid blocking user requests
- **Caching Strategy**: Multiple layers of caching (Redis, query cache, recommendation cache) for performance
- **User Isolation**: Each user's API key is used for their own Gemini requests, ensuring quota isolation
- **Error Handling**: Graceful fallbacks at every step to ensure system reliability
- **Real-time Updates**: SSE streams for import progress, WebSocket-ready architecture

---

*Last Updated: 2024*

