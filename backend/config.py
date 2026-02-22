"""
PatientPath AI - Configuration
==============================
Application settings and configuration management.
"""

import os
from typing import List


def _build_default_db_url():
    """Build default database URL. Uses MySQL locally, SQLite on cloud."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    # Check if USE_SQLITE is set (for cloud deployment without MySQL)
    if os.getenv("USE_SQLITE", "false").lower() == "true":
        db_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(db_dir, "patientpath.db")
        return f"sqlite:///{db_path}"
    # Default: MySQL for local development
    return (
        f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', 'root')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}"
        f"/{os.getenv('DB_NAME', 'hospital')}?charset=utf8mb4"
    )


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
    
    # MySQL Database Configuration (used locally)
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "root")
    DB_NAME: str = os.getenv("DB_NAME", "hospital")
    
    # Database URL - auto-detects MySQL (local) or SQLite (cloud)
    DATABASE_URL: str = _build_default_db_url()
    DATABASE_ECHO: bool = DEBUG
    
    @property
    def IS_SQLITE(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")
    
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
    RATE_LIMIT_REQUESTS: int = 500
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # WebSocket Configuration
    WEBSOCKET_HEARTBEAT: int = 30 # seconds
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "patientpath.log"


settings = Settings()
