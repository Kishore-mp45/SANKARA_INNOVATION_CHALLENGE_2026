"""
PatientPath AI - Test Configuration
====================================
Shared fixtures for tracking system tests.
Uses an in-memory SQLite database for isolation.
"""

import sys
import os
import pytest

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database.database import Base
from models.patient import Patient, PatientStatus
from models.movement_event import MovementEvent, SourceType
from models.staff_confirmation import StaffConfirmation, ConfirmationStatus
from models.zone import Zone


# In-memory SQLite engine for tests
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    echo=False
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def db():
    """Provide a clean database session for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def seed_zones(db):
    """Seed standard hospital zones."""
    zones = [
        Zone(zone_name="registration", display_name="Registration", capacity_limit=50, current_occupancy=0),
        Zone(zone_name="vision_lab", display_name="Vision Lab", capacity_limit=30, current_occupancy=0),
        Zone(zone_name="dilation_hall", display_name="Dilation Hall", capacity_limit=40, current_occupancy=0),
        Zone(zone_name="diagnostics", display_name="Diagnostics", capacity_limit=20, current_occupancy=0),
        Zone(zone_name="consultation", display_name="Consultation", capacity_limit=25, current_occupancy=0),
        Zone(zone_name="pharmacy", display_name="Pharmacy", capacity_limit=15, current_occupancy=0),
        Zone(zone_name="billing_insurance", display_name="Billing & Insurance", capacity_limit=20, current_occupancy=0),
    ]
    for z in zones:
        db.add(z)
    db.commit()
    return zones


@pytest.fixture
def test_patient(db, seed_zones):
    """Create a test patient at registration with a QR token."""
    patient = Patient(
        name="Test Patient",
        tracking_id="CV-TEST-001",
        qr_token=Patient.generate_qr_token(),
        mobile="9876543210",
        status=PatientStatus.ENTERED,
        current_zone="registration",
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@pytest.fixture
def patient_at_vision_lab(db, seed_zones):
    """Create a test patient already at vision_lab."""
    patient = Patient(
        name="Vision Lab Patient",
        tracking_id="CV-TEST-002",
        qr_token=Patient.generate_qr_token(),
        mobile="9876543211",
        status=PatientStatus.ENTERED,
        current_zone="vision_lab",
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@pytest.fixture
def patient_at_diagnostics(db, seed_zones):
    """Create a test patient already at diagnostics."""
    patient = Patient(
        name="Diagnostics Patient",
        tracking_id="CV-TEST-003",
        qr_token=Patient.generate_qr_token(),
        mobile="9876543212",
        status=PatientStatus.ENTERED,
        current_zone="diagnostics",
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient
