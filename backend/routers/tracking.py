"""
PatientPath AI - Tracking Router
==================================
API endpoints for QR scanning, Re-ID events, staff confirmations, and movement audit.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models.patient import Patient
from schemas.tracking import (
    QRScanRequest, QRScanResponse,
    ReIDEventRequest, ReIDEventResponse,
    ConfirmationAction, ConfirmationResponse,
    PendingConfirmationItem, MovementEventResponse
)
from services.tracking_service import (
    handle_qr_scan, handle_reid_event, handle_staff_confirmation,
    get_pending_confirmations, get_movement_history, get_tracking_stats,
    DEPARTMENT_SEQUENCE, ALLOWED_TRANSITIONS
)
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/tracking", tags=["Tracking"])


# ============================================================================
# QR SCANNING
# ============================================================================

@router.post("/qr-scan", summary="Process QR Code Scan")
async def qr_scan(data: QRScanRequest, db: Session = Depends(get_db)):
    """
    Staff scans patient QR code at a zone entrance.
    Primary tracking method — takes precedence over Re-ID.
    """
    result = handle_qr_scan(db, data.qr_token, data.zone_name, data.scanned_by)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/qr-info/{qr_token}", summary="Get Patient Info from QR Token")
async def get_qr_info(qr_token: str, db: Session = Depends(get_db)):
    """Look up patient by QR token (for scanner preview)."""
    patient = db.query(Patient).filter(Patient.qr_token == qr_token).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found for this QR code")
    return {
        "patient_id": patient.id,
        "tracking_id": patient.tracking_id,
        "name": patient.name,
        "current_zone": patient.current_zone,
        "status": patient.status.value if patient.status else None,
        "tracking_method": patient.tracking_method,
        "needs_confirmation": patient.needs_confirmation
    }


# ============================================================================
# RE-ID FALLBACK
# ============================================================================

@router.post("/reid-event", summary="Submit Re-ID Detection Event")
async def reid_event(data: ReIDEventRequest, db: Session = Depends(get_db)):
    """
    Re-ID system submits a candidate match.
    Only triggers fallback if no QR scan within event window.
    Routes based on confidence thresholds.
    """
    result = handle_reid_event(
        db, data.zone_name, data.candidate_patient_id,
        data.candidate_tracking_id, data.confidence, data.embedding_id
    )
    return result


# ============================================================================
# STAFF CONFIRMATION QUEUE
# ============================================================================

@router.get("/confirmations/pending", summary="Get Pending Confirmations")
async def list_pending_confirmations(db: Session = Depends(get_db)):
    """Get all pending Re-ID matches awaiting staff review."""
    return get_pending_confirmations(db)


@router.post("/confirmations/action", summary="Approve or Reject Confirmation")
async def process_confirmation(data: ConfirmationAction, db: Session = Depends(get_db)):
    """Staff approves or rejects a pending Re-ID match."""
    result = handle_staff_confirmation(
        db, data.confirmation_id, data.action, data.staff_id, data.reason
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ============================================================================
# MOVEMENT AUDIT
# ============================================================================

@router.get("/events", summary="Get Movement Events")
async def list_movement_events(
    patient_id: Optional[int] = Query(None),
    tracking_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get movement event audit trail."""
    return get_movement_history(db, patient_id, tracking_id, limit)


@router.get("/stats", summary="Get Tracking Statistics")
async def tracking_stats(db: Session = Depends(get_db)):
    """Get summary statistics for tracking methods and pending items."""
    return get_tracking_stats(db)


# ============================================================================
# DOMAIN INFO
# ============================================================================

@router.get("/department-sequence", summary="Get Department Sequence")
async def department_sequence():
    """Get the ordered department workflow sequence."""
    return {
        "sequence": DEPARTMENT_SEQUENCE,
        "transitions": ALLOWED_TRANSITIONS
    }
