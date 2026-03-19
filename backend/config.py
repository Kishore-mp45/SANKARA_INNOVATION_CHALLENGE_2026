"""
PatientPath AI - Configuration
==============================
Application settings and configuration management.
"""

import os
from typing import List


def _build_default_db_url():
    """Force SQLite for local development (no MySQL needed)."""
    db_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(db_dir, "patientpath.db")
    return f"sqlite:///{db_path}"


class Settings:
    """Application settings and configuration."""
    
    # Application Info
    APP_NAME: str = "PatientPath AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Healthcare Analytics Platform - Real-time patient flow tracking and analytics"
    DEBUG: bool = True
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # ❌ Remove MySQL usage completely
    
    # ✅ Force SQLite
    DATABASE_URL: str = _build_default_db_url()
    DATABASE_ECHO: bool = DEBUG
    
    @property
    def IS_SQLITE(self) -> bool:
        return True  # Always true
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]
    
    # Alert Thresholds
    CAPACITY_WARNING_THRESHOLD: float = 0.8
    CAPACITY_CRITICAL_THRESHOLD: float = 0.95
    LONG_WAIT_THRESHOLD_MINUTES: int = 45
    
    # Cache Configuration
    CACHE_DEFAULT_TTL: int = 300
    CACHE_METRICS_TTL: int = 60
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 500
    RATE_LIMIT_WINDOW: int = 60
    
    # WebSocket Configuration
    WEBSOCKET_HEARTBEAT: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "patientpath.log"


settings = Settings()