# PatientPath AI — Deployment & Demo Checklist

## Hardware Assumptions
- Laptop with 8GB+ RAM
- Windows 10/11
- MySQL 8.0 running locally (or SQLite fallback)
- Optional: Webcam for Re-ID demo (not required for MVP)

## Software Requirements
- Python 3.10+
- MySQL 8.0 (or set `USE_SQLITE=true` in `.env`)
- pip packages from `backend/requirements.txt`
- Browser: Chrome/Edge (modern)

## Pre-Demo Setup

### 1. Environment Variables
```bash
cd backend
# Verify .env exists with correct values:
cat .env
# Required: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, USE_SQLITE, DEBUG
# New tracking config auto-defaults from code if missing
```

### 2. Database Migration
```bash
# The app auto-creates new tables on startup (init_db)
# New tables: movement_events, staff_confirmations
# New columns on patients: qr_token, tracking_method, reid_confidence, needs_confirmation, updated_by_source, last_movement_time
#
# If using MySQL and tables already exist, run:
python -c "from database.database import init_db; init_db()"
#
# If columns are missing on existing patients table, run MySQL ALTER:
# ALTER TABLE patients ADD COLUMN qr_token VARCHAR(64) UNIQUE;
# ALTER TABLE patients ADD COLUMN tracking_method VARCHAR(30) DEFAULT 'manual';
# ALTER TABLE patients ADD COLUMN reid_confidence FLOAT;
# ALTER TABLE patients ADD COLUMN needs_confirmation BOOLEAN DEFAULT FALSE;
# ALTER TABLE patients ADD COLUMN updated_by_source VARCHAR(100) DEFAULT 'system';
# ALTER TABLE patients ADD COLUMN last_movement_time DATETIME;
```

### 3. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 4. Start Backend
```bash
cd backend
python main.py
# Runs on http://localhost:8000
# Admin portal on http://localhost:5000
```

### 5. Verify Health
```bash
curl http://localhost:8000/system/health
curl http://localhost:8000/tracking/stats
curl http://localhost:8000/tracking/department-sequence
```

### 6. Seed Demo Data (Optional)
```bash
# Run the demo script to create test patients:
python scripts/demo_short.py
```

## Startup Sequence (Exact Commands)

```bash
# Terminal 1: Backend API
cd d:\iQube\Sankara-2026\SANKARA_INNOVATION_CHALLENGE_2026\backend
python main.py

# Terminal 2: Run tests (optional)
cd d:\iQube\Sankara-2026\SANKARA_INNOVATION_CHALLENGE_2026
python scripts/test_tracking_system.py

# Terminal 3: Run demo
python scripts/demo_short.py   # 3-min version
python scripts/demo_full.py    # 8-min version
```

## Quick Health Checks Before Live Demo

| Check | Command | Expected |
|-------|---------|----------|
| Server up | `curl localhost:8000/system/health` | `{"status": "ok"}` |
| Tracking API | `curl localhost:8000/tracking/stats` | JSON with thresholds |
| Department sequence | `curl localhost:8000/tracking/department-sequence` | 7 departments |
| Frontend loads | Open `http://localhost:8000/qr_scanner.html` | Page renders |
| Confirmation queue | Open `http://localhost:8000/staff_confirmation.html` | Page renders |
| Audit trail | Open `http://localhost:8000/movement_audit.html` | Page renders |

## Demo Pages

| Page | URL | Purpose |
|------|-----|---------|
| QR Scanner | /qr_scanner.html | Scan QR codes to record movement |
| Confirmation Queue | /staff_confirmation.html | Approve/reject Re-ID matches |
| Movement Audit | /movement_audit.html | Full audit trail with badges |
| Staff Panel | /staff_panel.html | Staff dashboard |
| API Docs | /docs | Interactive API documentation |

## GPU/CPU Mode
- YOLOv8 detection: CPU mode by default (yolov8n.pt)
- Re-ID: Simulated via API calls in MVP (no GPU required)
- All ML inference bounded at 5 FPS cap
