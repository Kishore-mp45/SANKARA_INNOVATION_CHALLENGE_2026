"""
PatientPath AI - Database Connection
====================================
MySQL database connection with SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import os
import sys

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings


# Create MySQL engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,           # Number of persistent connections
    max_overflow=20,        # Extra connections allowed beyond pool_size
    pool_recycle=3600,      # Recycle connections after 1 hour (avoid MySQL timeout)
    pool_pre_ping=True,     # Verify connections are alive before using them
    echo=settings.DATABASE_ECHO
)


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for models
Base = declarative_base()


def get_db():
    """
    FastAPI dependency for database sessions.
    Yields a database session and ensures proper cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    Use this for non-FastAPI contexts.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.
    Safe to call multiple times.
    """
    # Import all models to ensure they are registered
    from models.patient import Patient
    from models.zone import Zone
    from models.occupancy import OccupancyLog
    from models.alert import Alert
    from models.metric import Metric
    
    Base.metadata.create_all(bind=engine)
