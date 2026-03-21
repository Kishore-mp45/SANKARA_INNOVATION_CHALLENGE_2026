"""
PatientPath AI - Configuration
==============================
Environment-driven settings supporting MySQL and SQLite.
Reads from backend/.env file. No DATABASE_URL required.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load .env from backend directory
_backend_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_backend_dir, ".env"))


def _parse_bool(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() in ("true", "1", "yes")


def _build_database_url() -> str:
    """Build SQLAlchemy database URL from environment variables."""
    use_sqlite = _parse_bool(os.getenv("USE_SQLITE", "true"))

    if use_sqlite:
        db_path = os.path.join(_backend_dir, "patientpath.db")
        return f"sqlite:///{db_path}"

    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "root")
    db_name = os.getenv("DB_NAME", "patientpath")

    return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"


class Settings:
    """Application settings and configuration."""

    # Application Info
    APP_NAME: str = "PatientPath AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Healthcare Analytics Platform - Real-time patient flow tracking and analytics"
    DEBUG: bool = _parse_bool(os.getenv("DEBUG", "true"), default=True)

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ADMIN_PORT: int = 5000

    # Database Configuration (built from env vars, no DATABASE_URL required)
    DATABASE_URL: str = _build_database_url()
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

    # QR & Re-ID Tracking Thresholds
    REID_AUTO_THRESHOLD: float = float(os.getenv("REID_AUTO_THRESHOLD", "0.85"))
    REID_REVIEW_THRESHOLD: float = float(os.getenv("REID_REVIEW_THRESHOLD", "0.60"))
    QR_PRIORITY_WINDOW_SECS: int = int(os.getenv("QR_PRIORITY_WINDOW_SECS", "60"))
    REID_TRIGGER_DELAY_SECS: int = int(os.getenv("REID_TRIGGER_DELAY_SECS", "30"))
    DUPLICATE_WINDOW_SECS: int = int(os.getenv("DUPLICATE_WINDOW_SECS", "120"))
    REID_FPS_CAP: int = int(os.getenv("REID_FPS_CAP", "5"))
    REID_CHECK_INTERVAL_SECS: int = int(os.getenv("REID_CHECK_INTERVAL_SECS", "10"))

    # Free-move mode: allows movement to any zone (not just sequential next)
    ENABLE_FREE_MOVE: bool = _parse_bool(os.getenv("ENABLE_FREE_MOVE", "true"), default=True)


settings = Settings()
