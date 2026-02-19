"""
PatientPath AI - Configuration
==============================
Application settings and configuration management.
"""

import os
from typing import List


class Settings:
    """Application settings and configuration."""
    
    # Application Info
    APP_NAME: str = "PatientPath AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Healthcare Analytics Platform - Real-time patient flow tracking and analytics"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./patientpath.db")
    DATABASE_ECHO: bool = DEBUG
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"  # Allow all for development
    ]
    
    # Alert Thresholds
    CAPACITY_WARNING_THRESHOLD: float = 0.8
    CAPACITY_CRITICAL_THRESHOLD: float = 0.95
    LONG_WAIT_THRESHOLD_MINUTES: int = 45
    
    # Cache Configuration
    CACHE_DEFAULT_TTL: int = 300  # 5 minutes
    CACHE_METRICS_TTL: int = 60   # 1 minute for real-time metrics
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # WebSocket Configuration
    WEBSOCKET_HEARTBEAT: int = 30 # seconds
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "patientpath.log"


settings = Settings()
