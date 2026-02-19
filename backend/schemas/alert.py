"""
PatientPath AI - Alert Schemas
==============================
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class AlertType(str, Enum):
    CAPACITY_WARNING = "capacity_warning"
    CAPACITY_CRITICAL = "capacity_critical"
    LONG_WAIT_TIME = "long_wait_time"
    UNUSUAL_ACTIVITY = "unusual_activity"
    SYSTEM_ERROR = "system_error"
    CUSTOM = "custom"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCreate(BaseModel):
    """Schema for creating a new alert."""
    alert_type: AlertType
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = Field(..., min_length=1)
    zone_name: Optional[str] = None
    patient_id: Optional[int] = None


class AlertResponse(BaseModel):
    """Response for a single alert."""
    id: int
    timestamp: datetime
    alert_type: str
    severity: str
    message: str
    zone_name: Optional[str]
    is_active: bool
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """Response for paginated alert list."""
    items: List[AlertResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert."""
    acknowledged_by: Optional[str] = None


class AlertResolve(BaseModel):
    """Schema for resolving an alert."""
    resolution_notes: Optional[str] = None


class AlertSummary(BaseModel):
    """Summary of alert statistics."""
    total_alerts: int
    active_alerts: int
    acknowledged_alerts: int
    unacknowledged_alerts: int
    by_severity: dict
    by_type: dict
