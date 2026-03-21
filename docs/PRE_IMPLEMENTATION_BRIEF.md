# PatientPath AI — Pre-Implementation Brief
## QR-First Patient Tracking with Re-ID Fallback MVP

**Date**: 2026-03-21
**Engineer**: Lead Hackathon Engineer
**Status**: Pre-Implementation

---

## A) ONE-PAGE PRODUCT SCOPE

### In-Scope MVP Features
1. **QR Code Generation & Scanning** — Generate QR per patient at registration; scan to record zone transitions
2. **QR-First Movement Logic** — QR scan immediately updates patient zone with `tracking_method=qr`
3. **Re-ID Fallback** — When no QR scan in event window, use person re-identification to match patient
4. **Confidence Threshold Policy** — AUTO_THRESHOLD (≥0.85), REVIEW_THRESHOLD (≥0.60), below = unresolved
5. **Staff Confirmation Queue** — Pending Re-ID matches shown to staff for approve/reject
6. **Movement Audit Trail** — Every event logged with source_type, confidence, timestamps, actor
7. **Dashboard Tracking Badges** — Visual indicators for QR / Re-ID Auto / Manual Confirmed / Pending / Rejected
8. **Zone Transition Validation** — Only valid next-zone transitions allowed

### Explicitly Out-of-Scope
- Multi-camera Re-ID model training or fine-tuning
- Mobile app for QR scanning (use web-based scanner)
- Patient self-service movement updates
- Cross-building or multi-floor routing
- Re-ID model switching or ensemble
- Historical Re-ID accuracy analytics
- Push notifications for staff confirmation
- Patient photo capture/storage for Re-ID (use existing video feed embeddings)

### User/Demo Journey Steps
1. **Registration** → Patient registered, QR code generated and printed/displayed
2. **QR Scan at Zone** → Staff scans QR → patient moves to next zone instantly
3. **QR Missed** → Re-ID detects person in new zone → high confidence auto-moves, medium creates pending item
4. **Staff Reviews** → Staff opens confirmation queue → approves or rejects pending matches
5. **Dashboard View** → Admin/staff sees all patient movements with tracking method badges
6. **Audit Trail** → Click any patient to see full event history with sources

### Demo Success Criteria
- [ ] Patient registers and gets QR code
- [ ] QR scan moves patient through 3+ zones successfully
- [ ] Simulated Re-ID match auto-moves patient (high confidence)
- [ ] Simulated Re-ID match creates pending item (medium confidence)
- [ ] Staff approves pending match → movement committed
- [ ] Staff rejects pending match → no movement
- [ ] Dashboard shows all tracking method badges correctly
- [ ] Audit trail shows complete event history
- [ ] No silent zone updates from low-confidence matches
- [ ] Invalid zone transitions blocked

---

## B) CURRENT SYSTEM MAPPING

### Backend Routes (Relevant)

| Purpose | Route | Method | File |
|---------|-------|--------|------|
| Patient Registration | `/patient/enter` | POST | routers/patients.py |
| Patient Movement | `/patient/movement` | POST | routers/patients.py |
| Stage Update | `/patient/update-stage` | POST | routers/patients.py |
| Patient Exit | `/patient/exit` | POST | routers/patients.py |
| Patient List | `/patient/list` | GET | routers/patients.py |
| Patient Detail | `/patient/{patient_id}` | GET | routers/patients.py |
| Patient by Zone | `/patient/zone/{zone_name}` | GET | routers/patients.py |
| Zone List | `/zones` | GET | routers/zones.py |
| Zone Detail | `/zones/{zone_name}` | GET | routers/zones.py |
| Escalations | `/admin/escalations` | GET | routers/admin.py |
| Activity Logs | `/admin/activity` | GET | routers/admin.py |
| Dashboard Stats | `/admin/dashboard-stats` | GET | routers/admin.py |
| WebSocket | `/ws` | WS | routers/websocket.py |

### Database Tables (Relevant)

| Table | Key Fields |
|-------|-----------|
| `patients` | id, name, tracking_id, mobile, status, current_zone, action_history (JSON), entry_time, exit_time |
| `zones` | id, zone_name, display_name, capacity_limit, current_occupancy, zone_type |
| `occupancy_logs` | id, timestamp, people_count, zone_name, source |
| `alerts` | id, alert_type, severity, message, zone_name, patient_id |
| `escalations` | id, staff_id, department, issue_type, description, status |

### Frontend Pages (Relevant)

| Purpose | File | Role |
|---------|------|------|
| Patient Dashboard | patient_dashboard.html | Patient |
| Live Navigator | live_navigator.html | Patient |
| Staff Panel | staff_panel.html | Staff |
| Patient Search | patient_search.html | Staff |
| Admin Dashboard | admin_dashboard.html | Admin |
| Occupancy View | occupancy.html | All |
| Escalation Reports | escalation_reports.html | Admin |

### Existing Workflow Sequence
```
registration → vision_lab → dilation_hall → diagnostics → consultation → pharmacy → billing_insurance
```

---

## C) DOMAIN RULE DEFINITION

### Department Sequence (Full Ordered List)
```
0: registration
1: vision_lab
2: dilation_hall
3: diagnostics
4: consultation
5: pharmacy
6: billing_insurance
7: exit
```

### Allowed Transitions (from_zone → valid next zones)

| From Zone | Valid Next Zones |
|-----------|-----------------|
| entrance | registration |
| registration | vision_lab |
| vision_lab | dilation_hall |
| dilation_hall | diagnostics |
| diagnostics | consultation |
| consultation | pharmacy |
| pharmacy | billing_insurance |
| billing_insurance | exit |

> **Rule**: Only sequential forward transitions allowed in MVP. No skipping, no backward movement.

### Confidence Threshold Policy

```
AUTO_THRESHOLD    = 0.85   # ≥ 0.85 → auto-update, tracking_method = reid_auto
REVIEW_THRESHOLD  = 0.60   # ≥ 0.60 and < 0.85 → pending staff review
                           # < 0.60 → no movement, unresolved event only
```

### Patient Identity Schema Contract

```json
{
  "patient_id": "int (PK)",
  "tracking_id": "string (CV-XXXXX format)",
  "qr_token": "string (UUID, unique per patient)",
  "name": "string",
  "current_zone": "string (zone_name)",
  "status": "enum (ENTERED, WAITING, IN_ROOM, EXITED)",
  "tracking_method": "enum (qr, reid_auto, manual_confirmed, pending_review, rejected)",
  "reid_confidence": "float (0.0-1.0, nullable)",
  "needs_confirmation": "boolean (default false)",
  "last_movement_time": "datetime (UTC)",
  "updated_by_source": "string (system/staff_id)"
}
```

### Movement Event Schema

```json
{
  "event_id": "int (PK, auto)",
  "patient_id": "int (FK)",
  "source_type": "enum (qr, reid_auto, pending_review, manual_confirmed, rejected)",
  "from_zone": "string",
  "to_zone": "string",
  "confidence": "float (nullable, Re-ID only)",
  "event_timestamp": "datetime (UTC, backend-authored)",
  "actor": "string (system / staff_user_id)",
  "notes": "string (nullable, rejection reason)"
}
```

### Event Window
- **QR Priority Window**: 60 seconds — if QR scan arrives within 60s of Re-ID detection, QR takes precedence
- **Re-ID Trigger Delay**: 30 seconds after expected zone transition with no QR scan
- **Duplicate Prevention**: Max 1 movement event per patient per zone per 120-second window

---

## PERFORMANCE CONSTRAINTS (Hackathon MVP)

| Parameter | Target |
|-----------|--------|
| Camera inference FPS cap | 5 FPS (sufficient for demo) |
| Re-ID check throttle | 1 check per 10 seconds per zone |
| Max patients for Re-ID matching | Active patients in adjacent zones only |
| API response latency | < 500ms for all endpoints |
| WebSocket broadcast latency | < 1 second |
| Staff confirmation queue refresh | 5 seconds polling or WebSocket |

---

## IMPLEMENTATION PHASES

### Phase 0: Security & Setup Hardening
- Verify .env not committed, secrets not in code
- Add QR/Re-ID config to .env

### Phase 1: This Document (Complete)

### Phase 2: Data Model & API Contract Updates
- Add `qr_token`, `tracking_method`, `reid_confidence`, `needs_confirmation`, `updated_by_source` to Patient model
- Create `MovementEvent` model/table
- Create `StaffConfirmation` model/table
- Add tracking config constants

### Phase 3: QR-First Flow Integration
- QR token generation on patient registration
- QR scan endpoint (`POST /patient/qr-scan`)
- QR-based movement with zone validation
- QR code display on patient dashboard

### Phase 4: Re-ID Fallback Integration
- Re-ID service wrapper (simulated for MVP)
- Confidence-based routing logic
- Event window and duplicate prevention
- Auto-move for high confidence

### Phase 5: Staff Confirmation Queue
- Pending confirmation list endpoint
- Approve/reject endpoints
- Staff confirmation UI page

### Phase 6: Dashboard Indicators + Audit
- Tracking method badges in patient list/dashboard
- Movement event history view
- Confidence display for Re-ID events

### Phase 7: Test Scenarios + Demo Scripts
- Automated test cases for all 8 scenarios
- Short demo script
- Full demo script

### Phase 8: Stabilization & Rollback
- Risk register
- Fallback plan
- Deployment checklist
