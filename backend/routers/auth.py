"""
PatientPath AI - Auth Router
=============================
Login / Logout / Me endpoints.
No authentication required on these endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from auth import authenticate_user, create_token, invalidate_token, get_token_user, _extract_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    user_id: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: str
    role: str
    name: str
    message: str


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login",
    description="Authenticate with user_id and password. Returns a Bearer token valid for 8 hours."
)
async def login(data: LoginRequest):
    """
    Login endpoint.

    Demo credentials:
    - admin001 / Admin@123
    - staff001 / Staff@123
    - doctor001 / Doctor@123
    - patient001 / Patient@123
    """
    user = authenticate_user(data.user_id, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID or password."
        )
    token = create_token(user["user_id"], user["role"], user["name"])
    logger.info("User logged in: %s (role=%s)", user["user_id"], user["role"])
    return LoginResponse(
        token=token,
        user_id=user["user_id"],
        role=user["role"],
        name=user["name"],
        message=f"Welcome, {user['name']}!"
    )


@router.post(
    "/logout",
    summary="Logout",
    description="Invalidate the current session token."
)
async def logout(request: Request):
    """Logout — invalidates the Bearer token."""
    token = _extract_token(request)
    if token:
        invalidate_token(token)
    return {"message": "Logged out successfully."}


@router.get(
    "/me",
    summary="Current User",
    description="Returns the currently authenticated user's info."
)
async def get_me(request: Request):
    """Return current user info from token."""
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    user = get_token_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return {
        "user_id": user["user_id"],
        "role": user["role"],
        "name": user["name"],
        "created_at": user.get("created_at"),
    }


@router.get(
    "/demo-users",
    summary="List Demo Credentials",
    description="Returns available demo login credentials for testing."
)
async def demo_users():
    """Return demo credentials for easy testing."""
    return {
        "demo_credentials": [
            {"user_id": "admin001",   "password": "Admin@123",   "role": "admin"},
            {"user_id": "staff001",   "password": "Staff@123",   "role": "staff"},
            {"user_id": "doctor001",  "password": "Doctor@123",  "role": "doctor"},
            {"user_id": "patient001", "password": "Patient@123", "role": "patient"},
        ],
        "note": "These are demo credentials for development/testing only."
    }
