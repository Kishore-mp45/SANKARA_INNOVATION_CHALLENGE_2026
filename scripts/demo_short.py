"""
PatientPath AI - SHORT DEMO SCRIPT
====================================
Fast judges walkthrough (~3 minutes)

Usage: python scripts/demo_short.py
"""

import requests
import json
import time

BASE = "http://localhost:8000"
CYAN = "\033[96m"; GREEN = "\033[92m"; YELLOW = "\033[93m"; BOLD = "\033[1m"; RESET = "\033[0m"

def post(path, data):
    r = requests.post(f"{BASE}{path}", json=data)
    return r.json()

def get(path):
    return requests.get(f"{BASE}{path}").json()

def pause(msg):
    print(f"\n{BOLD}{CYAN}>>> {msg}{RESET}")
    input(f"{YELLOW}    [Press ENTER to continue...]{RESET}")

def show(label, data):
    print(f"  {GREEN}{label}:{RESET}")
    if isinstance(data, dict):
        for k, v in data.items():
            if k in ("success", "message", "tracking_method", "to_zone", "from_zone",
                      "action_taken", "confidence", "tracking_id", "qr_token",
                      "current_zone", "action", "pending_confirmations"):
                print(f"    {k}: {BOLD}{v}{RESET}")
    else:
        print(f"    {data}")


print(f"\n{BOLD}{'='*60}")
print(f"  PatientPath AI - SHORT DEMO (Fast Judges Walkthrough)")
print(f"{'='*60}{RESET}\n")

# ── STEP 1: Register Patient ──
pause("STEP 1: Register a new patient (generates QR code)")
patient = post("/patient/enter", {
    "name": "Rajesh Kumar",
    "tracking_id": f"DEMO-{int(time.time())}",
    "zone_name": "registration"
})
show("Patient Registered", patient)
QR = patient.get("qr_token")
TID = patient.get("tracking_id")
print(f"\n  {BOLD}QR Token generated: {QR}{RESET}")
print(f"  {BOLD}Key point: Every patient gets a unique QR code at registration.{RESET}")

# ── STEP 2: QR Scan Movement ──
pause("STEP 2: Staff scans QR code at Vision Lab entrance")
result = post("/tracking/qr-scan", {"qr_token": QR, "zone_name": "vision_lab", "scanned_by": "demo_staff"})
show("QR Scan Result", result)
print(f"  {BOLD}Key point: QR is the PRIMARY tracking method. Instant, reliable.{RESET}")

pause("STEP 2b: Continue QR scan to Dilation Hall")
result = post("/tracking/qr-scan", {"qr_token": QR, "zone_name": "dilation_hall", "scanned_by": "demo_staff"})
show("QR Scan Result", result)

# ── STEP 3: Re-ID Auto-Move (High Confidence) ──
pause("STEP 3: QR missed! Re-ID detects patient at Diagnostics (92% confidence)")
result = post("/tracking/reid-event", {
    "zone_name": "diagnostics",
    "candidate_tracking_id": TID,
    "confidence": 0.92
})
show("Re-ID Result", result)
print(f"  {BOLD}Key point: High confidence (>=85%) auto-moves patient. No staff action needed.{RESET}")

# ── STEP 4: Re-ID Pending (Medium Confidence) ──
pause("STEP 4: Re-ID detects patient at Consultation (68% confidence)")
result = post("/tracking/reid-event", {
    "zone_name": "consultation",
    "candidate_tracking_id": TID,
    "confidence": 0.68
})
show("Re-ID Result", result)
conf_id = result.get("confirmation_id")
print(f"  {BOLD}Key point: Medium confidence (60-84%) creates a PENDING item for staff review.{RESET}")
print(f"  {BOLD}Patient does NOT move until staff approves.{RESET}")

# ── STEP 5: Staff Confirmation ──
pause("STEP 5: Staff reviews and approves the pending match")
result = post("/tracking/confirmations/action", {
    "confirmation_id": conf_id,
    "action": "approve",
    "staff_id": "demo_staff"
})
show("Confirmation Result", result)
print(f"  {BOLD}Key point: Staff has full control. Can approve or reject with audit trail.{RESET}")

# ── STEP 6: Audit Trail ──
pause("STEP 6: View complete movement audit trail")
events = get(f"/tracking/events?tracking_id={TID}")
print(f"  Movement events for {TID}:")
for ev in events:
    conf = f" ({int(ev['confidence']*100)}%)" if ev.get('confidence') else ""
    print(f"    [{ev['source_type']:>20}] {ev.get('from_zone','start'):>18} -> {ev['to_zone']:<20}{conf}  by {ev['actor']}")

# ── STEP 7: Stats ──
pause("STEP 7: View tracking statistics")
stats = get("/tracking/stats")
show("Tracking Stats", stats)

print(f"\n{BOLD}{'='*60}")
print(f"  DEMO COMPLETE")
print(f"{'='*60}{RESET}")
print(f"""
{BOLD}KEY TALKING POINTS:{RESET}
  1. {GREEN}QR-first{RESET}: Primary tracking via QR codes — instant, reliable
  2. {GREEN}Re-ID fallback{RESET}: Camera-based when QR is missed — confidence-based routing
  3. {GREEN}Safety{RESET}: Low confidence NEVER auto-moves patients
  4. {GREEN}Staff control{RESET}: Medium confidence requires human approval
  5. {GREEN}Full audit trail{RESET}: Every movement tracked with source, confidence, actor
  6. {GREEN}Zone validation{RESET}: Invalid transitions blocked automatically
""")
