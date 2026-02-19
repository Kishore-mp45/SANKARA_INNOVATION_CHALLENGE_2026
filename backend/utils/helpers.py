"""
PatientPath AI - Helper Functions
=================================
Utility functions for common operations.
"""

from datetime import datetime
from typing import Tuple


def calculate_pagination(total: int, page: int, page_size: int) -> Tuple[int, int, int]:
    """
    Calculate pagination values.
    
    Args:
        total: Total number of items
        page: Current page number (1-based)
        page_size: Items per page
        
    Returns:
        Tuple of (offset, limit, total_pages)
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 10
        
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size
    
    return offset, page_size, total_pages


def calculate_dwell_time_minutes(entry_time: datetime, exit_time: datetime = None) -> float:
    """
    Calculate dwell time in minutes.
    
    Args:
        entry_time: When the patient entered
        exit_time: When the patient exited (uses current time if None)
        
    Returns:
        Dwell time in minutes
    """
    if exit_time is None:
        exit_time = datetime.utcnow()
    
    delta = exit_time - entry_time
    return round(delta.total_seconds() / 60, 2)


def format_datetime(dt: datetime) -> str:
    """Format datetime to ISO string."""
    if dt is None:
        return None
    return dt.isoformat()


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string."""
    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
