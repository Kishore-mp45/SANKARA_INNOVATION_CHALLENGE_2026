"""
PatientPath AI - Database Connection
====================================
Supports MySQL and SQLite via environment-driven configuration.
""" 

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import os
import sys

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings


# Build engine with appropriate settings for MySQL vs SQLite
if settings.IS_SQLITE:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DATABASE_ECHO
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # MySQL engine with connection pooling
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        pool_pre_ping=True,
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
    from models.escalation import Escalation
    from models.prescription import Prescription
    from models.user import User
    from models.notification import Notification

    Base.metadata.create_all(bind=engine)
