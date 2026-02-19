"""
PatientPath AI - Main Application
=================================
FastAPI application entry point with middleware and router configuration.

This is the main entry point for the PatientPath AI backend system.
It configures the FastAPI application, registers middleware, and includes
all API routers.

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Or directly:
    python main.py
"""

# Force reload for schema update 2026-02-13 22:20

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import sys
import os

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Now import modules
from config import settings
from database.database import init_db
from utils.logger import setup_logging, get_logger
from utils.middleware import (
    RequestLoggingMiddleware,
    ErrorHandlingMiddleware,
    RateLimitMiddleware
)

# Import routers
from routers.system import router as system_router
from routers.patients import router as patients_router
from routers.zones import router as zones_router
from routers.occupancy import router as occupancy_router
from routers.alerts import router as alerts_router
from routers.metrics import router as metrics_router
from routers.websocket import router as websocket_router
from routers.export import router as export_router
from routers.admin import router as admin_router

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs startup and shutdown logic.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Seed initial data if needed
    try:
        from seed_data import seed_initial_data
        seed_initial_data()
    except ImportError:
        logger.info("Seed data module not found, skipping initial data seeding")
    except Exception as e:
        logger.warning(f"Data seeding skipped: {e}")
    
    logger.info(f"Server ready at http://{settings.HOST}:{settings.PORT}")
    logger.info(f"API Documentation: http://{settings.HOST}:{settings.PORT}/docs")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PatientPath AI backend...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

# CORS middleware - must be added first
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"]
)

# Error handling middleware
app.add_middleware(ErrorHandlingMiddleware)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting middleware (with reasonable defaults)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_window=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW
)


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": f"The requested resource '{request.url.path}' was not found",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": str(exc)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle internal server errors."""
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred"
        }
    )


# =============================================================================
# ROUTER REGISTRATION
# =============================================================================

# System routes (health check, root)
app.include_router(system_router)

# Patient management routes
app.include_router(patients_router)

# Admin routes
app.include_router(admin_router) # new

# Zone management routes
app.include_router(zones_router)

# Occupancy tracking routes
app.include_router(occupancy_router)

# Alert management routes
app.include_router(alerts_router)

# Metrics and analytics routes
app.include_router(metrics_router)

# WebSocket routes
app.include_router(websocket_router)

# Export routes
app.include_router(export_router)

# Prediction routes (New)
from routers.prediction import router as prediction_router
app.include_router(prediction_router)

# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(backend_dir), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    """
    Run the application directly with Python.
    
    Usage:
        python main.py
        
    Or with uvicorn for development:
        uvicorn main:app --reload --host 0.0.0.0 --port 8000
    """
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
 
