"""Patient Schemas"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class PatientStatus(str, Enum):
    ENTERED = "entered"
    WAITING = "waiting"
    IN_ROOM = "in_room"
    EXITED = "exited"


class PatientEnter(BaseModel):
    """Schema for patient entry."""
    name: Optional[str] = Field(None, max_length=100)
    tracking_id: str = Field(..., max_length=50)
    zone_name: str = Field(default="entrance")


class PatientExit(BaseModel):
    """Schema for patient exit."""
    tracking_id: str = Field(..., max_length=50)
    zone_name: Optional[str] = None


class PatientMovement(BaseModel):
    """Schema for patient zone movement."""
    tracking_id: str = Field(..., max_length=50)
    from_zone: str
    to_zone: str


class PatientCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    mobile: Optional[str] = Field(None, max_length=20)
    tracking_id: str = Field(..., max_length=50)
    status: PatientStatus = PatientStatus.ENTERED
    current_zone: Optional[str] = None


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[PatientStatus] = None
    current_zone: Optional[str] = None
    exit_time: Optional[datetime] = None


# Force reload for schema update 2026-02-13 22:32


class PatientStageUpdate(BaseModel):
    """Schema for manual patient stage update by staff."""
    tracking_id: str = Field(..., max_length=50)
    name: Optional[str] = None
    mobile: Optional[str] = None
    department: str
    action: str
    next_department: Optional[str] = None
    staff_id: Optional[str] = None


class PatientResponse(BaseModel):
    id: int
    name: Optional[str]
    mobile: Optional[str] = None
    tracking_id: str
    entry_time: datetime
    exit_time: Optional[datetime]
    status: str
    current_zone: Optional[str]
    is_active: Optional[bool] = None
    last_action: Optional[str] = None
    dwell_time_minutes: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    """Response for paginated patient list."""
    patients: List[PatientResponse]
    total: int
    active_count: Optional[int] = None
    page: int
    page_size: int
    total_pages: int
