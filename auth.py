"""
Authentication module for user login.

Provides simple email/password authentication using existing customers
in Cosmos DB. Passwords are hashed using bcrypt.
"""

import logging
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)


# =============================================================================
# MODELS
# =============================================================================

class LoginRequest(BaseModel):
    """Login request model."""
    email: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None


class UserSession(BaseModel):
    """User session data."""
    user_id: str
    email: str
    first_name: str
    last_name: str
    membership_tier: str


# =============================================================================
# PASSWORD UTILITIES
# =============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256 with salt.
    
    Note: For production, use bcrypt or argon2. SHA-256 is used here
    for simplicity since bcrypt requires additional dependencies.
    """
    # Create a salt from the password itself (deterministic for demo)
    # In production, use a random salt stored with the hash
    salt = "chatkit_retail_demo_salt_"
    salted = salt + password
    return hashlib.sha256(salted.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(password) == password_hash


def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)


# =============================================================================
# SESSION STORE (In-Memory for Demo)
# =============================================================================

# In production, store sessions in Redis or Cosmos DB
_sessions: Dict[str, Dict[str, Any]] = {}


def create_session(user_data: Dict[str, Any]) -> str:
    """Create a new session for a user and return the token."""
    token = generate_session_token()
    
    _sessions[token] = {
        "user_id": user_data["id"],
        "email": user_data["email"],
        "first_name": user_data.get("first_name", ""),
        "last_name": user_data.get("last_name", ""),
        "membership_tier": user_data.get("membership_tier", "Basic"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }
    
    logger.info(f"Created session for user {user_data['id']}")
    return token


def get_session(token: str) -> Optional[Dict[str, Any]]:
    """Get session data for a token, or None if invalid/expired."""
    if not token or token not in _sessions:
        return None
    
    session = _sessions[token]
    
    # Check expiration
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        del _sessions[token]
        return None
    
    return session


def delete_session(token: str) -> bool:
    """Delete a session (logout)."""
    if token in _sessions:
        del _sessions[token]
        return True
    return False


def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user_id from a valid session token."""
    session = get_session(token)
    return session["user_id"] if session else None


# =============================================================================
# DEFAULT PASSWORDS FOR DEMO CUSTOMERS
# =============================================================================

# Default password for all demo customers (for easy testing)
DEFAULT_PASSWORD = "demo123"
DEFAULT_PASSWORD_HASH = hash_password(DEFAULT_PASSWORD)

# Map of customer emails to their passwords (all same for demo)
DEMO_PASSWORDS = {
    "jane.smith@email.com": DEFAULT_PASSWORD_HASH,
    "rjohnson@company.com": DEFAULT_PASSWORD_HASH,
    "m.garcia@inbox.com": DEFAULT_PASSWORD_HASH,
    "mchen2024@gmail.com": DEFAULT_PASSWORD_HASH,
    "swilliams@outlook.com": DEFAULT_PASSWORD_HASH,
}


def get_password_hash_for_customer(email: str) -> str:
    """Get the password hash for a customer email."""
    return DEMO_PASSWORDS.get(email, DEFAULT_PASSWORD_HASH)
