"""
PatientPath AI - System Router
==============================
System health check and status endpoints.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from schemas.common import StatusResponse
from config import settings
from utils.cache import cache_manager as cache

router = APIRouter(tags=["System"])

# Track server start time for uptime calculation
_server_start_time = time.time()


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Health Check",
    description="Check backend system health and connectivity status."
)
async def health_check(db: Session = Depends(get_db)):
    """
    Backend health check endpoint.
    
    Returns:
        StatusResponse with system health information
        
    Example Response:
    ```json
    {
        "status": "healthy",
        "message": "PatientPath AI Backend is running",
        "version": "1.0.0",
        "timestamp": "2024-01-15T10:30:00Z",
        "database_connected": true,
        "uptime_seconds": 3600.5
    }
    ```
    """
    # Check database connectivity
    db_connected = False
    try:
        db.execute("SELECT 1")
        db_connected = True
    except Exception:
        db_connected = False
    
    # Calculate uptime
    uptime = time.time() - _server_start_time
    
    # Determine overall status
    status = "healthy" if db_connected else "degraded"
    
    return StatusResponse(
        status=status,
        message=f"{settings.APP_NAME} Backend is running",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        database_connected=db_connected,
        uptime_seconds=round(uptime, 2)
    )


@router.get(
    "/",
    summary="Root Endpoint",
    description="Redirects to the frontend application."
)
async def root():
    """
    Root endpoint - redirects to the frontend.
    """
    return RedirectResponse(url="/frontend/index.html")


@router.get(
    "/cache/stats",
    summary="Cache Statistics",
    description="Get cache performance statistics."
)
async def cache_stats():
    """
    Get cache statistics for monitoring.
    
    Returns:
        Cache hit/miss statistics
    """
    return {
        "cache_stats": cache.stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post(
    "/cache/clear",
    summary="Clear Cache",
    description="Clear all cached data."
)
async def clear_cache():
    """
    Clear all cached data.
    
    Returns:
        Confirmation message
    """
    cache.clear()
    return {
        "message": "Cache cleared successfully",
        "timestamp": datetime.utcnow().isoformat()
    }
