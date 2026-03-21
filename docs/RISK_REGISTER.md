# PatientPath AI — Risk Register & Fallback Strategy

## Top Implementation Risks

| # | Risk | Likelihood | Impact | Mitigation | Fallback |
|---|------|-----------|--------|------------|----------|
| 1 | MySQL schema migration fails (existing table mismatch) | Medium | High | Auto-create via init_db(); provide ALTER scripts | Switch to `USE_SQLITE=true` for clean schema |
| 2 | Re-ID service unavailable | Low (MVP uses API simulation) | Medium | Re-ID is API-driven, not dependent on GPU | Demo QR-only flow; Re-ID events submitted via test scripts |
| 3 | QR token lookup slow under load | Low | Medium | qr_token column indexed; UUID lookup is O(1) | Fall back to tracking_id based lookup |
| 4 | Frontend pages don't load (static mount order) | Low | High | Tracking router registered before static mount | Access pages directly via /qr_scanner.html |
| 5 | Confidence thresholds too strict/loose | Medium | Low | Configurable via .env variables | Adjust REID_AUTO_THRESHOLD and REID_REVIEW_THRESHOLD live |
| 6 | Concurrent QR + Re-ID race condition | Low | Medium | QR priority window (60s) cancels pending Re-ID | QR always wins; pending items auto-rejected |
| 7 | Demo data conflicts with existing patients | Low | Low | Test scripts use timestamped tracking IDs | Clear test data before demo |

## Immediate Fallback Demo Mode

If ANY module fails, the system degrades gracefully:

### If Backend fails to start:
1. Check `.env` configuration
2. Try `USE_SQLITE=true` to bypass MySQL issues
3. Run `python -c "from database.database import init_db; init_db()"`

### If Re-ID module fails:
- QR scanning still works independently
- Demo the QR-first flow only
- Use test scripts to simulate Re-ID events manually

### If Frontend pages fail:
- Use API docs at `/docs` for interactive demo
- Use demo scripts (`demo_short.py`, `demo_full.py`) for terminal-based demo

### If Database migration fails:
- Switch to SQLite: `USE_SQLITE=true`
- This creates fresh tables automatically

## "Plan B" Minimal Demo

If time is critically constrained, demonstrate:

1. **Patient Registration** → QR token generated (POST /patient/enter)
2. **QR Scan Movement** → Two zone transitions via QR (POST /tracking/qr-scan)
3. **Re-ID Simulation** → One high-confidence auto-move (POST /tracking/reid-event)
4. **Audit Trail** → Show movement events with source badges (GET /tracking/events)

This proves the hybrid tracking concept in ~90 seconds using just the API.

## Deferred Items (If Timeline Constrained)

| Item | Reason Deferred | Impact on Demo |
|------|----------------|----------------|
| Camera-based Re-ID inference | Requires GPU + model training | None — simulated via API |
| Mobile QR scanner app | Not needed for web-based demo | None — web form scanner works |
| WebSocket push for confirmations | Polling at 5s is sufficient | Minimal — 5s delay acceptable |
| Patient photo in confirmation queue | Privacy and storage complexity | Low — patient name shown |
| Re-ID accuracy analytics dashboard | Out of MVP scope | None |
| Push notifications for staff | Additional complexity | None — queue page auto-refreshes |
| Multi-floor routing | Out of scope | None — single floor in demo |
