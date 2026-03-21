"""
PatientPath AI - Tracking System Test Suite
=============================================
Tests all 8 required scenarios for QR-first + Re-ID fallback MVP.

Run: python scripts/test_tracking_system.py
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

results = []


def log(msg, color=RESET):
    print(f"{color}{msg}{RESET}")


def test(name, fn):
    log(f"\n{'='*60}", CYAN)
    log(f"TEST: {name}", BOLD)
    log(f"{'='*60}", CYAN)
    try:
        fn()
        results.append((name, "PASS"))
        log(f"  RESULT: PASS", GREEN)
    except AssertionError as e:
        results.append((name, f"FAIL: {e}"))
        log(f"  RESULT: FAIL - {e}", RED)
    except Exception as e:
        results.append((name, f"ERROR: {e}"))
        log(f"  RESULT: ERROR - {e}", RED)


def api_get(path):
    r = requests.get(f"{BASE_URL}{path}")
    return r.status_code, r.json()


def api_post(path, data):
    r = requests.post(f"{BASE_URL}{path}", json=data)
    return r.status_code, r.json()


# ============================================================================
# SETUP: Register a test patient
# ============================================================================

test_patient = {}


def setup_patient():
    """Create a test patient for the suite."""
    global test_patient
    tracking_id = f"TEST-{int(time.time())}"
    status, data = api_post("/patient/enter", {
        "name": "Test Patient QR",
        "tracking_id": tracking_id,
        "zone_name": "registration"
    })
    assert status == 200, f"Patient creation failed: {data}"
    test_patient = data
    log(f"  Created patient: {tracking_id}, QR token: {data.get('qr_token', 'N/A')}", CYAN)
    assert data.get("qr_token"), "No QR token generated!"


# ============================================================================
# TEST 1: QR Success Path
# ============================================================================

def test_qr_success():
    """QR scan updates zone immediately, method shown as QR."""
    qr_token = test_patient["qr_token"]

    status, data = api_post("/tracking/qr-scan", {
        "qr_token": qr_token,
        "zone_name": "vision_lab",
        "scanned_by": "test_staff"
    })
    log(f"  Response: {json.dumps(data, indent=2)}", YELLOW)
    assert status == 200, f"QR scan failed: {data}"
    assert data["success"] is True
    assert data["to_zone"] == "vision_lab"
    assert data["tracking_method"] == "qr"
    log(f"  Patient moved to vision_lab via QR scan", GREEN)


# ============================================================================
# TEST 2: QR Missed -> Re-ID High Confidence
# ============================================================================

def test_reid_high_confidence():
    """Re-ID auto-move when confidence >= 0.85."""
    # Move patient forward via QR first to dilation_hall
    qr_token = test_patient["qr_token"]
    api_post("/tracking/qr-scan", {
        "qr_token": qr_token,
        "zone_name": "dilation_hall",
        "scanned_by": "test_staff"
    })

    # Now simulate Re-ID high confidence move to diagnostics
    status, data = api_post("/tracking/reid-event", {
        "zone_name": "diagnostics",
        "candidate_tracking_id": test_patient["tracking_id"],
        "confidence": 0.92
    })
    log(f"  Response: {json.dumps(data, indent=2)}", YELLOW)
    assert status == 200
    assert data["action_taken"] == "auto_moved"
    assert data["confidence"] == 0.92
    log(f"  Auto-moved via Re-ID (92% confidence)", GREEN)


# ============================================================================
# TEST 3: QR Missed -> Medium Confidence (Pending)
# ============================================================================

def test_reid_medium_confidence():
    """Medium confidence creates pending queue item, no auto-move."""
    status, data = api_post("/tracking/reid-event", {
        "zone_name": "consultation",
        "candidate_tracking_id": test_patient["tracking_id"],
        "confidence": 0.72
    })
    log(f"  Response: {json.dumps(data, indent=2)}", YELLOW)
    assert status == 200
    assert data["action_taken"] == "pending_review"
    assert data.get("confirmation_id") is not None
    log(f"  Pending review created (72% confidence), ID: {data['confirmation_id']}", GREEN)

    # Store for confirmation tests
    test_patient["pending_confirmation_id"] = data["confirmation_id"]


# ============================================================================
# TEST 4: Low Confidence -> No Movement
# ============================================================================

def test_reid_low_confidence():
    """Low confidence logs event but does NOT move patient."""
    # Create a second patient to test low confidence
    tracking_id_2 = f"TEST-LOW-{int(time.time())}"
    api_post("/patient/enter", {
        "name": "Test Patient Low",
        "tracking_id": tracking_id_2,
        "zone_name": "registration"
    })

    status, data = api_post("/tracking/reid-event", {
        "zone_name": "vision_lab",
        "candidate_tracking_id": tracking_id_2,
        "confidence": 0.35
    })
    log(f"  Response: {json.dumps(data, indent=2)}", YELLOW)
    assert status == 200
    assert data["action_taken"] == "unresolved"
    log(f"  Low confidence (35%) — no movement, logged for manual handling", GREEN)


# ============================================================================
# TEST 5: Staff Approves Pending Match
# ============================================================================

def test_staff_approve():
    """Staff approves pending match -> movement committed."""
    conf_id = test_patient.get("pending_confirmation_id")
    assert conf_id, "No pending confirmation ID from previous test"

    status, data = api_post("/tracking/confirmations/action", {
        "confirmation_id": conf_id,
        "action": "approve",
        "staff_id": "test_staff_001"
    })
    log(f"  Response: {json.dumps(data, indent=2)}", YELLOW)
    assert status == 200
    assert data["success"] is True
    assert data["action"] == "approve"
    assert data["to_zone"] == "consultation"
    log(f"  Staff approved -> patient moved to consultation", GREEN)


# ============================================================================
# TEST 6: Staff Rejects Pending Match
# ============================================================================

def test_staff_reject():
    """Staff rejects pending match -> no movement."""
    # Create another pending item
    # Move patient via QR to pharmacy first
    qr_token = test_patient["qr_token"]
    api_post("/tracking/qr-scan", {
        "qr_token": qr_token,
        "zone_name": "pharmacy",
        "scanned_by": "test_staff"
    })

    # Create a medium-confidence Re-ID event
    status, data = api_post("/tracking/reid-event", {
        "zone_name": "billing_insurance",
        "candidate_tracking_id": test_patient["tracking_id"],
        "confidence": 0.68
    })
    assert data["action_taken"] == "pending_review"
    conf_id = data["confirmation_id"]

    # Reject it
    status, data = api_post("/tracking/confirmations/action", {
        "confirmation_id": conf_id,
        "action": "reject",
        "staff_id": "test_staff_002",
        "reason": "Wrong patient match"
    })
    log(f"  Response: {json.dumps(data, indent=2)}", YELLOW)
    assert status == 200
    assert data["action"] == "reject"
    log(f"  Staff rejected -> no movement applied", GREEN)


# ============================================================================
# TEST 7: Invalid Zone Transition Blocked
# ============================================================================

def test_invalid_transition():
    """Invalid zone transition is blocked."""
    # Try to move patient from pharmacy directly to diagnostics (invalid)
    tracking_id_3 = f"TEST-INV-{int(time.time())}"
    s, p = api_post("/patient/enter", {
        "name": "Invalid Trans Test",
        "tracking_id": tracking_id_3,
        "zone_name": "registration"
    })
    qr = p.get("qr_token")

    # Try invalid transition: registration -> diagnostics (should skip vision_lab, dilation_hall)
    status, data = api_post("/tracking/qr-scan", {
        "qr_token": qr,
        "zone_name": "diagnostics",
        "scanned_by": "test_staff"
    })
    log(f"  Response: status={status}, {json.dumps(data, indent=2)}", YELLOW)
    assert status == 400, "Should have blocked invalid transition"
    log(f"  Invalid transition blocked correctly", GREEN)


# ============================================================================
# TEST 8: Duplicate Prevention
# ============================================================================

def test_duplicate_prevention():
    """No duplicate zone updates for same patient/event window."""
    tracking_id_4 = f"TEST-DUP-{int(time.time())}"
    s, p = api_post("/patient/enter", {
        "name": "Duplicate Test",
        "tracking_id": tracking_id_4,
        "zone_name": "registration"
    })
    qr = p.get("qr_token")

    # First scan — should succeed
    status1, data1 = api_post("/tracking/qr-scan", {
        "qr_token": qr, "zone_name": "vision_lab", "scanned_by": "test"
    })
    assert status1 == 200 and data1["success"]

    # Second scan — same zone, should be blocked as duplicate
    status2, data2 = api_post("/tracking/qr-scan", {
        "qr_token": qr, "zone_name": "vision_lab", "scanned_by": "test"
    })
    log(f"  Duplicate response: status={status2}, {json.dumps(data2, indent=2)}", YELLOW)
    assert status2 == 400, "Duplicate should be blocked"
    log(f"  Duplicate correctly blocked", GREEN)


# ============================================================================
# TEST 9: Movement Audit Trail
# ============================================================================

def test_audit_trail():
    """Verify movement events are logged with correct source types."""
    status, events = api_get(f"/tracking/events?tracking_id={test_patient['tracking_id']}&limit=20")
    assert status == 200
    log(f"  Found {len(events)} events for {test_patient['tracking_id']}", CYAN)
    for ev in events:
        log(f"    [{ev['source_type']}] {ev.get('from_zone','?')} -> {ev['to_zone']} (conf={ev.get('confidence','N/A')}) by {ev['actor']}", YELLOW)

    source_types = set(ev["source_type"] for ev in events)
    assert "qr" in source_types, "Expected QR events in audit trail"
    log(f"  Audit trail verified with source types: {source_types}", GREEN)


# ============================================================================
# TEST 10: Tracking Stats
# ============================================================================

def test_tracking_stats():
    """Verify tracking stats endpoint returns correct summary."""
    status, stats = api_get("/tracking/stats")
    assert status == 200
    log(f"  Stats: {json.dumps(stats, indent=2)}", YELLOW)
    assert stats["total_events"] > 0
    assert "thresholds" in stats
    log(f"  Tracking stats verified: {stats['total_events']} total events", GREEN)


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    log(f"\n{'#'*60}", BOLD)
    log(f"  PatientPath AI - Tracking System Test Suite", BOLD)
    log(f"  Target: {BASE_URL}", CYAN)
    log(f"{'#'*60}\n", BOLD)

    # Health check
    try:
        s, d = api_get("/system/health")
        assert s == 200
        log(f"Server is up: {d.get('status', 'ok')}", GREEN)
    except Exception as e:
        log(f"Server not reachable at {BASE_URL}: {e}", RED)
        log("Start the server with: cd backend && python main.py", YELLOW)
        sys.exit(1)

    # Setup
    test("Setup: Create test patient with QR token", setup_patient)

    # Core tests
    test("1. QR Success Path", test_qr_success)
    test("2. Re-ID High Confidence Auto-Move", test_reid_high_confidence)
    test("3. Re-ID Medium Confidence -> Pending Queue", test_reid_medium_confidence)
    test("4. Re-ID Low Confidence -> No Movement", test_reid_low_confidence)
    test("5. Staff Approves Pending Match", test_staff_approve)
    test("6. Staff Rejects Pending Match", test_staff_reject)
    test("7. Invalid Zone Transition Blocked", test_invalid_transition)
    test("8. Duplicate Movement Prevention", test_duplicate_prevention)
    test("9. Movement Audit Trail Verified", test_audit_trail)
    test("10. Tracking Stats Endpoint", test_tracking_stats)

    # Summary
    log(f"\n{'='*60}", BOLD)
    log(f"  TEST SUMMARY", BOLD)
    log(f"{'='*60}", BOLD)
    passed = sum(1 for _, r in results if r == "PASS")
    total = len(results)
    for name, result in results:
        color = GREEN if result == "PASS" else RED
        log(f"  {color}{'PASS' if result == 'PASS' else 'FAIL'}{RESET} {name}")
    log(f"\n  {passed}/{total} tests passed", GREEN if passed == total else RED)
    sys.exit(0 if passed == total else 1)
