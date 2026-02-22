"""
PatientPath AI - Logger Utility
===============================
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def setup_logging():
    """Configure application logging."""
    from config import settings
    
    handlers = [logging.StreamHandler()]
    
    # Only add file handler if we can write to the log file
    try:
        file_handler = logging.FileHandler(settings.LOG_FILE, mode='a')
        handlers.append(file_handler)
    except (OSError, PermissionError):
        pass  # Skip file logging in production/read-only environments
    
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=settings.LOG_FORMAT,
        handlers=handlers
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
