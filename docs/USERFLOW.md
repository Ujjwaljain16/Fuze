# User Flow Documentation

User journeys and system flows for Fuze.

## Table of Contents

1. [Complete User Onboarding Flow](#complete-user-onboarding-flow)
2. [API Key Setup Flow](#api-key-setup-flow)
3. [Bookmark Saving Flow](#bookmark-saving-flow)
4. [Chrome Extension Import Flow](#chrome-extension-import-flow)
5. [Content Analysis Flow](#content-analysis-flow)
6. [Recommendation Generation Flow](#recommendation-generation-flow)
7. [Project-Based Recommendations Flow](#project-based-recommendations-flow)
8. [Search Flow](#search-flow)
9. [LinkedIn Integration Flow](#linkedin-integration-flow)
10. [Extension Authentication Flow](#extension-authentication-flow)
11. [Task Management Flow](#task-management-flow)

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

## API Key Setup Flow

This shows how users set up their Gemini API key for AI-powered features.

```mermaid
flowchart TD
    Start([User needs AI features]) --> CheckAPIKey{API Key Set?}

    CheckAPIKey -->|No| VisitProfile[Visit Profile Settings]
    VisitProfile --> ClickAddKey[Click 'Add API Key']
    ClickAddKey --> ShowInstructions[Show Gemini API Setup Instructions]
    ShowInstructions --> UserGetsKey[User gets API key from Google AI Studio]
    UserGetsKey --> EnterKey[User enters API key in form]
    EnterKey --> ValidateKey{Valid Format?}

    ValidateKey -->|No| ShowError[Show format error]
    ShowError --> EnterKey

    ValidateKey -->|Yes| SubmitKey[POST /api/user/api-key]
    SubmitKey --> TestKey[Test key with Gemini API]
    TestKey --> TestSuccess{Success?}

    TestSuccess -->|No| ShowTestError[Show test error message]
    ShowTestError --> EnterKey

    TestSuccess -->|Yes| SaveKey[Save encrypted key to database]
    SaveKey --> MarkOnboarding[Mark API key onboarding complete]
    MarkOnboarding --> EnableFeatures[Enable AI features in UI]

    CheckAPIKey -->|Yes| EnableFeatures

    EnableFeatures --> End([User can use AI features])

    style Start fill:#4a90e2
    style EnableFeatures fill:#50c878
    style ShowInstructions fill:#cd853f
```

**Key Features**:
- API key encryption at rest
- Per-user key isolation
- Rate limiting per user
- Automatic key validation
- Without a key, users share the system key up to `SYSTEM_GEMINI_DAILY_LIMIT_PER_USER` uses a day (default 30); after that they're asked to add a key and background analysis waits

---

## Bookmark Saving Flow

This shows how bookmarks are saved from the extension or web interface.

```mermaid
sequenceDiagram
    participant User
    participant Extension as Chrome Extension
    participant Frontend as Web Frontend
    participant Backend as Flask Backend
    participant DB as Database
    participant Queue as RQ (Redis)
    participant Worker as RQ Worker
    participant Redis as Redis Cache

    User->>Extension: Click 'Save to Fuze' button
    Extension->>Extension: Get current tab URL & title
    Extension->>Extension: Get auth token from storage
    Extension->>Backend: POST /api/bookmarks<br/>{url, title, description, category, tags}

    Backend->>Backend: Validate JWT token
    Backend->>Backend: Sanitize inputs (URL ≤ 2048 bytes)
    Backend->>DB: Check for duplicate URL (normalized)

    alt Duplicate Found
        DB-->>Backend: Existing bookmark
        Backend->>DB: Update existing bookmark
        Backend->>Redis: Invalidate cache
        Backend-->>Extension: 200 OK (updated)
    else New Bookmark
        Backend->>DB: Save bookmark (scrape_status PENDING)
        Backend->>Queue: Enqueue fetch job (one job id per bookmark)
        Note over Backend,Queue: If Redis is down the bookmark stays PENDING<br/>and the reconciler enqueues it later
        Backend->>Redis: Invalidate user caches
        Backend-->>Extension: 201 Created {bookmark_id, processing: background}

        Note over Worker: Background pipeline
        Queue->>Worker: process_bookmark_content_task
        Worker->>Worker: Official API, or robots.txt + domain rate limit + SSRF-safe fetch
        alt Fetched
            Worker->>DB: Save extracted text (SUCCESS)
        else Failed / blocked / disallowed
            Worker->>DB: Keep title + notes (FAILED_FETCH / BLOCKED / DISALLOWED)
        end
        Worker->>Queue: Enqueue embedding job
        Queue->>Worker: generate_embedding_task
        Worker->>DB: Document embedding + passage chunks
        Worker->>Worker: Gemini content profile (only with fetched text)
        Worker->>DB: Save ContentAnalysis record
        Worker->>Redis: XADD pipeline events (live SSE updates)
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
    StartImport --> SizeCheck{More than 5000 items?}
    SizeCheck -->|Yes| TooLarge[413 - extension sends 1000 at a time]
    SizeCheck -->|No| InitProgress[Initialize Progress in Redis]
    InitProgress --> StartSSE[Start SSE Stream for Progress]

    StartSSE --> ProcessBatch[Backend: Process Bookmarks]
    ProcessBatch --> ForEachBookmark{For Each Bookmark}

    ForEachBookmark --> CheckDuplicate[Check if Duplicate or invalid URL]
    CheckDuplicate --> IsDuplicate{Skip?}
    IsDuplicate -->|Yes| SkipBookmark[Skip - Increment skipped_count]
    IsDuplicate -->|No| AddToBatch[Save bookmark as PENDING]

    SkipBookmark --> UpdateProgress[Update Progress in Redis]
    AddToBatch --> UpdateProgress

    UpdateProgress --> MoreBookmarks{More Bookmarks?}
    MoreBookmarks -->|Yes| ForEachBookmark
    MoreBookmarks -->|No| SaveBatch[Commit]

    SaveBatch --> TriggerAnalysis[Enqueue one fetch job per bookmark<br/>fetch, embed and analyze run in RQ]
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

Analysis of saved bookmarks using Gemini AI. It runs at the end of the embedding job
in the RQ worker, not on a polling thread.

```mermaid
sequenceDiagram
    participant Worker as RQ Worker (embedding job)
    participant AnalysisService as Analysis Service
    participant Gemini as Gemini AI
    participant DB as Database
    participant Redis as Redis Cache
    participant User as User Dashboard

    Worker->>Worker: Embedding + passage chunks stored
    Worker->>AnalysisService: analyze_content(bookmark_id, user_id)
    AnalysisService->>DB: Get bookmark & user data

    AnalysisService->>AnalysisService: Skip if already analyzed or no fetched text
    alt Needs Analysis
        AnalysisService->>AnalysisService: Pick key: user's own, or shared system key<br/>(daily per-user cap)
        AnalysisService->>Gemini: Content profile request<br/>(own genai.Client bound to that key)
        Note over Gemini: Every call gets its own client, so a<br/>prompt can never run on another user's key
        Gemini-->>AnalysisService: Summary, what it teaches/solves,<br/>key concepts, when it's useful

        AnalysisService->>DB: Save ContentAnalysis record
        AnalysisService->>Redis: Cache analysis
        AnalysisService->>Redis: Invalidate recommendation cache

        Note over User: Live status via the SSE stream
    end
```

---

## Recommendation Generation Flow

How recommendations are produced for a general query, a project, a task or a subtask. The engine is
`backend/ml/intent_engine/`; see [RECOMMENDATIONS.md](RECOMMENDATIONS.md) for the details.

```mermaid
flowchart TD
    Start([User requests recommendations]) --> SelectContext[Select context:<br/>free text, project, task or subtask]
    SelectContext --> POSTRequest[POST /api/recommendations/unified-orchestrator]
    POSTRequest --> ValidateAuth{Valid JWT?}
    ValidateAuth -->|No| Error1[401 Unauthorized]
    Error1 --> End3([Show error])

    ValidateAuth -->|Yes| BuildIntent[Build intent text from the user's own words:<br/>subtask, task, query, project]
    BuildIntent --> CheckCache{Redis: results for this intent,<br/>limit and content version?}
    CheckCache -->|Hit| ReturnCached[Return cached results]
    ReturnCached --> End1([Display recommendations])

    CheckCache -->|Miss| Stmt{Cached Gemini intent<br/>statement and needs?}
    Stmt -->|Yes| Vectors[Query vectors:<br/>intent text + statement + needs]
    Stmt -->|No| Schedule[Schedule background job] --> Vectors2[Query vector:<br/>intent text]
    Vectors --> Retrieve
    Vectors2 --> Retrieve[Nearest passages and content profiles<br/>of the user's content, pgvector HNSW]
    Retrieve --> Rerank{SEARCH_RERANK_ENABLED?}
    Rerank -->|Yes| CrossEnc[Cross-encoder rerank of the top 30]
    Rerank -->|No| MMR
    CrossEnc --> MMR[MMR diversity]
    MMR --> FormatResults[Attach matched passage and content profile]
    FormatResults --> CacheResults[Cache for 10 minutes]
    CacheResults --> End2([Display recommendations])

    style Start fill:#4a90e2
    style End1 fill:#50c878
    style End2 fill:#50c878
    style End3 fill:#ff6b6b
    style BuildIntent fill:#cd853f
    style Retrieve fill:#cd853f
    style CrossEnc fill:#cd853f
```

Helpful / not-relevant judgments are sent to `POST /api/recommendations/feedback` and stored per project.

---

## Project-Based Recommendations Flow

A project's title, description and technologies are the intent. Creating or editing a project precomputes its
intent statement in the background, so the first request after that already has it.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Queue as RQ (Redis)
    participant Worker as RQ Worker
    participant Gemini as Gemini
    participant DB as Database
    participant Redis as Redis Cache

    User->>Frontend: Create or edit a project
    Frontend->>Backend: POST /api/projects
    Backend->>DB: Save project
    Backend->>Queue: Enqueue project intent job
    Backend-->>Frontend: Project created
    Queue->>Worker: process_project_ml
    Worker->>Gemini: Intent statement + 2-4 information needs
    Worker->>Redis: Cache by context hash (7 days)

    User->>Frontend: Request project recommendations
    Frontend->>Backend: POST /api/recommendations/unified-orchestrator<br/>{project_id}
    Backend->>DB: Load project (owned by the user), and task or subtask if given
    Backend->>Redis: Results cached for this intent?
    alt Hit
        Redis-->>Backend: Cached results
    else Miss
        Backend->>Redis: Intent statement and needs
        Backend->>Backend: Embed intent text, statement and needs
        Backend->>DB: Nearest passages and profiles per query vector (user's content only)
        opt SEARCH_RERANK_ENABLED
            Backend->>Backend: Cross-encoder rerank
        end
        Backend->>Backend: MMR diversity, attach matched passage
        Backend->>Redis: Cache results
    end
    Backend-->>Frontend: Recommendations with score and reason
    Frontend-->>User: Display project-specific recommendations
```

---

## Search Flow

Keyword and semantic search.

```mermaid
flowchart TD
    Start([User enters search query]) --> SearchType{Search type?}

    SearchType -->|Text| TextSearch[GET /api/search/text]
    TextSearch --> QueryDB[Postgres full-text search on search_vector<br/>title, notes and body, websearch syntax<br/>plus a title ILIKE match]
    QueryDB --> TextResults[Ranked with ts_rank_cd]
    TextResults --> End1([Display results])

    SearchType -->|Semantic| SemanticSearch[POST /api/search/supabase-semantic]
    SemanticSearch --> Embed[Embed the query<br/>Redis-cached]
    Embed --> Retrieve[One SQL statement:<br/>nearest passages with their bookmark's details,<br/>plus bookmarks not yet chunked<br/>filtered by user_id, HNSW]
    Retrieve --> Rerank{SEARCH_RERANK_ENABLED?}
    Rerank -->|Yes| CrossEnc[Cross-encoder rerank]
    Rerank -->|No| Merge
    CrossEnc --> Merge[One result per bookmark,<br/>best passage as the snippet]
    Merge --> End2([Display results])

    style Start fill:#4a90e2
    style End1 fill:#50c878
    style End2 fill:#50c878
    style Embed fill:#cd853f
    style Retrieve fill:#cd853f
```

---

## LinkedIn Integration Flow

This shows how users extract and analyze LinkedIn content.

```mermaid
flowchart TD
    Start([User wants to analyze LinkedIn content]) --> CheckAuth{Authenticated?}

    CheckAuth -->|No| AuthRequired[Show authentication required]
    AuthRequired --> End1([Cannot proceed])

    CheckAuth -->|Yes| ChooseMethod{Extraction Method}

    ChooseMethod -->|Single Post| EnterURL[Enter LinkedIn post URL]
    ChooseMethod -->|Batch Extract| SelectProfile[Select LinkedIn profile]

    EnterURL --> ExtractSingle[POST /api/linkedin/extract]
    SelectProfile --> ExtractBatch[POST /api/linkedin/batch-extract]

    ExtractSingle --> Processing[Content processing and analysis]
    ExtractBatch --> Processing

    Processing --> ShowResults[Display extracted content and analysis]
    ShowResults --> SaveOption{Save to Bookmarks?}

    SaveOption -->|Yes| SaveBookmark[POST /api/linkedin/save-to-bookmarks]
    SaveOption -->|No| ViewOnly[View extracted content only]

    SaveBookmark --> BookmarkCreated[Bookmark created with analysis]
    BookmarkCreated --> End2([Content saved])

    ViewOnly --> End3([Content viewed])

    style Start fill:#4a90e2
    style ShowResults fill:#50c878
    style Processing fill:#cd853f
```

**Features**:
- Single post extraction
- Batch profile extraction
- Content analysis with AI
- Save to bookmarks integration
- Extraction history tracking

---

## Task Management Flow

This shows how users create and manage project tasks with AI assistance.

```mermaid
flowchart TD
    Start([User needs to break down project]) --> ChooseProject[Select existing project]

    ChooseProject --> DescribeTask[Describe task in natural language]
    DescribeTask --> UseAIBreakdown{Use AI Breakdown?}

    UseAIBreakdown -->|Yes| SubmitToAI[POST /api/tasks/ai-breakdown]
    UseAIBreakdown -->|No| ManualBreakdown[Manually create subtasks]

    SubmitToAI --> AIProcessing[AI analyzes and breaks down task]
    AIProcessing --> ShowSuggestions[Show AI-generated subtasks]
    ShowSuggestions --> ReviewEdit{Review and Edit?}

    ReviewEdit -->|Yes| ModifyTasks[Modify suggested tasks]
    ReviewEdit -->|No| AcceptTasks[Accept AI suggestions]

    ModifyTasks --> CreateTasks[Create tasks and subtasks]
    AcceptTasks --> CreateTasks

    ManualBreakdown --> CreateTasks

    CreateTasks --> TaskCreated[Tasks created in database]
    TaskCreated --> ManageTasks[User can update, complete tasks]
    ManageTasks --> GetRecommendations{Get Task Recommendations?}

    GetRecommendations -->|Yes| TaskRecs[POST /api/recommendations/task/:id]
    GetRecommendations -->|No| ContinueWork[Continue working]

    TaskRecs --> ShowTaskRecs[Show relevant content recommendations]
    ShowTaskRecs --> End1([Task completed with recommendations])

    ContinueWork --> End2([Task management complete])

    style Start fill:#4a90e2
    style TaskCreated fill:#50c878
    style AIProcessing fill:#cd853f
```

**Features**:
- AI-powered task breakdown
- Manual task creation
- Subtask management
- Task-based recommendations
- Progress tracking

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

High-level view of how the components interact. See [ARCHITECTURE.md](ARCHITECTURE.md) for the deployment.

```mermaid
graph TB
    subgraph "User interface"
        WebApp[Web app<br/>React + Vite]
        Extension[Chrome extension<br/>Manifest V3]
    end

    subgraph "API (Flask blueprints)"
        AuthAPI[Auth<br/>JWT]
        BookmarksAPI[Bookmarks<br/>CRUD and import]
        ProjectsAPI[Projects and tasks]
        RecommendationsAPI[Recommendations]
        SearchAPI[Search]
    end

    subgraph "Engine and services"
        Engine[Intent engine<br/>ml/intent_engine]
        Retrieval[Passage retrieval<br/>services/hybrid_search]
    end

    subgraph "RQ workers"
        Pipeline[Bookmark pipeline<br/>fetch, embed, chunk, profile]
        IntentJob[Project intent job]
        Reconciler[Reconciler<br/>every 5 minutes]
    end

    subgraph "Data"
        PostgreSQL[(PostgreSQL + pgvector<br/>content_chunks, HNSW)]
        Redis[(Redis<br/>cache and queues)]
    end

    subgraph "External"
        Gemini[Google Gemini<br/>user's key or capped system key]
        WebContent[Web content<br/>HTTP fetch, reader service, Wayback]
    end

    WebApp --> AuthAPI
    WebApp --> BookmarksAPI
    WebApp --> ProjectsAPI
    WebApp --> RecommendationsAPI
    WebApp --> SearchAPI
    Extension --> AuthAPI
    Extension --> BookmarksAPI

    BookmarksAPI --> PostgreSQL
    BookmarksAPI -->|enqueue| Redis
    ProjectsAPI --> PostgreSQL
    ProjectsAPI -->|enqueue| Redis
    RecommendationsAPI --> Engine
    SearchAPI --> Retrieval
    Engine --> Retrieval
    Engine --> Redis
    Retrieval --> PostgreSQL

    Redis -->|jobs| Pipeline
    Redis -->|jobs| IntentJob
    Reconciler -.->|re-enqueue| Redis
    Pipeline --> WebContent
    Pipeline --> PostgreSQL
    Pipeline --> Gemini
    IntentJob --> Gemini
    IntentJob --> Redis

    style WebApp fill:#4a90e2
    style Extension fill:#4a90e2
    style Engine fill:#cd853f
    style Pipeline fill:#cd853f
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
- **Caching Strategy**: shared Redis caches for pages, embeddings, analysis and recommendation results
- **User Isolation**: Gemini requests use the user's own key, or the shared system key up to a daily per-user cap, so one user cannot use another's quota
- **Error Handling**: transient failures are retried by RQ, and a reconciler re-enqueues work that was lost or deferred
- **Real-time Updates**: Server-Sent Events stream import progress and pipeline status
