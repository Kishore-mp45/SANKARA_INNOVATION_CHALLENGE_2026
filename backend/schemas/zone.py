"""Zone Schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List


class ZoneCreate(BaseModel):
    zone_name: str = Field(..., max_length=50)
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    capacity_limit: int = Field(50, ge=1)
    zone_type: Optional[str] = None
    floor_number: Optional[int] = None
    building: Optional[str] = None


class ZoneUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    capacity_limit: Optional[int] = None
    current_occupancy: Optional[int] = None
    zone_type: Optional[str] = None
    is_active: Optional[bool] = None


class ZoneResponse(BaseModel):
    id: int
    zone_name: str
    display_name: Optional[str]
    description: Optional[str]
    capacity_limit: int
    current_occupancy: int
    occupancy_rate: float
    zone_type: Optional[str]
    floor_number: Optional[int]
    building: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


class ZoneListResponse(BaseModel):
    """Response for paginated zone list."""
    items: List[ZoneResponse]
    total: int


class ZoneSummary(BaseModel):
    """Summary of zone statistics."""
    total_zones: int
    active_zones: int
    total_capacity: int
    total_occupancy: int
    occupancy_rate: float


class ZoneOccupancyUpdate(BaseModel):
    """Update zone occupancy directly."""
    current_occupancy: int = Field(..., ge=0)
