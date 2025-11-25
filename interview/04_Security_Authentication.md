# Part 4: Security, Authentication & Multi-tenancy

## 📋 Table of Contents

1. [JWT Authentication Flow](#jwt-authentication-flow)
2. [User Data Isolation](#user-data-isolation)
3. [Multi-Tenant Architecture](#multi-tenant-architecture)
4. [API Key Management](#api-key-management)
5. [Security Middleware](#security-middleware)
6. [Rate Limiting](#rate-limiting)
7. [Q&A Section](#qa-section)

---

## JWT Authentication Flow

### Authentication Architecture

**Flow:**
```
1. User Login → POST /api/auth/login
2. Server validates credentials
3. Server generates JWT tokens (access + refresh)
4. Access token in response body
5. Refresh token in HTTP-only cookie
6. Client stores access token in localStorage
7. All subsequent requests include: Authorization: Bearer {token}
```

**File**: `backend/blueprints/auth.py`

### Token Generation

```python
from flask_jwt_extended import create_access_token, create_refresh_token

@auth_bp.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(username=identifier).first()
    
    if user and check_password_hash(user.password_hash, password):
        # Generate tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        response = jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        })
        
        # Set refresh token in HTTP-only cookie
        set_refresh_cookies(response, refresh_token)
        
        return response, 200
```

### Token Validation

**Middleware**: All protected endpoints use `@jwt_required()`

```python
@jwt_required()
def get_bookmarks():
    current_user_id = get_jwt_identity()  # Extract user_id from token
    # Use user_id for queries
```

**File**: `backend/blueprints/bookmarks.py`

### Token Refresh

**Purpose**: Extend session without re-login

```python
@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({'access_token': access_token}), 200
```

**Frontend**: Automatic refresh on 401 errors

**File**: `frontend/src/services/api.js`

---

## User Data Isolation

### Three-Layer Isolation

#### Layer 1: Application-Level Filtering

**All queries include `user_id` filter**

```python
@jwt_required()
@require_user_context
def get_bookmarks(user_id: int):
    # user_id guaranteed to be present and valid
    bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
    return jsonify([b.to_dict() for b in bookmarks])
```

**Decorator**: `@require_user_context`

**File**: `backend/middleware/security_middleware.py`

```python
def require_user_context(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        user_id = int(user_id)
        g.current_user_id = user_id
        kwargs['user_id'] = user_id
        
        return func(*args, **kwargs)
    return wrapper
```

#### Layer 2: Database-Level Indexes

**Composite indexes ensure fast user-specific queries**

```sql
CREATE INDEX idx_saved_content_user_id ON saved_content(user_id);
CREATE INDEX idx_saved_content_user_quality ON saved_content(user_id, quality_score DESC);
```

**Benefits:**
- ✅ Fast lookups (O(log n) instead of O(n))
- ✅ Database-level security
- ✅ Prevents accidental cross-user queries

**File**: `backend/utils/database_indexes.py`

#### Layer 3: API-Level Validation

**JWT token validation on every request**

```python
@jwt_required()
def protected_endpoint():
    user_id = get_jwt_identity()  # From JWT token
    # Token is signed, can't be tampered with
```

**Security Benefits:**
- ✅ Tokens are signed (can't be modified)
- ✅ Token expiration enforced
- ✅ User ID extracted from token (not from request body)

---

## Multi-Tenant Architecture

### Design Principles

1. **Complete Data Isolation**: Users can't access each other's data
2. **Per-User Resources**: API keys, rate limits, preferences
3. **Scalable**: Scales per-user independently
4. **Secure**: Multiple layers of security

### Implementation

**User-Scoped Queries:**
```python
# All queries filtered by user_id
SavedContent.query.filter_by(user_id=current_user_id).all()
Project.query.filter_by(user_id=current_user_id).all()
```

**User-Scoped Caching:**
```python
# Cache keys include user_id
cache_key = f"user_bookmarks:{user_id}"
cache_key = f"recommendations:{user_id}:{request_hash}"
```

**User-Scoped API Keys:**
```python
# Each user has their own Gemini API key
api_key = get_user_api_key(user_id)
gemini_analyzer = GeminiAnalyzer(api_key=api_key)
```

### Data Model

**All user-related tables have `user_id` foreign key:**

```python
class SavedContent(Base):
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), 
                    nullable=False, index=True)
    # ... other fields
```

**Cascade Delete:**
- When user is deleted, all their data is deleted
- Ensures no orphaned data
- Maintains data integrity

---

## API Key Management

### Per-User API Key System

**Problem**: Shared API key limits and costs

**Solution**: Encrypted per-user API keys with individual rate limiting

**File**: `backend/services/multi_user_api_manager.py`

### Encryption

**Fernet Encryption** (symmetric encryption)

```python
from cryptography.fernet import Fernet

# Generate key from SECRET_KEY
secret_key = os.environ.get('SECRET_KEY')
key = hashlib.sha256(secret_key.encode()).digest()
cipher = Fernet(base64.urlsafe_b64encode(key))

# Encrypt API key
encrypted_key = cipher.encrypt(api_key.encode()).decode()

# Decrypt API key
decrypted_key = cipher.decrypt(encrypted_key.encode()).decode()
```

**Storage**: Encrypted keys stored in `user_metadata` JSON field

```python
user.user_metadata = {
    'api_key': {
        'encrypted': encrypted_key,
        'hash': api_key_hash,
        'name': 'My API Key',
        'status': 'active'
    }
}
```

### Rate Limiting Per User

**Limits:**
- 15 requests per minute
- 1,500 requests per day
- 45,000 requests per month

**Implementation:**
```python
def check_user_rate_limit(user_id: int) -> Dict:
    current_time = datetime.now()
    
    # Check minute limit
    requests_last_minute = count_requests(user_id, since=current_time - timedelta(minutes=1))
    if requests_last_minute >= self.REQUESTS_PER_MINUTE:
        return {'can_make_request': False, 'wait_time_seconds': 60}
    
    # Check day limit
    requests_today = count_requests(user_id, since=current_time.replace(hour=0, minute=0))
    if requests_today >= self.REQUESTS_PER_DAY:
        return {'can_make_request': False, 'wait_time_seconds': 86400}
    
    return {'can_make_request': True}
```

### API Key Validation

**Format Validation:**
```python
def validate_api_key(self, api_key: str) -> bool:
    if not api_key:
        return False
    
    # Gemini API keys start with 'AIza'
    if not api_key.startswith('AIza'):
        return False
    
    # Check length (typically 39 characters)
    if len(api_key) < 30:
        return False
    
    return True
```

**Testing Endpoint:**
```python
@user_api_key_bp.route('/test', methods=['POST'])
@jwt_required()
def test_api_key():
    # Test user's API key with actual Gemini request
    # Return success/failure
```

---

## Security Middleware

### Input Validation

**File**: `backend/middleware/validation.py`

**Purpose**: Sanitize and validate all inputs

```python
def sanitize_string(text, max_length=255):
    """Remove null bytes, control characters, limit length"""
    if not text:
        return None
    
    # Remove null bytes and control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Trim whitespace
    text = text.strip()
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text
```

### SQL Injection Prevention

**Parameterized Queries**: All queries use SQLAlchemy ORM or parameterized SQL

```python
# ✅ Safe - Parameterized
user = User.query.filter_by(username=username).first()

# ✅ Safe - Parameterized SQL
db.session.execute(
    text("SELECT * FROM users WHERE username = :username"),
    {'username': username}
)

# ❌ Never do this - SQL Injection risk
db.session.execute(f"SELECT * FROM users WHERE username = '{username}'")
```

### XSS Prevention

**Input Sanitization**: Remove dangerous characters

```python
def sanitize_input(text):
    # Remove script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE)
    # Remove event handlers
    text = re.sub(r'on\w+\s*=', '', text)
    return text
```

**Output Escaping**: React automatically escapes content

```javascript
// ✅ Safe - React escapes automatically
<div>{userInput}</div>

// ❌ Dangerous - Don't use dangerouslySetInnerHTML
<div dangerouslySetInnerHTML={{ __html: userInput }} />
```

---

## Rate Limiting

### Implementation

**File**: `backend/middleware/rate_limiting.py`

**Flask-Limiter** with Redis backend

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=redis_url,
    default_limits=["100 per minute"]
)
```

### Rate Limits by Endpoint

**Login/Register**: Stricter limits (prevent brute force)
```python
@limiter.limit("5 per 15 minutes")
@auth_bp.route('/login', methods=['POST'])
def login():
    # Login logic
```

**Recommendations**: Moderate limits (expensive operations)
```python
@limiter.limit("20 per minute")
@recommendations_bp.route('/unified-orchestrator', methods=['POST'])
def unified_orchestrator():
    # Recommendation logic
```

**Other Endpoints**: Standard limits
```python
@limiter.limit("100 per minute")
@bookmarks_bp.route('/', methods=['GET'])
def get_bookmarks():
    # Bookmarks logic
```

### Rate Limit Headers

**Response Headers:**
```
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 15
X-RateLimit-Reset: 1609459200
```

**Rate Limit Exceeded Response:**
```json
{
  "message": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

**Status Code**: `429 Too Many Requests`

---

## Q&A Section

### Q1: How do you prevent JWT token tampering?

**Answer:**
JWT tokens are cryptographically signed:

1. **Token Structure**: `header.payload.signature`
2. **Signature**: HMAC-SHA256 hash of header + payload + secret
3. **Validation**: Server verifies signature on every request
4. **Secret Key**: Stored in environment variable (never in code)

**If token is tampered:**
- Signature won't match
- Token validation fails
- Request rejected with 401 Unauthorized

**Code:**
```python
# Token creation (signed)
access_token = create_access_token(identity=str(user.id))

# Token validation (verifies signature)
@jwt_required()
def protected_endpoint():
    user_id = get_jwt_identity()  # Only works if signature is valid
```

### Q2: How do you handle token expiration?

**Answer:**
Multiple strategies:

1. **Access Token**: Short-lived (1 hour), stored in localStorage
2. **Refresh Token**: Long-lived (30 days), stored in HTTP-only cookie
3. **Automatic Refresh**: Frontend refreshes token before expiration
4. **Fallback**: Redirect to login if refresh fails

**Frontend Implementation:**
```javascript
// Proactive token refresh
const refreshTokenIfNeeded = async () => {
  const token = localStorage.getItem('token');
  const payload = JSON.parse(atob(token.split('.')[1]));
  const expirationTime = payload.exp * 1000;
  
  // If expires in less than 5 minutes, refresh
  if (expirationTime - Date.now() < 5 * 60 * 1000) {
    const res = await axios.post('/api/auth/refresh', {}, {
      withCredentials: true
    });
    localStorage.setItem('token', res.data.access_token);
  }
};
```

### Q3: How do you ensure users can't access each other's data?

**Answer:**
Three-layer defense:

1. **Application Level**: All queries filtered by `user_id`
   ```python
   @require_user_context
   def get_bookmarks(user_id: int):
       # user_id from JWT token, can't be faked
       return SavedContent.query.filter_by(user_id=user_id).all()
   ```

2. **Database Level**: Composite indexes on `user_id`
   ```sql
   CREATE INDEX idx_saved_content_user_id ON saved_content(user_id);
   ```

3. **API Level**: JWT validation extracts `user_id` from token (not request)

**Even if bug occurs:**
- Database indexes ensure user isolation
- JWT tokens can't be tampered with
- Multiple layers of defense

### Q4: How do you secure API keys in the database?

**Answer:**
Multiple security measures:

1. **Encryption**: Fernet encryption (symmetric)
   ```python
   encrypted_key = cipher.encrypt(api_key.encode()).decode()
   ```

2. **Hashing**: SHA-256 hash for verification
   ```python
   api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
   ```

3. **Storage**: Encrypted keys in `user_metadata` JSON field
4. **Access Control**: Only user can access their own API key
5. **Key Derivation**: Encryption key derived from `SECRET_KEY`

**Security Benefits:**
- ✅ Keys encrypted at rest
- ✅ Can't be read without decryption key
- ✅ Per-user isolation
- ✅ Can be rotated if compromised

### Q5: How do you prevent brute force attacks?

**Answer:**
Multiple strategies:

1. **Rate Limiting**: 5 login attempts per 15 minutes per IP
   ```python
   @limiter.limit("5 per 15 minutes", key_func=get_remote_address)
   def login():
       # Login logic
   ```

2. **Password Hashing**: bcrypt with salt (slow hashing)
   ```python
   password_hash = generate_password_hash(password)  # Uses bcrypt
   ```

3. **Account Lockout**: Future feature (lock after N failed attempts)
4. **CAPTCHA**: Future feature for suspicious activity

**Current Protection:**
- ✅ Rate limiting prevents rapid attempts
- ✅ Password hashing prevents rainbow table attacks
- ✅ No user enumeration (same error for invalid username/password)

---

## Summary

Security implementation focuses on:
- ✅ **JWT authentication** with token refresh
- ✅ **Three-layer data isolation** (application, database, API)
- ✅ **Encrypted API keys** with per-user rate limiting
- ✅ **Input validation** and sanitization
- ✅ **SQL injection prevention** via parameterized queries
- ✅ **XSS prevention** via input sanitization
- ✅ **Rate limiting** to prevent abuse

**Key Files:**
- `backend/blueprints/auth.py` - Authentication
- `backend/middleware/security_middleware.py` - Security middleware
- `backend/services/multi_user_api_manager.py` - API key management
- `backend/middleware/rate_limiting.py` - Rate limiting

---

**Next**: [Part 5: ML/AI & Recommendation System](./05_ML_AI_Recommendations.md)

