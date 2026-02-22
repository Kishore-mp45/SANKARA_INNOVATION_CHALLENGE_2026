"""
PatientPath AI - Cache Manager
==============================
Simple in-memory caching with TTL support.
"""

from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import threading


class CacheManager:
    """Thread-safe in-memory cache with TTL support."""
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if datetime.now() < expires_at:
                    return value
                else:
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL (seconds)."""
        with self._lock:
            expires_at = datetime.now() + timedelta(seconds=ttl)
            self._cache[key] = (value, expires_at)
    
    def delete(self, key: str):
        """Delete value from cache."""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()


# Global cache instance
cache_manager = CacheManager()
