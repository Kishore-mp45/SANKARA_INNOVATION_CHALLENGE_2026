"""
PatientPath AI - Occupancy Schemas
==================================
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class OccupancyUpdate(BaseModel):
    """Schema for updating zone occupancy from CV detection."""
    zone_name: str = Field(..., max_length=50)
    people_count: int = Field(..., ge=0)
    entry_count: int = Field(0, ge=0)
    exit_count: int = Field(0, ge=0)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    source: str = "cv_detection"
    unique_ids: Optional[List[int]] = Field(None, description="List of unique person IDs")


class OccupancyBatchUpdate(BaseModel):
    """Schema for batch updating multiple zones."""
    updates: List[OccupancyUpdate]


class OccupancyLogResponse(BaseModel):
    """Response for a single occupancy log entry."""
    id: int
    timestamp: datetime
    people_count: int
    previous_count: Optional[int]
    zone_name: str
    entry_count: int
    exit_count: int
    confidence_score: Optional[float]
    source: str
    unique_ids: Optional[List[int]] = Field(None)

    model_config = {"from_attributes": True}


class OccupancyCurrentResponse(BaseModel):
    """Response for current occupancy status."""
    zone_name: str
    current_count: int
    capacity_limit: int
    occupancy_rate: float
    status: str  # normal, warning, critical
    last_updated: datetime


class OccupancyHistoryResponse(BaseModel):
    """Response for occupancy history."""
    zone_name: str
    logs: List[OccupancyLogResponse]
    total: int


# Aliases for compatibility
OccupancyCreate = OccupancyUpdate
OccupancyResponse = OccupancyLogResponse
OccupancyListResponse = OccupancyHistoryResponse
