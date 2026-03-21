"""
PatientPath AI - Tracking Schemas
==================================
Request/response schemas for QR scanning, Re-ID events, and staff confirmations.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SourceType(str, Enum):
    QR = "qr"
    REID_AUTO = "reid_auto"
    PENDING_REVIEW = "pending_review"
    MANUAL_CONFIRMED = "manual_confirmed"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"


# === QR Scanning ===

class QRScanRequest(BaseModel):
    """Staff scans a patient's QR code at a zone."""
    qr_token: str = Field(..., description="UUID from the patient's QR code")
    zone_name: str = Field(..., description="Zone where QR was scanned")
    scanned_by: Optional[str] = Field(None, description="Staff user ID who scanned")


class QRScanResponse(BaseModel):
    success: bool
    message: str
    patient_id: Optional[int] = None
    tracking_id: Optional[str] = None
    from_zone: Optional[str] = None
    to_zone: Optional[str] = None
    tracking_method: str = "qr"


# === Re-ID Events ===

class ReIDEventRequest(BaseModel):
    """Re-ID system submits a candidate match."""
    zone_name: str = Field(..., description="Zone where person was detected")
    candidate_tracking_id: Optional[str] = Field(None, description="Best-match patient tracking ID")
    candidate_patient_id: Optional[int] = Field(None, description="Best-match patient DB ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence score")
    embedding_id: Optional[str] = Field(None, description="Reference to stored embedding")


class ReIDEventResponse(BaseModel):
    success: bool
    message: str
    action_taken: str  # auto_moved, pending_review, unresolved, duplicate, invalid_transition
    patient_id: Optional[int] = None
    tracking_id: Optional[str] = None
    confidence: float
    event_id: Optional[int] = None
    confirmation_id: Optional[int] = None


# === Staff Confirmation ===

class ConfirmationAction(BaseModel):
    """Staff approves or rejects a pending Re-ID match."""
    confirmation_id: int
    action: str = Field(..., pattern="^(approve|reject)$")
    staff_id: str = Field(..., description="Staff user ID")
    reason: Optional[str] = Field(None, description="Rejection reason")


class ConfirmationResponse(BaseModel):
    success: bool
    message: str
    confirmation_id: int
    action: str
    patient_id: Optional[int] = None
    tracking_id: Optional[str] = None
    to_zone: Optional[str] = None


class PendingConfirmationItem(BaseModel):
    id: int
    patient_id: int
    tracking_id: str
    patient_name: Optional[str] = None
    candidate_zone: str
    from_zone: Optional[str] = None
    confidence: float
    created_at: datetime
    status: str

    model_config = {"from_attributes": True}


# === Movement Event (audit) ===

class MovementEventResponse(BaseModel):
    event_id: int
    patient_id: int
    tracking_id: str
    source_type: str
    from_zone: Optional[str] = None
    to_zone: str
    confidence: Optional[float] = None
    event_timestamp: datetime
    actor: str
    notes: Optional[str] = None

    model_config = {"from_attributes": True}
