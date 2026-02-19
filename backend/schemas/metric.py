"""
PatientPath AI - Metric Schemas
===============================
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


class MetricResponse(BaseModel):
    """Response for a single metric record."""
    id: int
    timestamp: datetime
    metric_type: str
    zone_name: Optional[str]
    avg_dwell_time: Optional[float]
    min_dwell_time: Optional[float]
    max_dwell_time: Optional[float]
    entry_rate: Optional[float]
    exit_rate: Optional[float]
    throughput: Optional[float]
    total_entries: Optional[int]
    total_exits: Optional[int]
    peak_occupancy: Optional[int]
    avg_occupancy: Optional[float]

    model_config = {"from_attributes": True}


class MetricLiveResponse(BaseModel):
    """Live/real-time metrics response."""
    timestamp: datetime
    total_occupancy: int
    total_capacity: int
    occupancy_rate: float
    active_patients: int
    zones: List[Dict[str, Any]]
    avg_dwell_time_minutes: float


class MetricHistoryResponse(BaseModel):
    """Historical metrics response."""
    items: List[MetricResponse]
    total: int
    period: str  # e.g., "24h", "7d"
    start_time: datetime
    end_time: datetime


class DashboardSummary(BaseModel):
    """Dashboard summary response."""
    timestamp: datetime
    total_patients: int
    active_patients: int
    total_zones: int
    total_occupancy: int
    total_capacity: int
    occupancy_rate: float
    avg_dwell_time_minutes: float
    zones: List[Dict[str, Any]]
