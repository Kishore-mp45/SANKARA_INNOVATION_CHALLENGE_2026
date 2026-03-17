"""
PatientPath AI - Authentication Module
=======================================
Simple token-based authentication for demo/development use.
Tokens are signed secrets stored server-side with TTL of 8 hours.

Demo credentials:
  admin001  / Admin@123   → role: admin
  staff001  / Staff@123   → role: staff
  doctor001 / Doctor@123  → role: doctor
  patient001/ Patient@123 → role: patient
"""

import os
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Demo user store (replace with DB users in production)
# ---------------------------------------------------------------------------
DEMO_USERS: Dict[str, Dict[str, str]] = {
    "admin001":   {"password": "Admin@123",   "role": "admin",   "name": "Admin User"},
    "staff001":   {"password": "Staff@123",   "role": "staff",   "name": "Staff Member"},
    "staff002":   {"password": "Staff@456",   "role": "staff",   "name": "Staff Member 2"},
    "doctor001":  {"password": "Doctor@123",  "role": "doctor",  "name": "Dr. Smith"},
    "doctor002":  {"password": "Doctor@456",  "role": "doctor",  "name": "Dr. Patel"},
    "patient001": {"password": "Patient@123", "role": "patient", "name": "Patient User"},
}

# ---------------------------------------------------------------------------
# In-memory token store  { token: {user_id, role, name, expires_at} }
# ---------------------------------------------------------------------------
_active_tokens: Dict[str, Dict[str, Any]] = {}
TOKEN_TTL_HOURS = 8


def _hash_password(password: str) -> str:
    """Simple SHA-256 hash (demo only — use bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate_user(user_id: str, password: str) -> Optional[Dict[str, Any]]:
    """Validate credentials. Returns user dict on success, None on failure."""
    user = DEMO_USERS.get(user_id)
    if not user:
        return None
    if user["password"] != password:   # plain-text compare for demo
        return None
    return {"user_id": user_id, "role": user["role"], "name": user["name"]}


def create_token(user_id: str, role: str, name: str) -> str:
    """Create a secure random token and store it server-side."""
    token = secrets.token_hex(32)
    _active_tokens[token] = {
        "user_id": user_id,
        "role": role,
        "name": name,
        "expires_at": datetime.now() + timedelta(hours=TOKEN_TTL_HOURS),
        "created_at": datetime.now().isoformat(),
    }
    _purge_expired_tokens()
    return token


def invalidate_token(token: str) -> bool:
    """Remove token from store (logout)."""
    return _active_tokens.pop(token, None) is not None


def get_token_user(token: str) -> Optional[Dict[str, Any]]:
    """Return user data for a valid, non-expired token."""
    data = _active_tokens.get(token)
    if not data:
        return None
    if datetime.now() > data["expires_at"]:
        del _active_tokens[token]
        return None
    return data


def _purge_expired_tokens():
    """Clean up expired tokens (runs on each login)."""
    now = datetime.now()
    expired = [t for t, d in _active_tokens.items() if now > d["expires_at"]]
    for t in expired:
        del _active_tokens[t]


# ---------------------------------------------------------------------------
# FastAPI dependency helpers
# ---------------------------------------------------------------------------

def _extract_token(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    # Also allow token in query param for browser-based video streams
    return request.query_params.get("token")


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency — validates Bearer token and returns user dict.
    Raises HTTP 401 if token is missing or invalid.
    """
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_token_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory — checks that authenticated user has one of the allowed roles.

    Usage:
        @router.get("/admin-only")
        async def endpoint(user = Depends(require_role("admin"))):
            ...
    """
    def _checker(request: Request) -> Dict[str, Any]:
        user = get_current_user(request)
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}",
            )
        return user
    return _checker
