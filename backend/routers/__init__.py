"""
PatientPath AI - Routers Package
================================
API route handlers for all endpoints.
"""

from .system import router as system_router
from .patients import router as patients_router
from .zones import router as zones_router
from .occupancy import router as occupancy_router
from .alerts import router as alerts_router
from .metrics import router as metrics_router
from .websocket import router as websocket_router
from .export import router as export_router

__all__ = [
    "system_router",
    "patients_router",
    "zones_router",
    "occupancy_router",
    "alerts_router",
    "metrics_router",
    "websocket_router",
    "export_router"
]
