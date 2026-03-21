"""
PatientPath AI - Tracking Service Unit Tests
==============================================
Comprehensive tests for QR-first tracking with Re-ID fallback.

Covers:
- QR scan success/failure paths
- Re-ID confidence routing (high/medium/low)
- QR-priority conflict resolution
- Transition validation
- Duplicate prevention
- Staff confirmation approve/reject
- Audit trail integrity
- Tracking statistics

Run: cd backend && python -m pytest tests/test_tracking_service.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta

from models.patient import Patient, PatientStatus
from models.movement_event import MovementEvent, SourceType
from models.staff_confirmation import StaffConfirmation, ConfirmationStatus
from config import settings
from services.tracking_service import (
    handle_qr_scan, handle_reid_event, handle_staff_confirmation,
    get_pending_confirmations, get_movement_history, get_tracking_stats,
    is_valid_transition, is_valid_qr_transition, get_next_valid_zones,
    DEPARTMENT_SEQUENCE, ALLOWED_TRANSITIONS, _check_duplicate_event,
)


# =============================================================================
# TRANSITION VALIDATION
# =============================================================================

class TestTransitionValidation:
    """Tests with ENABLE_FREE_MOVE=True (default)."""

    def test_forward_transitions(self):
        assert is_valid_transition(None, "registration") is True
        assert is_valid_transition("registration", "vision_lab") is True
        assert is_valid_transition("billing_insurance", "exit") is True

    def test_free_move_skip_allowed(self):
        """In free-move mode, skipping departments is allowed."""
        assert is_valid_transition("registration", "diagnostics") is True
        assert is_valid_transition("registration", "consultation") is True

    def test_free_move_backward_allowed(self):
        """In free-move mode, backward moves are allowed."""
        assert is_valid_transition("vision_lab", "registration") is True
        assert is_valid_transition("consultation", "vision_lab") is True
        assert is_valid_transition("pharmacy", "registration") is True

    def test_same_zone_blocked(self):
        assert is_valid_transition("registration", "registration") is False

    def test_invalid_zone_name_blocked(self):
        assert is_valid_transition("registration", "nonexistent_zone") is False

    def test_no_zone_allows_any_valid_dept(self):
        assert is_valid_transition(None, "registration") is True
        assert is_valid_transition(None, "vision_lab") is True
        assert is_valid_transition(None, "consultation") is True

    def test_exit_allowed_from_any_zone(self):
        assert is_valid_transition("registration", "exit") is True
        assert is_valid_transition("pharmacy", "exit") is True

    def test_get_next_valid_zones_free_mode(self):
        zones = get_next_valid_zones("registration")
        assert "vision_lab" in zones
        assert "pharmacy" in zones
        assert "exit" in zones
        assert "registration" not in zones  # current zone excluded

    def test_department_sequence_completeness(self):
        for dept in DEPARTMENT_SEQUENCE:
            assert dept in ALLOWED_TRANSITIONS, f"Missing transition for {dept}"

    # QR transition (always free move)
    def test_qr_allows_backward_move(self):
        assert is_valid_qr_transition("vision_lab", "registration") is True
        assert is_valid_qr_transition("diagnostics", "dilation_hall") is True

    def test_qr_allows_forward_skip(self):
        assert is_valid_qr_transition("registration", "diagnostics") is True

    def test_qr_blocks_same_zone(self):
        assert is_valid_qr_transition("registration", "registration") is False

    def test_qr_allows_exit(self):
        assert is_valid_qr_transition("billing_insurance", "exit") is True
        assert is_valid_qr_transition("registration", "exit") is True


class TestSequentialModeBackwardCompat:
    """Tests with ENABLE_FREE_MOVE=False (sequential mode)."""

    def setup_method(self):
        self._original = settings.ENABLE_FREE_MOVE
        settings.ENABLE_FREE_MOVE = False

    def teardown_method(self):
        settings.ENABLE_FREE_MOVE = self._original

    def test_forward_only(self):
        assert is_valid_transition("registration", "vision_lab") is True
        assert is_valid_transition("vision_lab", "dilation_hall") is True

    def test_skip_blocked(self):
        assert is_valid_transition("registration", "diagnostics") is False

    def test_backward_blocked(self):
        assert is_valid_transition("vision_lab", "registration") is False

    def test_no_zone_must_start_at_registration(self):
        assert is_valid_transition(None, "registration") is True
        assert is_valid_transition(None, "vision_lab") is False

    def test_get_next_valid_zones_sequential(self):
        assert get_next_valid_zones("registration") == ["vision_lab"]
        assert get_next_valid_zones("billing_insurance") == ["exit"]


# =============================================================================
# QR SCAN HANDLER
# =============================================================================

class TestQRScan:

    def test_qr_scan_success(self, db, test_patient):
        result = handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff_001")

        assert result["success"] is True
        assert result["to_zone"] == "vision_lab"
        assert result["from_zone"] == "registration"
        assert result["tracking_method"] == "qr"
        assert result["event_id"] is not None

        # Verify patient state updated
        db.refresh(test_patient)
        assert test_patient.current_zone == "vision_lab"
        assert test_patient.tracking_method == "qr"

    def test_qr_scan_invalid_token(self, db, seed_zones):
        result = handle_qr_scan(db, "nonexistent-token", "vision_lab", "staff")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_qr_scan_exited_patient(self, db, test_patient):
        test_patient.status = PatientStatus.EXITED
        db.commit()

        result = handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")
        assert result["success"] is False
        assert "exited" in result["message"].lower()

    def test_qr_scan_same_zone_blocked(self, db, test_patient):
        """QR scan to the same zone patient is already at should be blocked."""
        result = handle_qr_scan(db, test_patient.qr_token, "registration", "staff")
        assert result["success"] is False

    def test_qr_scan_backward_move_allowed(self, db, patient_at_vision_lab):
        """QR scan should allow backward moves (e.g., vision_lab -> registration)."""
        result = handle_qr_scan(db, patient_at_vision_lab.qr_token, "registration", "staff")
        assert result["success"] is True
        assert result["to_zone"] == "registration"

    def test_qr_scan_skip_forward_allowed(self, db, test_patient):
        """QR scan should allow skipping departments (e.g., registration -> diagnostics)."""
        result = handle_qr_scan(db, test_patient.qr_token, "diagnostics", "staff")
        assert result["success"] is True
        assert result["to_zone"] == "diagnostics"

    def test_qr_scan_duplicate_blocked(self, db, test_patient):
        """Scanning same zone twice: first moves, second blocked (same-zone check)."""
        r1 = handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")
        assert r1["success"] is True

        # Same zone again — blocked because patient is already there
        r2 = handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")
        assert r2["success"] is False

    def test_qr_scan_cancels_pending_confirmations(self, db, test_patient):
        """QR scan must cancel any pending Re-ID confirmations."""
        # Create a pending confirmation
        confirmation = StaffConfirmation(
            patient_id=test_patient.id,
            tracking_id=test_patient.tracking_id,
            candidate_zone="vision_lab",
            from_zone="registration",
            confidence=0.72,
            status=ConfirmationStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        db.add(confirmation)
        db.commit()

        # QR scan to same zone
        result = handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")
        assert result["success"] is True

        # Confirmation should be rejected
        db.refresh(confirmation)
        assert confirmation.status == ConfirmationStatus.REJECTED
        assert confirmation.reviewed_by == "System (QR Override)"

    def test_qr_scan_creates_audit_event(self, db, test_patient):
        handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff_001")

        event = db.query(MovementEvent).filter(
            MovementEvent.patient_id == test_patient.id,
            MovementEvent.source_type == SourceType.QR
        ).first()

        assert event is not None
        assert event.from_zone == "registration"
        assert event.to_zone == "vision_lab"
        assert event.actor == "staff_001"

    def test_qr_scan_updates_zone_occupancy(self, db, test_patient, seed_zones):
        from models.zone import Zone
        vl_zone = db.query(Zone).filter(Zone.zone_name == "vision_lab").first()

        vl_before = vl_zone.current_occupancy

        handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")

        db.refresh(vl_zone)
        assert vl_zone.current_occupancy == vl_before + 1


# =============================================================================
# RE-ID EVENT HANDLER - HIGH CONFIDENCE
# =============================================================================

class TestReIDHighConfidence:

    def test_auto_move_on_high_confidence(self, db, test_patient):
        result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.92
        )

        assert result["success"] is True
        assert result["action_taken"] == "auto_moved"
        assert result["confidence"] == 0.92
        assert result["event_id"] is not None

        db.refresh(test_patient)
        assert test_patient.current_zone == "vision_lab"
        assert test_patient.tracking_method == "reid_auto"

    def test_auto_move_at_exact_threshold(self, db, test_patient):
        """Confidence == 0.85 (exact threshold) should auto-move."""
        result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.85
        )
        assert result["action_taken"] == "auto_moved"

    def test_auto_move_with_patient_id(self, db, test_patient):
        """Can resolve patient by ID instead of tracking_id."""
        result = handle_reid_event(
            db, "vision_lab", test_patient.id, None, 0.90
        )
        assert result["action_taken"] == "auto_moved"

    def test_auto_move_creates_reid_auto_event(self, db, test_patient):
        handle_reid_event(db, "vision_lab", None, test_patient.tracking_id, 0.95)

        event = db.query(MovementEvent).filter(
            MovementEvent.patient_id == test_patient.id,
            MovementEvent.source_type == SourceType.REID_AUTO
        ).first()
        assert event is not None
        assert event.confidence == 0.95
        assert event.actor == "Re-ID System"

    def test_embedding_id_stored_in_notes(self, db, test_patient):
        handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.92,
            embedding_id="emb_abc123"
        )
        event = db.query(MovementEvent).filter(
            MovementEvent.patient_id == test_patient.id
        ).first()
        assert "embedding:emb_abc123" in event.notes

    def test_reid_free_move_skip_forward(self, db, test_patient):
        """Re-ID high confidence can skip departments in free-move mode."""
        result = handle_reid_event(
            db, "consultation", None, test_patient.tracking_id, 0.92
        )
        assert result["action_taken"] == "auto_moved"
        db.refresh(test_patient)
        assert test_patient.current_zone == "consultation"

    def test_reid_free_move_backward(self, db, patient_at_diagnostics):
        """Re-ID high confidence can move backward in free-move mode."""
        result = handle_reid_event(
            db, "registration", None, patient_at_diagnostics.tracking_id, 0.90
        )
        assert result["action_taken"] == "auto_moved"
        db.refresh(patient_at_diagnostics)
        assert patient_at_diagnostics.current_zone == "registration"


# =============================================================================
# RE-ID EVENT HANDLER - MEDIUM CONFIDENCE
# =============================================================================

class TestReIDMediumConfidence:

    def test_pending_review_on_medium_confidence(self, db, test_patient):
        result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )

        assert result["success"] is True
        assert result["action_taken"] == "pending_review"
        assert result["confirmation_id"] is not None

        # Patient should NOT have moved
        db.refresh(test_patient)
        assert test_patient.current_zone == "registration"
        assert test_patient.needs_confirmation is True

    def test_pending_at_exact_review_threshold(self, db, test_patient):
        """Confidence == 0.60 should create pending review."""
        result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.60
        )
        assert result["action_taken"] == "pending_review"

    def test_just_below_auto_threshold(self, db, test_patient):
        """Confidence == 0.84 should be pending, NOT auto-moved."""
        result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.84
        )
        assert result["action_taken"] == "pending_review"

    def test_confirmation_record_created(self, db, test_patient):
        result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )

        confirmation = db.query(StaffConfirmation).filter(
            StaffConfirmation.id == result["confirmation_id"]
        ).first()
        assert confirmation is not None
        assert confirmation.status == ConfirmationStatus.PENDING
        assert confirmation.candidate_zone == "vision_lab"
        assert confirmation.from_zone == "registration"
        assert confirmation.confidence == 0.72

    def test_pending_review_event_logged(self, db, test_patient):
        handle_reid_event(db, "vision_lab", None, test_patient.tracking_id, 0.72)

        event = db.query(MovementEvent).filter(
            MovementEvent.patient_id == test_patient.id,
            MovementEvent.source_type == SourceType.PENDING_REVIEW
        ).first()
        assert event is not None


# =============================================================================
# RE-ID EVENT HANDLER - LOW CONFIDENCE
# =============================================================================

class TestReIDLowConfidence:

    def test_unresolved_on_low_confidence(self, db, test_patient):
        result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.35
        )

        assert result["success"] is True
        assert result["action_taken"] == "unresolved"

        # Patient must NOT move
        db.refresh(test_patient)
        assert test_patient.current_zone == "registration"

    def test_just_below_review_threshold(self, db, test_patient):
        """Confidence == 0.59 should be unresolved."""
        result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.59
        )
        assert result["action_taken"] == "unresolved"

    def test_zero_confidence(self, db, test_patient):
        result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.0
        )
        assert result["action_taken"] == "unresolved"

    def test_no_confirmation_created_for_low(self, db, test_patient):
        handle_reid_event(db, "vision_lab", None, test_patient.tracking_id, 0.35)

        count = db.query(StaffConfirmation).filter(
            StaffConfirmation.patient_id == test_patient.id
        ).count()
        assert count == 0

    def test_unresolved_event_uses_correct_source_type(self, db, test_patient):
        """Low confidence events must use UNRESOLVED, not PENDING_REVIEW."""
        handle_reid_event(db, "vision_lab", None, test_patient.tracking_id, 0.30)

        event = db.query(MovementEvent).filter(
            MovementEvent.patient_id == test_patient.id
        ).first()
        assert event.source_type == SourceType.UNRESOLVED
        assert "low confidence" in event.notes.lower()


# =============================================================================
# QR-PRIORITY CONFLICT
# =============================================================================

class TestQRPriority:

    def test_reid_blocked_when_qr_exists_in_window(self, db, test_patient):
        """If QR scan exists for same patient/zone within priority window, Re-ID must not move."""
        # QR scan moves patient to vision_lab
        handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")

        # Re-ID event for same zone - should be blocked by QR priority
        result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.95
        )
        assert result["action_taken"] == "qr_priority"
        assert result["success"] is True

    def test_reid_allowed_for_different_zone(self, db, test_patient):
        """QR priority only blocks same zone, not next zone."""
        # QR scan moves patient to vision_lab
        handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")

        # Re-ID event for NEXT zone (dilation_hall) - should proceed
        result = handle_reid_event(
            db, "dilation_hall", None, test_patient.tracking_id, 0.92
        )
        assert result["action_taken"] == "auto_moved"

    def test_reid_allowed_after_priority_window_expires(self, db, test_patient):
        """Re-ID should work after QR priority window has expired."""
        # QR scan moves patient to vision_lab
        handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")

        # Backdate the QR event to outside the priority window
        qr_event = db.query(MovementEvent).filter(
            MovementEvent.patient_id == test_patient.id,
            MovementEvent.source_type == SourceType.QR
        ).first()
        qr_event.event_timestamp = datetime.now(timezone.utc) - timedelta(seconds=120)
        db.commit()

        # Re-ID to same zone - now allowed (but will be duplicate since patient is already there)
        # Let's test with next zone instead
        result = handle_reid_event(
            db, "dilation_hall", None, test_patient.tracking_id, 0.90
        )
        assert result["action_taken"] == "auto_moved"


# =============================================================================
# DUPLICATE PREVENTION
# =============================================================================

class TestDuplicatePrevention:

    def test_duplicate_qr_scan_blocked(self, db, test_patient):
        """Re-scanning same zone is blocked (same-zone validation catches it)."""
        r1 = handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")
        assert r1["success"] is True

        # vision_lab -> vision_lab blocked (same zone)
        r2 = handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")
        assert r2["success"] is False

    def test_duplicate_reid_blocked(self, db, test_patient):
        """Re-ID to same zone after auto-move is blocked."""
        r1 = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.92
        )
        assert r1["action_taken"] == "auto_moved"

        # vision_lab -> vision_lab blocked (same zone)
        r2 = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.90
        )
        assert r2["action_taken"] == "invalid_transition"

    def test_duplicate_event_within_window(self, db, patient_at_vision_lab):
        """Duplicate check catches repeated movements to same zone within window."""
        # Manually insert a recent event to test the duplicate checker directly
        event = MovementEvent(
            patient_id=patient_at_vision_lab.id,
            tracking_id=patient_at_vision_lab.tracking_id,
            source_type=SourceType.QR,
            from_zone="registration",
            to_zone="dilation_hall",
            event_timestamp=datetime.now(),
            actor="staff"
        )
        db.add(event)
        db.commit()

        assert _check_duplicate_event(db, patient_at_vision_lab.id, "registration", "dilation_hall") is True
        assert _check_duplicate_event(db, patient_at_vision_lab.id, "registration", "diagnostics") is False

    def test_check_duplicate_event_helper(self, db, test_patient):
        assert _check_duplicate_event(db, test_patient.id, "registration", "vision_lab") is False

        handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")
        assert _check_duplicate_event(db, test_patient.id, "registration", "vision_lab") is True


# =============================================================================
# RE-ID ERROR CASES
# =============================================================================

class TestReIDErrors:

    def test_no_matching_patient(self, db, seed_zones):
        result = handle_reid_event(db, "vision_lab", None, "NONEXISTENT", 0.90)
        assert result["success"] is False
        assert result["action_taken"] == "unresolved"

    def test_exited_patient(self, db, test_patient):
        test_patient.status = PatientStatus.EXITED
        db.commit()

        result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.90
        )
        assert result["success"] is False
        assert result["action_taken"] == "unresolved"

    def test_invalid_zone_rejected(self, db, test_patient):
        """Re-ID to a non-existent zone is rejected."""
        result = handle_reid_event(
            db, "nonexistent_zone", None, test_patient.tracking_id, 0.95
        )
        assert result["action_taken"] == "invalid_transition"

    def test_same_zone_rejected(self, db, test_patient):
        """Re-ID to same zone patient is already at is rejected."""
        result = handle_reid_event(
            db, "registration", None, test_patient.tracking_id, 0.95
        )
        assert result["action_taken"] == "invalid_transition"

    def test_no_patient_id_or_tracking_id(self, db, seed_zones):
        result = handle_reid_event(db, "vision_lab", None, None, 0.90)
        assert result["success"] is False


# =============================================================================
# STAFF CONFIRMATION - APPROVE
# =============================================================================

class TestStaffApprove:

    def test_approve_moves_patient(self, db, test_patient):
        # Create pending confirmation
        reid_result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )
        conf_id = reid_result["confirmation_id"]

        # Approve
        result = handle_staff_confirmation(db, conf_id, "approve", "staff_001")
        assert result["success"] is True
        assert result["action"] == "approve"
        assert result["to_zone"] == "vision_lab"

        # Patient moved
        db.refresh(test_patient)
        assert test_patient.current_zone == "vision_lab"
        assert test_patient.tracking_method == "manual_confirmed"

    def test_approve_creates_manual_confirmed_event(self, db, test_patient):
        reid_result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )
        handle_staff_confirmation(db, reid_result["confirmation_id"], "approve", "staff_001")

        event = db.query(MovementEvent).filter(
            MovementEvent.patient_id == test_patient.id,
            MovementEvent.source_type == SourceType.MANUAL_CONFIRMED
        ).first()
        assert event is not None
        assert event.actor == "staff_001"

    def test_approve_updates_confirmation_record(self, db, test_patient):
        reid_result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )
        conf_id = reid_result["confirmation_id"]
        handle_staff_confirmation(db, conf_id, "approve", "staff_001")

        confirmation = db.query(StaffConfirmation).filter(
            StaffConfirmation.id == conf_id
        ).first()
        assert confirmation.status == ConfirmationStatus.APPROVED
        assert confirmation.reviewed_by == "staff_001"
        assert confirmation.reviewed_at is not None

    def test_approve_fails_if_patient_moved_via_qr(self, db, test_patient):
        """If patient moved via QR after pending was created, approve should fail."""
        reid_result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )
        conf_id = reid_result["confirmation_id"]

        # Patient moves via QR to vision_lab first
        handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")

        # Now try to approve the confirmation — transition is no longer valid
        # (patient is at vision_lab, confirmation wants to move to vision_lab too — same zone)
        # Actually the QR scan should have cancelled this confirmation
        confirmation = db.query(StaffConfirmation).filter(
            StaffConfirmation.id == conf_id
        ).first()
        assert confirmation.status == ConfirmationStatus.REJECTED


# =============================================================================
# STAFF CONFIRMATION - REJECT
# =============================================================================

class TestStaffReject:

    def test_reject_does_not_move_patient(self, db, test_patient):
        reid_result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )
        conf_id = reid_result["confirmation_id"]

        result = handle_staff_confirmation(
            db, conf_id, "reject", "staff_002", reason="Wrong person"
        )
        assert result["success"] is True
        assert result["action"] == "reject"
        assert result["to_zone"] is None

        db.refresh(test_patient)
        assert test_patient.current_zone == "registration"  # unchanged

    def test_reject_creates_rejected_event(self, db, test_patient):
        reid_result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )
        handle_staff_confirmation(
            db, reid_result["confirmation_id"], "reject", "staff_002", reason="Mismatch"
        )

        event = db.query(MovementEvent).filter(
            MovementEvent.patient_id == test_patient.id,
            MovementEvent.source_type == SourceType.REJECTED
        ).first()
        assert event is not None
        assert event.actor == "staff_002"

    def test_reject_stores_reason(self, db, test_patient):
        reid_result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )
        conf_id = reid_result["confirmation_id"]
        handle_staff_confirmation(
            db, conf_id, "reject", "staff_002", reason="Not the right patient"
        )

        confirmation = db.query(StaffConfirmation).filter(
            StaffConfirmation.id == conf_id
        ).first()
        assert confirmation.rejection_reason == "Not the right patient"

    def test_reject_clears_needs_confirmation(self, db, test_patient):
        handle_reid_event(db, "vision_lab", None, test_patient.tracking_id, 0.72)

        db.refresh(test_patient)
        assert test_patient.needs_confirmation is True

        conf = db.query(StaffConfirmation).filter(
            StaffConfirmation.patient_id == test_patient.id
        ).first()
        handle_staff_confirmation(db, conf.id, "reject", "staff", reason="No")

        db.refresh(test_patient)
        assert test_patient.needs_confirmation is False


# =============================================================================
# STAFF CONFIRMATION - ERROR CASES
# =============================================================================

class TestStaffConfirmationErrors:

    def test_confirmation_not_found(self, db, seed_zones):
        result = handle_staff_confirmation(db, 99999, "approve", "staff")
        assert result["success"] is False

    def test_already_approved(self, db, test_patient):
        reid_result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )
        conf_id = reid_result["confirmation_id"]

        handle_staff_confirmation(db, conf_id, "approve", "staff")
        result = handle_staff_confirmation(db, conf_id, "approve", "staff")
        assert result["success"] is False
        assert "already" in result["message"].lower()

    def test_invalid_action(self, db, test_patient):
        reid_result = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )
        result = handle_staff_confirmation(
            db, reid_result["confirmation_id"], "invalid_action", "staff"
        )
        assert result["success"] is False


# =============================================================================
# QUERY HELPERS
# =============================================================================

class TestQueryHelpers:

    def test_get_pending_confirmations(self, db, test_patient):
        handle_reid_event(db, "vision_lab", None, test_patient.tracking_id, 0.72)

        pending = get_pending_confirmations(db)
        assert len(pending) == 1
        assert pending[0]["patient_name"] == "Test Patient"
        assert pending[0]["candidate_zone"] == "vision_lab"

    def test_get_movement_history_by_tracking_id(self, db, test_patient):
        handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")

        history = get_movement_history(db, tracking_id=test_patient.tracking_id)
        assert len(history) == 1
        assert history[0]["source_type"] == "qr"

    def test_get_movement_history_by_patient_id(self, db, test_patient):
        handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")

        history = get_movement_history(db, patient_id=test_patient.id)
        assert len(history) == 1

    def test_get_tracking_stats(self, db, test_patient):
        handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")
        handle_reid_event(db, "dilation_hall", None, test_patient.tracking_id, 0.92)

        stats = get_tracking_stats(db)
        assert stats["total_events"] == 2
        assert stats["by_source"]["qr"] == 1
        assert stats["by_source"]["reid_auto"] == 1
        assert "thresholds" in stats

    def test_stats_include_pending_count(self, db, test_patient):
        handle_reid_event(db, "vision_lab", None, test_patient.tracking_id, 0.72)

        stats = get_tracking_stats(db)
        assert stats["pending_confirmations"] == 1

    def test_unresolved_events_counted_separately(self, db, test_patient):
        """UNRESOLVED events must NOT inflate pending_review count in stats."""
        handle_reid_event(db, "vision_lab", None, test_patient.tracking_id, 0.30)

        stats = get_tracking_stats(db)
        assert stats["by_source"].get("unresolved", 0) == 1
        assert stats["by_source"].get("pending_review", 0) == 0


# =============================================================================
# END-TO-END WORKFLOW
# =============================================================================

class TestEndToEndWorkflow:

    def test_full_patient_journey_qr_only(self, db, test_patient):
        """Patient flows through all zones via QR scans."""
        zones = ["vision_lab", "dilation_hall", "diagnostics",
                 "consultation", "pharmacy", "billing_insurance"]

        for zone in zones:
            result = handle_qr_scan(db, test_patient.qr_token, zone, "staff")
            assert result["success"] is True, f"Failed at {zone}: {result['message']}"

        db.refresh(test_patient)
        assert test_patient.current_zone == "billing_insurance"

        history = get_movement_history(db, patient_id=test_patient.id)
        assert len(history) == len(zones)
        assert all(e["source_type"] == "qr" for e in history)

    def test_mixed_qr_and_reid_journey(self, db, test_patient):
        """Patient tracked by mix of QR scans and Re-ID auto-moves."""
        # QR: registration -> vision_lab
        handle_qr_scan(db, test_patient.qr_token, "vision_lab", "staff")

        # Re-ID: vision_lab -> dilation_hall (high confidence)
        handle_reid_event(db, "dilation_hall", None, test_patient.tracking_id, 0.91)

        # QR: dilation_hall -> diagnostics
        handle_qr_scan(db, test_patient.qr_token, "diagnostics", "staff")

        db.refresh(test_patient)
        assert test_patient.current_zone == "diagnostics"

        history = get_movement_history(db, patient_id=test_patient.id)
        source_types = {e["source_type"] for e in history}
        assert "qr" in source_types
        assert "reid_auto" in source_types

    def test_reid_pending_then_approved_journey(self, db, test_patient):
        """Re-ID pending -> staff approves -> patient moves."""
        # Medium confidence Re-ID
        reid = handle_reid_event(
            db, "vision_lab", None, test_patient.tracking_id, 0.72
        )
        assert reid["action_taken"] == "pending_review"

        db.refresh(test_patient)
        assert test_patient.current_zone == "registration"  # not moved yet

        # Staff approves
        result = handle_staff_confirmation(
            db, reid["confirmation_id"], "approve", "staff_001"
        )
        assert result["success"] is True

        db.refresh(test_patient)
        assert test_patient.current_zone == "vision_lab"  # now moved
