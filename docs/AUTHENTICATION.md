# Authentication & Session Management

This document describes the authentication system and session context isolation implemented in the ChatKit Order Returns sample.

## Overview

The application implements user authentication to ensure:
- **Conversation isolation**: Each user sees only their own chat threads
- **Session context isolation**: In-progress return workflows are isolated per conversation
- **User-specific greetings**: Personalized experience based on logged-in user

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         AUTHENTICATION FLOW                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Browser                    Backend                     Cosmos DB           │
│   ───────                    ───────                     ─────────           │
│                                                                              │
│   1. User enters email/password                                              │
│         │                                                                    │
│         ▼                                                                    │
│   POST /api/auth/login ──────────►  Lookup customer by email                 │
│                                           │                                  │
│                                           ▼                                  │
│                                    Verify password (hardcoded demo)          │
│                                           │                                  │
│                                           ▼                                  │
│   ◄────────────────────────────  Create session token                        │
│   Store token in:                        │                                   │
│   • localStorage                         ▼                                   │
│   • cookie (for ChatKit)          Store in memory                            │
│                                                                              │
│   2. User sends chat message                                                 │
│         │                                                                    │
│         ▼                                                                    │
│   POST /chatkit ─────────────────►  Extract token from cookie                │
│   (cookie: auth_token=xxx)              │                                    │
│                                         ▼                                    │
│                                   Get user_id from session                   │
│                                         │                                    │
│                                         ▼                                    │
│                                   Pass user_id in context ──────►  Thread    │
│                                                                   owner_id   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Demo Credentials

For testing, all demo customers use the same password:

| Email | Password | Name | Membership Tier |
|-------|----------|------|-----------------|
| `jane.smith@email.com` | `demo123` | Jane Smith | Gold |
| `john.doe@email.com` | `demo123` | John Doe | Basic |
| `alice.johnson@email.com` | `demo123` | Alice Johnson | Platinum |
| `bob.wilson@email.com` | `demo123` | Bob Wilson | Basic |
| `carol.davis@email.com` | `demo123` | Carol Davis | Gold |

## Components

### 1. Authentication Module (`auth.py`)

```python
# Password hashing (SHA-256 for demo, use bcrypt in production)
def hash_password(password: str) -> str:
    salt = "chatkit_retail_demo_salt_"
    return hashlib.sha256((salt + password).encode()).hexdigest()

# Session management (in-memory for demo)
_sessions: Dict[str, Dict[str, Any]] = {}

def create_session(user_data: Dict[str, Any]) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "user_id": user_data["id"],
        "email": user_data["email"],
        # ... expires in 24 hours
    }
    return token
```

### 2. Password Verification

Passwords are **hardcoded** for the demo (not stored in Cosmos DB):

```python
DEFAULT_PASSWORD = "demo123"
DEFAULT_PASSWORD_HASH = hash_password(DEFAULT_PASSWORD)

# All demo customers use the same password
DEMO_PASSWORDS = {
    "jane.smith@email.com": DEFAULT_PASSWORD_HASH,
    # ...
}
```

To use Cosmos DB for passwords, add a `password_hash` field to customer documents.

### 3. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | Authenticate with email/password |
| `/api/auth/logout` | POST | Invalidate session |
| `/api/auth/me` | GET | Get current user info |

### 4. Frontend Integration

The frontend stores the auth token in both localStorage and a cookie:

```typescript
// On successful login
localStorage.setItem('auth_token', data.token);
document.cookie = `auth_token=${data.token}; path=/; max-age=86400; SameSite=Strict`;
```

The cookie is necessary because ChatKit's API doesn't support custom headers, so the token is sent automatically with requests.

## Thread Ownership

### How Threads Are Isolated

When a thread is created, it's associated with the logged-in user:

```python
# cosmos_store.py - _create_thread()
thread_doc = {
    "id": thread_id,
    "title": "New Chat",
    "owner_id": user_id,  # From auth context
    # ...
}
```

### How Threads Are Filtered

When loading the thread list, only the user's threads are returned:

```python
# cosmos_store.py - load_threads()
if user_id:
    # Authenticated: show only their threads
    query = "SELECT * FROM c WHERE c.owner_id = @owner_id"
else:
    # Anonymous: show only anonymous threads
    query = "SELECT * FROM c WHERE NOT IS_DEFINED(c.owner_id) OR c.owner_id = null"
```

### Backward Compatibility

Old threads (without `owner_id`) are:
- ✅ Visible to anonymous users
- ❌ Not visible to logged-in users (they start fresh)

No data migration is required.

## Session Context Isolation

### The Problem (Before Fix)

The session context was stored as a single dictionary on the server:

```python
class RetailChatKitServer:
    def __init__(self):
        self._session_context = {}  # ❌ SHARED across ALL concurrent users!
```

This caused race conditions where concurrent users would overwrite each other's session state.

### The Solution (Per-Thread Sessions)

Session context is now stored per-thread:

```python
class RetailChatKitServer:
    def __init__(self):
        self._thread_sessions: dict[str, dict] = {}  # ✅ Isolated per thread
    
    def _get_session_context(self, thread_id: str) -> dict:
        if thread_id not in self._thread_sessions:
            self._thread_sessions[thread_id] = {}
        return self._thread_sessions[thread_id]
```

### Session Context Contents

The session context tracks the return workflow state:

```python
{
    "customer_id": "cust_001",
    "customer_name": "Jane Smith",
    "selected_order_id": "ord_12345",
    "selected_product_id": "prod_abc",
    "selected_item_name": "Wireless Headphones",
    "reason_code": "DEFECTIVE",
    "resolution": "FULL_REFUND",
    "shipping_method": "PREPAID_LABEL",
    "displayed_orders": [...],  # For natural language references
}
```

## Security Considerations

### Current Implementation (Demo)

| Aspect | Implementation | Production Recommendation |
|--------|---------------|---------------------------|
| Password storage | Hardcoded hash | Store bcrypt hashes in Cosmos DB |
| Session storage | In-memory dict | Use Redis or Cosmos DB |
| Token format | URL-safe random | Consider JWT with expiry |
| HTTPS | Not enforced | Always use HTTPS |

### Production Improvements

1. **Use bcrypt for password hashing**
   ```python
   import bcrypt
   hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
   ```

2. **Store sessions in Cosmos DB or Redis**
   - Survives server restarts
   - Works with multiple server instances

3. **Add session cleanup**
   - Delete expired sessions periodically
   - Clear session when thread is deleted

4. **Use JWT tokens**
   - Stateless authentication
   - Built-in expiration
   - Can include user claims

## Horizontal Scaling Considerations

The current in-memory session storage doesn't work with multiple server instances. For horizontal scaling:

1. **Shared session store** (Redis/Cosmos DB)
2. **Sticky sessions** (route user to same server)
3. **JWT tokens** (stateless, no server-side session)

The per-thread session context (`_thread_sessions`) also needs to be externalized for multi-instance deployments.
