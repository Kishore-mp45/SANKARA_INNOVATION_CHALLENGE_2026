"""
PatientPath AI - FULL DEMO SCRIPT
====================================
Detailed walkthrough with failure cases (~8 minutes)

Usage: python scripts/demo_full.py
"""

import requests
import json
import time

BASE = "http://localhost:8000"
CYAN = "\033[96m"; GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; BOLD = "\033[1m"; RESET = "\033[0m"

def post(path, data):
    r = requests.post(f"{BASE}{path}", json=data)
    return r.status_code, r.json()

def get(path):
    r = requests.get(f"{BASE}{path}")
    return r.status_code, r.json()

def pause(msg):
    print(f"\n{BOLD}{CYAN}>>> {msg}{RESET}")
    input(f"{YELLOW}    [Press ENTER to continue...]{RESET}")

def show(label, code, data):
    status_color = GREEN if code == 200 else RED
    print(f"  {status_color}[{code}]{RESET} {GREEN}{label}:{RESET}")
    print(f"    {json.dumps(data, indent=2)[:500]}")

print(f"\n{BOLD}{'='*60}")
print(f"  PatientPath AI - FULL DEMO SCRIPT")
print(f"  Hybrid QR + Re-ID Patient Tracking System")
print(f"{'='*60}{RESET}")

# ============================================================================
# SCENE 1: Patient Registration + QR Generation
# ============================================================================
pause("SCENE 1: Patient Registration — QR code auto-generated")
s, patient1 = post("/patient/enter", {
    "name": "Ananya Sharma",
    "tracking_id": f"DEMO-A-{int(time.time())}",
    "zone_name": "registration"
})
show("Patient 1 Registered", s, patient1)
QR1 = patient1.get("qr_token")
TID1 = patient1.get("tracking_id")
print(f"\n  {BOLD}QR Token: {QR1}{RESET}")

# Register a second patient for multi-person testing
s, patient2 = post("/patient/enter", {
    "name": "Vikram Patel",
    "tracking_id": f"DEMO-B-{int(time.time())}",
    "zone_name": "registration"
})
QR2 = patient2.get("qr_token")
TID2 = patient2.get("tracking_id")
print(f"  Patient 2: {TID2}, QR: {QR2}")

# ============================================================================
# SCENE 2: Happy Path — QR Scan Through Multiple Zones
# ============================================================================
pause("SCENE 2: QR scan — happy path through Registration -> Vision Lab -> Dilation Hall")

s, r = post("/tracking/qr-scan", {"qr_token": QR1, "zone_name": "vision_lab", "scanned_by": "nurse_001"})
show("QR Scan: Vision Lab", s, r)

s, r = post("/tracking/qr-scan", {"qr_token": QR1, "zone_name": "dilation_hall", "scanned_by": "nurse_001"})
show("QR Scan: Dilation Hall", s, r)

print(f"\n  {BOLD}All QR scans show tracking_method: 'qr' — instant zone updates{RESET}")

# ============================================================================
# SCENE 3: Invalid Transition Blocked
# ============================================================================
pause("SCENE 3: SAFETY — Invalid zone transition blocked")
print(f"  Attempting: Dilation Hall -> Pharmacy (skipping Diagnostics & Consultation)")
s, r = post("/tracking/qr-scan", {"qr_token": QR1, "zone_name": "pharmacy", "scanned_by": "nurse_001"})
show("Invalid Transition", s, r)
print(f"\n  {RED}{BOLD}Blocked! Only sequential transitions allowed.{RESET}")

# ============================================================================
# SCENE 4: Duplicate Prevention
# ============================================================================
pause("SCENE 4: SAFETY — Duplicate scan prevention")
s, r = post("/tracking/qr-scan", {"qr_token": QR1, "zone_name": "dilation_hall", "scanned_by": "nurse_001"})
show("Duplicate Scan", s, r)
print(f"\n  {RED}{BOLD}Blocked! Cannot re-scan same zone within 120-second window.{RESET}")

# ============================================================================
# SCENE 5: Re-ID High Confidence Auto-Move
# ============================================================================
pause("SCENE 5: QR MISSED — Re-ID detects patient at Diagnostics (90% confidence)")
s, r = post("/tracking/reid-event", {
    "zone_name": "diagnostics",
    "candidate_tracking_id": TID1,
    "confidence": 0.90
})
show("Re-ID Auto-Move", s, r)
print(f"\n  {BOLD}Action: auto_moved — confidence >= 85% threshold{RESET}")

# ============================================================================
# SCENE 6: Re-ID Medium Confidence → Pending Queue
# ============================================================================
pause("SCENE 6: Re-ID detects patient at Consultation (72% confidence)")
s, r = post("/tracking/reid-event", {
    "zone_name": "consultation",
    "candidate_tracking_id": TID1,
    "confidence": 0.72
})
show("Re-ID Pending Review", s, r)
conf_id_1 = r.get("confirmation_id")
print(f"\n  {YELLOW}{BOLD}Action: pending_review — staff must confirm before movement{RESET}")

# ============================================================================
# SCENE 7: Re-ID Low Confidence → No Movement
# ============================================================================
pause("SCENE 7: Re-ID low confidence match for Patient 2 (40%)")
# First move patient 2 via QR to vision_lab
post("/tracking/qr-scan", {"qr_token": QR2, "zone_name": "vision_lab", "scanned_by": "nurse_002"})

s, r = post("/tracking/reid-event", {
    "zone_name": "dilation_hall",
    "candidate_tracking_id": TID2,
    "confidence": 0.40
})
show("Low Confidence", s, r)
print(f"\n  {RED}{BOLD}Action: unresolved — NO movement, manual handling only{RESET}")

# ============================================================================
# SCENE 8: Staff Confirmation Queue
# ============================================================================
pause("SCENE 8: Staff views pending confirmation queue")
s, queue = get("/tracking/confirmations/pending")
show("Pending Queue", s, queue)
print(f"\n  {BOLD}{len(queue)} item(s) awaiting staff review{RESET}")

# ============================================================================
# SCENE 9: Staff Approves Match
# ============================================================================
pause("SCENE 9: Staff APPROVES the pending match")
if conf_id_1:
    s, r = post("/tracking/confirmations/action", {
        "confirmation_id": conf_id_1,
        "action": "approve",
        "staff_id": "dr_smith_042"
    })
    show("Approval Result", s, r)
    print(f"\n  {GREEN}{BOLD}Patient moved to Consultation — tracked as 'manual_confirmed'{RESET}")

# ============================================================================
# SCENE 10: Staff Rejects Match
# ============================================================================
pause("SCENE 10: Create and REJECT a pending match")
# Move patient1 via QR to pharmacy
post("/tracking/qr-scan", {"qr_token": QR1, "zone_name": "pharmacy", "scanned_by": "nurse_001"})

s, r = post("/tracking/reid-event", {
    "zone_name": "billing_insurance",
    "candidate_tracking_id": TID1,
    "confidence": 0.65
})
conf_id_2 = r.get("confirmation_id")

if conf_id_2:
    s, r = post("/tracking/confirmations/action", {
        "confirmation_id": conf_id_2,
        "action": "reject",
        "staff_id": "nurse_001",
        "reason": "Different patient — similar clothing"
    })
    show("Rejection Result", s, r)
    print(f"\n  {RED}{BOLD}Rejected — patient stays in current zone. Reason logged.{RESET}")

# ============================================================================
# SCENE 11: QR Overrides Pending Re-ID
# ============================================================================
pause("SCENE 11: QR scan overrides pending Re-ID (QR takes precedence)")
# Move patient2 to dilation_hall via QR
post("/tracking/qr-scan", {"qr_token": QR2, "zone_name": "dilation_hall", "scanned_by": "nurse_002"})

# Create a pending Re-ID for diagnostics
s, r = post("/tracking/reid-event", {
    "zone_name": "diagnostics",
    "candidate_tracking_id": TID2,
    "confidence": 0.70
})
pending_before = r.get("confirmation_id")

# Now QR scan arrives for the same zone — should override
s, r = post("/tracking/qr-scan", {"qr_token": QR2, "zone_name": "diagnostics", "scanned_by": "nurse_002"})
show("QR Override", s, r)
print(f"\n  {GREEN}{BOLD}QR scan overrides pending Re-ID — pending items auto-cancelled{RESET}")

# ============================================================================
# SCENE 12: Full Audit Trail
# ============================================================================
pause("SCENE 12: Complete audit trail for Patient 1")
s, events = get(f"/tracking/events?tracking_id={TID1}")
print(f"\n  Movement history for {TID1}:")
print(f"  {'Time':<22} {'Source':<20} {'From':<18} {'To':<18} {'Confidence':>10}  {'Actor'}")
print(f"  {'-'*110}")
for ev in events:
    t = ev['event_timestamp'][:19].replace('T', ' ')
    conf = f"{int(ev['confidence']*100)}%" if ev.get('confidence') else "  —"
    src = ev['source_type']
    print(f"  {t:<22} {src:<20} {ev.get('from_zone','start'):<18} {ev['to_zone']:<18} {conf:>10}  {ev['actor']}")

# ============================================================================
# SCENE 13: Tracking Statistics
# ============================================================================
pause("SCENE 13: System-wide tracking statistics")
s, stats = get("/tracking/stats")
show("Tracking Stats", s, stats)
print(f"\n  Thresholds: Auto={stats['thresholds']['auto']}, Review={stats['thresholds']['review']}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print(f"\n{BOLD}{'='*60}")
print(f"  DEMO COMPLETE — FULL WALKTHROUGH")
print(f"{'='*60}{RESET}")
print(f"""
{BOLD}HYBRID TRACKING SYSTEM — KEY FEATURES:{RESET}

  {GREEN}1. QR-First{RESET}: Primary method. Instant, 100% accurate zone tracking.
  {GREEN}2. Re-ID Fallback{RESET}: Activates when QR is missed. Confidence-based routing.
  {GREEN}3. Three Confidence Tiers{RESET}:
     - HIGH (>=85%): Auto-move, no staff action needed
     - MEDIUM (60-84%): Pending staff confirmation queue
     - LOW (<60%): No movement, logged for manual handling
  {GREEN}4. Staff Confirmation{RESET}: Full approve/reject workflow with audit trail.
  {GREEN}5. QR Priority{RESET}: QR scan always overrides pending Re-ID matches.
  {GREEN}6. Zone Validation{RESET}: Only sequential transitions allowed.
  {GREEN}7. Duplicate Prevention{RESET}: No redundant updates within event window.
  {GREEN}8. Complete Audit Trail{RESET}: Every event logged with source, confidence, actor.

{BOLD}SAFETY GUARANTEES:{RESET}
  - No silent patient-zone updates from low-confidence matches
  - No duplicate zone updates for same patient/event window
  - No cross-zone invalid transitions
  - All uncertain matches traceable and reviewable
  - QR always takes precedence over Re-ID

{BOLD}DEMO PAGES:{RESET}
  - QR Scanner:         http://localhost:8000/qr_scanner.html
  - Confirmation Queue:  http://localhost:8000/staff_confirmation.html
  - Movement Audit:      http://localhost:8000/movement_audit.html
  - Staff Panel:         http://localhost:8000/staff_panel.html
  - API Docs:            http://localhost:8000/docs
""")
