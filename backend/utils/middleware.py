"""
PatientPath AI - Middleware
===========================
Custom middleware for request processing.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import time
import uuid


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.4f}s"
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling uncaught errors."""
    
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={"error": "internal_server_error", "message": str(e)}
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(self, app, requests_per_window: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.requests = {}
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for static files and websocket
        path = request.url.path
        if path.endswith((".html", ".css", ".js", ".png", ".jpg", ".ico", ".svg", ".woff", ".woff2", ".ttf")) or path.startswith("/ws"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries
        window_start = current_time - self.window_seconds
        self.requests = {
            ip: times for ip, times in self.requests.items()
            if any(t > window_start for t in times)
        }
        
        # Check rate limit
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        recent_requests = [t for t in self.requests[client_ip] if t > window_start]
        
        if len(recent_requests) >= self.requests_per_window:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limit_exceeded", "message": "Too many requests"}
            )
        
        self.requests[client_ip] = recent_requests + [current_time]
        return await call_next(request)
