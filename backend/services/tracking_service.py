"""
PatientPath AI - Tracking Service
==================================
Core logic for QR-first movement tracking with Re-ID fallback.
Handles zone validation, confidence routing, and audit logging.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

IST = timezone(timedelta(hours=5, minutes=30))

def _now_ist():
    """Return current IST time as naive datetime (for DB storage)."""
    return datetime.now(IST).replace(tzinfo=None)
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings
from models.patient import Patient, PatientStatus
from models.movement_event import MovementEvent, SourceType
from models.staff_confirmation import StaffConfirmation, ConfirmationStatus
from models.zone import Zone
from models.user import User
from utils.logger import get_logger

logger = get_logger(__name__)

# Department sequence and allowed transitions
DEPARTMENT_SEQUENCE = [
    "registration", "vision_lab", "dilation_hall",
    "diagnostics", "consultation", "pharmacy", "billing_insurance"
]

ALLOWED_TRANSITIONS = {
    "entrance": ["registration"],
    "registration": ["vision_lab"],
    "vision_lab": ["dilation_hall"],
    "dilation_hall": ["diagnostics"],
    "diagnostics": ["consultation"],
    "consultation": ["pharmacy"],
    "pharmacy": ["billing_insurance"],
    "billing_insurance": ["exit"],
}


def get_next_valid_zones(current_zone: Optional[str]) -> list:
    """Return list of valid next zones for a given current zone."""
    if settings.ENABLE_FREE_MOVE:
        return [z for z in DEPARTMENT_SEQUENCE if z != current_zone] + ["exit"]
    if not current_zone:
        return ["registration"]
    return ALLOWED_TRANSITIONS.get(current_zone, [])


def _is_valid_zone(zone_name: str) -> bool:
    """Check if zone_name is a recognized department or 'exit'."""
    return zone_name in DEPARTMENT_SEQUENCE or zone_name == "exit"


def is_valid_transition(from_zone: Optional[str], to_zone: str) -> bool:
    """Check if a zone transition is valid.
    In free-move mode: any zone to any different zone is valid.
    In sequential mode: only forward transitions allowed."""
    if settings.ENABLE_FREE_MOVE:
        if not from_zone:
            return _is_valid_zone(to_zone)
        if from_zone == to_zone:
            return False
        return _is_valid_zone(to_zone)
    # Sequential mode
    if not from_zone:
        return to_zone == "registration"
    valid = ALLOWED_TRANSITIONS.get(from_zone, [])
    return to_zone in valid


def is_valid_qr_transition(from_zone: Optional[str], to_zone: str) -> bool:
    """Check if a QR transition is valid. QR always allows free move."""
    if not from_zone:
        return _is_valid_zone(to_zone)
    if from_zone == to_zone:
        return False
    return _is_valid_zone(to_zone)


def _check_duplicate_event(db: Session, patient_id: int, from_zone: Optional[str], to_zone: str) -> bool:
    """Return True if the exact same move (same from_zone -> to_zone) already exists within the duplicate window."""
    window_start = _now_ist() - timedelta(seconds=settings.DUPLICATE_WINDOW_SECS)
    query = db.query(MovementEvent).filter(
        MovementEvent.patient_id == patient_id,
        MovementEvent.to_zone == to_zone,
        MovementEvent.event_timestamp >= window_start,
        MovementEvent.source_type.in_([SourceType.QR, SourceType.REID_AUTO, SourceType.MANUAL_CONFIRMED])
    )
    if from_zone:
        query = query.filter(MovementEvent.from_zone == from_zone)
    return query.first() is not None


def _update_zone_occupancy(db: Session, from_zone: Optional[str], to_zone: str):
    """Adjust zone occupancy counts."""
    if from_zone:
        old = db.query(Zone).filter(Zone.zone_name == from_zone).first()
        if old and old.current_occupancy > 0:
            old.current_occupancy -= 1

    if to_zone != "exit":
        new = db.query(Zone).filter(Zone.zone_name == to_zone).first()
        if new:
            new.current_occupancy += 1


def _create_movement_event(
    db: Session,
    patient: Patient,
    source_type: SourceType,
    from_zone: Optional[str],
    to_zone: str,
    confidence: Optional[float] = None,
    actor: str = "system",
    notes: Optional[str] = None
) -> MovementEvent:
    """Create an immutable movement event record."""
    event = MovementEvent(
        patient_id=patient.id,
        tracking_id=patient.tracking_id,
        source_type=source_type,
        from_zone=from_zone,
        to_zone=to_zone,
        confidence=confidence,
        event_timestamp=_now_ist(),
        actor=actor,
        notes=notes
    )
    db.add(event)
    return event


def _move_patient(db: Session, patient: Patient, to_zone: str, method: str,
                  confidence: Optional[float] = None, source: str = "system"):
    """Update patient record to new zone."""
    old_zone = patient.current_zone
    patient.current_zone = to_zone
    patient.tracking_method = method
    patient.reid_confidence = confidence
    patient.needs_confirmation = False
    patient.updated_by_source = source
    patient.last_movement_time = _now_ist()
    patient.updated_at = _now_ist()

    if to_zone == "exit":
        patient.status = PatientStatus.EXITED
        patient.exit_time = _now_ist()
        # Remove patient's User account so they must re-register next visit
        _remove_patient_user(db, patient.tracking_id)

    _update_zone_occupancy(db, old_zone, to_zone)


def _remove_patient_user(db: Session, tracking_id: str):
    """Delete the patient's User record after journey completion."""
    try:
        user = db.query(User).filter(
            User.generated_id == tracking_id, User.role == "patient"
        ).first()
        if user:
            db.delete(user)
            logger.info(f"Patient user account removed: {tracking_id}")
    except Exception as e:
        logger.warning(f"Failed to remove patient user {tracking_id}: {e}")


# ============================================================================
# QR SCAN HANDLER
# ============================================================================

def handle_qr_scan(
    db: Session,
    qr_token: str,
    zone_name: str,
    scanned_by: Optional[str] = None
) -> dict:
    """
    Process a QR code scan. This is the PRIMARY tracking method.
    QR always takes precedence over Re-ID.
    """
    # Find patient by QR token
    patient = db.query(Patient).filter(Patient.qr_token == qr_token).first()
    if not patient:
        return {"success": False, "message": "Invalid QR code — patient not found"}

    if not patient.is_active:
        return {"success": False, "message": "Patient has already exited"}

    # Validate transition (QR allows forward + backward moves)
    if not is_valid_qr_transition(patient.current_zone, zone_name):
        return {
            "success": False,
            "message": f"Invalid move: patient is already at '{patient.current_zone}' or '{zone_name}' is not a valid department"
        }

    from_zone = patient.current_zone

    # Check duplicate (same from -> to within window)
    if _check_duplicate_event(db, patient.id, from_zone, zone_name):
        return {"success": False, "message": "Duplicate scan — movement already recorded for this zone"}

    # Cancel any pending Re-ID confirmations for this patient (QR takes precedence)
    pending = db.query(StaffConfirmation).filter(
        StaffConfirmation.patient_id == patient.id,
        StaffConfirmation.status == ConfirmationStatus.PENDING
    ).all()
    for p in pending:
        p.status = ConfirmationStatus.REJECTED
        p.reviewed_at = _now_ist()
        p.reviewed_by = "System (QR Override)"
        p.rejection_reason = "QR scan received — overrides pending Re-ID"

    # Move patient
    _move_patient(db, patient, zone_name, "qr", source=scanned_by or "QR Scanner")

    # Create audit event
    event = _create_movement_event(
        db, patient, SourceType.QR, from_zone, zone_name,
        actor=scanned_by or "QR Scanner"
    )

    db.commit()
    db.refresh(event)

    logger.info(f"QR scan: {patient.tracking_id} moved {from_zone} -> {zone_name}")

    return {
        "success": True,
        "message": f"Patient moved to {zone_name} via QR scan",
        "patient_id": patient.id,
        "tracking_id": patient.tracking_id,
        "from_zone": from_zone,
        "to_zone": zone_name,
        "tracking_method": "qr",
        "event_id": event.id
    }


# ============================================================================
# RE-ID FALLBACK HANDLER
# ============================================================================

def handle_reid_event(
    db: Session,
    zone_name: str,
    candidate_patient_id: Optional[int],
    candidate_tracking_id: Optional[str],
    confidence: float,
    embedding_id: Optional[str] = None
) -> dict:
    """
    Process a Re-ID detection event. Only used as fallback when QR is missing.
    Routes based on confidence thresholds:
    - >= AUTO_THRESHOLD: auto-move
    - >= REVIEW_THRESHOLD: create pending staff confirmation
    - < REVIEW_THRESHOLD: log as unresolved, no movement
    """
    # Resolve patient
    patient = None
    if candidate_patient_id:
        patient = db.query(Patient).filter(Patient.id == candidate_patient_id).first()
    if not patient and candidate_tracking_id:
        patient = db.query(Patient).filter(Patient.tracking_id == candidate_tracking_id).first()

    if not patient:
        return {
            "success": False, "message": "No matching patient found",
            "action_taken": "unresolved", "confidence": confidence
        }

    if not patient.is_active:
        return {
            "success": False, "message": "Patient already exited",
            "action_taken": "unresolved", "confidence": confidence
        }

    # Check if QR scan already handled this within the priority window
    qr_window_start = _now_ist() - timedelta(seconds=settings.QR_PRIORITY_WINDOW_SECS)
    qr_exists = db.query(MovementEvent).filter(
        MovementEvent.patient_id == patient.id,
        MovementEvent.to_zone == zone_name,
        MovementEvent.source_type == SourceType.QR,
        MovementEvent.event_timestamp >= qr_window_start
    ).first()
    if qr_exists:
        return {
            "success": True, "message": "QR scan already recorded for this zone",
            "action_taken": "qr_priority", "confidence": confidence,
            "patient_id": patient.id, "tracking_id": patient.tracking_id
        }

    # Validate transition
    if not is_valid_transition(patient.current_zone, zone_name):
        reason = f"patient is already at '{zone_name}'" if patient.current_zone == zone_name else f"'{zone_name}' is not a valid zone"
        return {
            "success": False,
            "message": f"Invalid transition: {reason}",
            "action_taken": "invalid_transition", "confidence": confidence
        }

    from_zone = patient.current_zone

    # Check duplicate (same from -> to within window)
    if _check_duplicate_event(db, patient.id, from_zone, zone_name):
        return {
            "success": True, "message": "Movement already recorded",
            "action_taken": "duplicate", "confidence": confidence,
            "patient_id": patient.id, "tracking_id": patient.tracking_id
        }

    # Route based on confidence
    embed_note = f" [embedding:{embedding_id}]" if embedding_id else ""

    if confidence >= settings.REID_AUTO_THRESHOLD:
        # HIGH confidence — auto-move
        _move_patient(db, patient, zone_name, "reid_auto", confidence, "Re-ID System")
        event = _create_movement_event(
            db, patient, SourceType.REID_AUTO, from_zone, zone_name,
            confidence=confidence, actor="Re-ID System",
            notes=f"Auto-moved (conf={confidence:.2f}){embed_note}" if embedding_id else None
        )
        db.commit()
        db.refresh(event)

        logger.info(f"Re-ID auto-move: {patient.tracking_id} -> {zone_name} (conf={confidence:.2f})")
        return {
            "success": True,
            "message": f"Auto-moved to {zone_name} (confidence: {confidence:.2f})",
            "action_taken": "auto_moved",
            "patient_id": patient.id, "tracking_id": patient.tracking_id,
            "confidence": confidence, "event_id": event.id
        }

    elif confidence >= settings.REID_REVIEW_THRESHOLD:
        # MEDIUM confidence — pending staff review
        event = _create_movement_event(
            db, patient, SourceType.PENDING_REVIEW, from_zone, zone_name,
            confidence=confidence, actor="Re-ID System",
            notes=f"Awaiting staff confirmation{embed_note}"
        )

        confirmation = StaffConfirmation(
            patient_id=patient.id,
            tracking_id=patient.tracking_id,
            candidate_zone=zone_name,
            from_zone=from_zone,
            confidence=confidence,
            status=ConfirmationStatus.PENDING,
            created_at=_now_ist(),
            movement_event_id=None  # Will be set after commit
        )
        db.add(confirmation)

        # Mark patient as needing confirmation
        patient.needs_confirmation = True
        patient.reid_confidence = confidence
        patient.updated_by_source = "Re-ID System"

        db.commit()
        db.refresh(event)
        db.refresh(confirmation)

        # Link event to confirmation
        confirmation.movement_event_id = event.id
        db.commit()

        logger.info(f"Re-ID pending: {patient.tracking_id} -> {zone_name} (conf={confidence:.2f})")
        return {
            "success": True,
            "message": f"Pending staff review (confidence: {confidence:.2f})",
            "action_taken": "pending_review",
            "patient_id": patient.id, "tracking_id": patient.tracking_id,
            "confidence": confidence, "event_id": event.id,
            "confirmation_id": confirmation.id
        }

    else:
        # LOW confidence — unresolved, no movement
        event = _create_movement_event(
            db, patient, SourceType.UNRESOLVED, from_zone, zone_name,
            confidence=confidence, actor="Re-ID System",
            notes=f"Low confidence ({confidence:.2f}) — no auto-move, manual handling required{embed_note}"
        )
        db.commit()
        db.refresh(event)

        logger.info(f"Re-ID unresolved: {patient.tracking_id} conf={confidence:.2f} (below threshold)")
        return {
            "success": True,
            "message": f"Low confidence ({confidence:.2f}) — logged for manual review only",
            "action_taken": "unresolved",
            "patient_id": patient.id, "tracking_id": patient.tracking_id,
            "confidence": confidence, "event_id": event.id
        }


# ============================================================================
# STAFF CONFIRMATION HANDLER
# ============================================================================

def handle_staff_confirmation(
    db: Session,
    confirmation_id: int,
    action: str,
    staff_id: str,
    reason: Optional[str] = None
) -> dict:
    """
    Staff approves or rejects a pending Re-ID match.
    """
    confirmation = db.query(StaffConfirmation).filter(
        StaffConfirmation.id == confirmation_id
    ).first()

    if not confirmation:
        return {"success": False, "message": "Confirmation item not found"}

    if confirmation.status != ConfirmationStatus.PENDING:
        return {"success": False, "message": f"Already {confirmation.status.value}"}

    patient = db.query(Patient).filter(Patient.id == confirmation.patient_id).first()
    if not patient:
        return {"success": False, "message": "Patient not found"}

    now = _now_ist()

    if action == "approve":
        # Validate transition is still valid
        if not is_valid_transition(patient.current_zone, confirmation.candidate_zone):
            return {
                "success": False,
                "message": f"Transition no longer valid — patient may have moved via QR"
            }

        # Move patient
        from_zone = patient.current_zone
        _move_patient(db, patient, confirmation.candidate_zone, "manual_confirmed",
                      confirmation.confidence, staff_id)

        # Create confirmed movement event
        event = _create_movement_event(
            db, patient, SourceType.MANUAL_CONFIRMED, from_zone,
            confirmation.candidate_zone, confidence=confirmation.confidence,
            actor=staff_id, notes=f"Staff approved Re-ID match"
        )

        confirmation.status = ConfirmationStatus.APPROVED
        confirmation.reviewed_at = now
        confirmation.reviewed_by = staff_id

        db.commit()
        db.refresh(event)

        logger.info(f"Staff approved: {patient.tracking_id} -> {confirmation.candidate_zone} by {staff_id}")
        return {
            "success": True,
            "message": f"Approved — patient moved to {confirmation.candidate_zone}",
            "confirmation_id": confirmation.id,
            "action": "approve",
            "patient_id": patient.id,
            "tracking_id": patient.tracking_id,
            "to_zone": confirmation.candidate_zone
        }

    elif action == "reject":
        # Create rejected event
        _create_movement_event(
            db, patient, SourceType.REJECTED, confirmation.from_zone,
            confirmation.candidate_zone, confidence=confirmation.confidence,
            actor=staff_id, notes=reason or "Staff rejected Re-ID match"
        )

        confirmation.status = ConfirmationStatus.REJECTED
        confirmation.reviewed_at = now
        confirmation.reviewed_by = staff_id
        confirmation.rejection_reason = reason

        # Clear patient's pending flag
        patient.needs_confirmation = False
        patient.reid_confidence = None
        patient.updated_by_source = staff_id

        db.commit()

        logger.info(f"Staff rejected: {patient.tracking_id} -> {confirmation.candidate_zone} by {staff_id}")
        return {
            "success": True,
            "message": "Rejected — no movement applied",
            "confirmation_id": confirmation.id,
            "action": "reject",
            "patient_id": patient.id,
            "tracking_id": patient.tracking_id,
            "to_zone": None
        }

    return {"success": False, "message": "Invalid action"}


# ============================================================================
# QUERY HELPERS
# ============================================================================

def get_pending_confirmations(db: Session) -> list:
    """Get all pending staff confirmations with patient names."""
    confirmations = db.query(StaffConfirmation).filter(
        StaffConfirmation.status == ConfirmationStatus.PENDING
    ).order_by(StaffConfirmation.created_at.desc()).all()

    results = []
    for c in confirmations:
        patient = db.query(Patient).filter(Patient.id == c.patient_id).first()
        item = c.to_dict()
        item["patient_name"] = patient.name if patient else "Unknown"
        results.append(item)
    return results


def get_movement_history(db: Session, patient_id: Optional[int] = None,
                         tracking_id: Optional[str] = None, limit: int = 50) -> list:
    """Get movement event history for a patient or all patients."""
    query = db.query(MovementEvent)
    if patient_id:
        query = query.filter(MovementEvent.patient_id == patient_id)
    elif tracking_id:
        query = query.filter(MovementEvent.tracking_id == tracking_id)
    return [e.to_dict() for e in query.order_by(MovementEvent.event_timestamp.desc()).limit(limit).all()]


def get_tracking_stats(db: Session) -> dict:
    """Get summary stats for tracking methods."""
    from sqlalchemy import func
    total = db.query(MovementEvent).count()
    by_source = db.query(
        MovementEvent.source_type, func.count(MovementEvent.id)
    ).group_by(MovementEvent.source_type).all()

    pending_count = db.query(StaffConfirmation).filter(
        StaffConfirmation.status == ConfirmationStatus.PENDING
    ).count()

    return {
        "total_events": total,
        "by_source": {s.value: c for s, c in by_source},
        "pending_confirmations": pending_count,
        "thresholds": {
            "auto": settings.REID_AUTO_THRESHOLD,
            "review": settings.REID_REVIEW_THRESHOLD
        }
    }
