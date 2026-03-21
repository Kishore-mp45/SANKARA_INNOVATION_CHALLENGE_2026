"""
PatientPath AI - Tracking System Migration
============================================
Adds new columns to existing patients table and creates new tracking tables.
Safe to run multiple times.

Usage: cd backend && python ../scripts/migrate_tracking.py
"""

import sys
import os

# Add backend to path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from database.database import engine, init_db, SessionLocal
from sqlalchemy import text, inspect

def run_migration():
    print("PatientPath AI — Tracking System Migration")
    print("=" * 50)

    # Step 1: Create new tables (movement_events, staff_confirmations)
    print("\n[1/3] Creating new tables...")
    init_db()
    print("  Tables created/verified: movement_events, staff_confirmations")

    # Step 2: Add new columns to patients table if they don't exist
    print("\n[2/3] Adding new columns to patients table...")
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("patients")}

    new_columns = {
        "qr_token": "VARCHAR(64) UNIQUE",
        "tracking_method": "VARCHAR(30) DEFAULT 'manual'",
        "reid_confidence": "FLOAT",
        "needs_confirmation": "BOOLEAN DEFAULT FALSE",
        "updated_by_source": "VARCHAR(100) DEFAULT 'system'",
        "last_movement_time": "DATETIME",
    }

    with engine.connect() as conn:
        for col_name, col_def in new_columns.items():
            if col_name not in existing_columns:
                try:
                    # Detect dialect
                    if engine.url.drivername.startswith("sqlite"):
                        conn.execute(text(f"ALTER TABLE patients ADD COLUMN {col_name} {col_def}"))
                    else:
                        conn.execute(text(f"ALTER TABLE patients ADD COLUMN {col_name} {col_def}"))
                    conn.commit()
                    print(f"  Added column: {col_name}")
                except Exception as e:
                    print(f"  Column {col_name}: {e}")
            else:
                print(f"  Column {col_name} already exists")

    # Step 3: Generate QR tokens for existing patients without one
    print("\n[3/3] Generating QR tokens for existing patients...")
    db = SessionLocal()
    try:
        from models.patient import Patient
        patients_without_qr = db.query(Patient).filter(Patient.qr_token == None).all()
        count = 0
        for p in patients_without_qr:
            p.qr_token = Patient.generate_qr_token()
            count += 1
        if count:
            db.commit()
            print(f"  Generated QR tokens for {count} existing patients")
        else:
            print(f"  All patients already have QR tokens")
    except Exception as e:
        print(f"  Error: {e}")
        db.rollback()
    finally:
        db.close()

    # Step 4: Add UNRESOLVED to source_type enum (MySQL only)
    print("\n[4/4] Updating source_type enum (if MySQL)...")
    if not engine.url.drivername.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE movement_events MODIFY COLUMN source_type "
                    "ENUM('qr','reid_auto','pending_review','manual_confirmed','rejected','unresolved') NOT NULL"
                ))
                conn.commit()
                print("  Added 'unresolved' to source_type enum")
        except Exception as e:
            print(f"  Enum update: {e}")
    else:
        print("  SQLite — no enum migration needed (stores as text)")

    # Step 5: Convert UTC timestamps to IST (+5:30) for existing movement events
    print("\n[5/5] Converting UTC timestamps to IST...")
    try:
        with engine.connect() as conn:
            if engine.url.drivername.startswith("sqlite"):
                conn.execute(text(
                    "UPDATE movement_events SET event_timestamp = datetime(event_timestamp, '+5 hours', '+30 minutes') "
                    "WHERE event_timestamp < datetime('now', '-4 hours')"
                ))
                conn.execute(text(
                    "UPDATE staff_confirmations SET created_at = datetime(created_at, '+5 hours', '+30 minutes') "
                    "WHERE created_at < datetime('now', '-4 hours')"
                ))
            else:
                conn.execute(text(
                    "UPDATE movement_events SET event_timestamp = DATE_ADD(event_timestamp, INTERVAL 330 MINUTE) "
                    "WHERE event_timestamp < DATE_SUB(NOW(), INTERVAL 4 HOUR)"
                ))
                conn.execute(text(
                    "UPDATE staff_confirmations SET created_at = DATE_ADD(created_at, INTERVAL 330 MINUTE) "
                    "WHERE created_at < DATE_SUB(NOW(), INTERVAL 4 HOUR)"
                ))
            conn.commit()
            print("  Converted existing UTC timestamps to IST")
    except Exception as e:
        print(f"  Timestamp conversion: {e}")

    print(f"\n{'='*50}")
    print("Migration complete!")
    print("New API endpoints available:")
    print("  POST /tracking/qr-scan          — QR code scanning")
    print("  POST /tracking/reid-event        — Re-ID fallback")
    print("  GET  /tracking/confirmations/pending")
    print("  POST /tracking/confirmations/action")
    print("  GET  /tracking/events            — Audit trail")
    print("  GET  /tracking/stats             — Statistics")

if __name__ == "__main__":
    run_migration()
