"""
PatientPath AI - Database Seeding Script
========================================
Seeds the database with initial test data for demonstration.
"""

from datetime import datetime, timedelta
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_context
from models.zone import Zone
from models.patient import Patient, PatientStatus
from models.occupancy import OccupancyLog
from models.alert import Alert, AlertType, AlertSeverity
from models.metric import Metric
from utils.logger import get_logger

logger = get_logger(__name__)


# Sample zone configurations for a hospital
# Sample zone configurations for a hospital
SAMPLE_ZONES = [
    {
        "zone_name": "vision_lab",
        "display_name": "Vision Lab",
        "description": "Vision testing and analysis",
        "capacity_limit": 15,
        "zone_type": "medical",
        "floor_number": 1,
        "building": "Main Building"
    },
    {
        "zone_name": "dilation_hall",
        "display_name": "Dilation Hall",
        "description": "Patient dilation area",
        "capacity_limit": 25,
        "zone_type": "waiting",
        "floor_number": 1,
        "building": "Main Building"
    },
    {
        "zone_name": "diagnostics",
        "display_name": "Diagnostics",
        "description": "Diagnostic imaging and tests",
        "capacity_limit": 20,
        "zone_type": "medical",
        "floor_number": 1,
        "building": "Main Building"
    },
    {
        "zone_name": "billing_insurance",
        "display_name": "Billing & Insurance",
        "description": "Financial services",
        "capacity_limit": 10,
        "zone_type": "service",
        "floor_number": 1,
        "building": "Main Building"
    },
    {
        "zone_name": "registration",
        "display_name": "Registration",
        "description": "New patient registration",
        "capacity_limit": 15,
        "zone_type": "service",
        "floor_number": 1,
        "building": "Main Building"
    },
    {
        "zone_name": "consultation",
        "display_name": "Consultation",
        "description": "Doctor consultation rooms",
        "capacity_limit": 10,
        "zone_type": "examination",
        "floor_number": 1,
        "building": "Main Building"
    },
    {
        "zone_name": "pharmacy",
        "display_name": "Pharmacy",
        "description": "Medication dispensing area",
        "capacity_limit": 20,
        "zone_type": "service",
        "floor_number": 1,
        "building": "Main Building"
    }
]


def seed_zones(db):
    """Seed zone data."""
    logger.info("Seeding zones...")
    
    for zone_data in SAMPLE_ZONES:
        # Check if zone already exists
        existing = db.query(Zone).filter(Zone.zone_name == zone_data["zone_name"]).first()
        if existing:
            continue
        
        zone = Zone(
            zone_name=zone_data["zone_name"],
            display_name=zone_data["display_name"],
            description=zone_data["description"],
            capacity_limit=zone_data["capacity_limit"],
            zone_type=zone_data["zone_type"],
            floor_number=zone_data["floor_number"],
            building=zone_data["building"],
            current_occupancy=random.randint(0, zone_data["capacity_limit"] // 2),
            warning_threshold=0.8,
            critical_threshold=0.95,
            is_active=True
        )
        db.add(zone)
    
    db.commit()
    logger.info(f"Seeded {len(SAMPLE_ZONES)} zones")


def seed_patients(db, count: int = 50):
    """Seed patient data."""
    logger.info(f"Seeding {count} patients...")
    
    # Check if patients already exist
    existing_count = db.query(Patient).count()
    if existing_count >= count:
        logger.info(f"Already have {existing_count} patients, skipping")
        return
    
    zones = db.query(Zone).filter(Zone.is_active == True).all()
    zone_names = [z.zone_name for z in zones]
    
    statuses = [PatientStatus.ENTERED, PatientStatus.WAITING, PatientStatus.IN_ROOM]
    
    for i in range(count - existing_count):
        # Random entry time in the last 24 hours
        hours_ago = random.randint(0, 24)
        entry_time = datetime.utcnow() - timedelta(hours=hours_ago)
        
        # Some patients have exited
        has_exited = random.random() < 0.3
        exit_time = None
        status = random.choice(statuses)
        
        if has_exited:
            exit_time = entry_time + timedelta(minutes=random.randint(15, 180))
            status = PatientStatus.EXITED
        
        patient = Patient(
            name=f"Patient_{i + 1 + existing_count}",
            tracking_id=f"CV-{random.randint(10000, 99999)}",
            entry_time=entry_time,
            exit_time=exit_time,
            status=status,
            current_zone=random.choice(zone_names) if not has_exited else None
        )
        db.add(patient)
    
    db.commit()
    logger.info(f"Seeded {count - existing_count} new patients")


def seed_occupancy_logs(db, hours: int = 24):
    """Seed historical occupancy logs."""
    logger.info(f"Seeding occupancy logs for last {hours} hours...")
    
    # Check if we already have logs
    existing_count = db.query(OccupancyLog).count()
    if existing_count > hours * 60:  # Roughly 1 per minute
        logger.info(f"Already have {existing_count} occupancy logs, skipping")
        return
    
    zones = db.query(Zone).filter(Zone.is_active == True).all()
    
    logs_created = 0
    for zone in zones:
        # Create hourly readings for the past N hours
        base_count = zone.current_occupancy
        
        for h in range(hours, 0, -1):
            timestamp = datetime.utcnow() - timedelta(hours=h)
            
            # Simulate occupancy variation
            variation = random.randint(-5, 5)
            people_count = max(0, min(base_count + variation, zone.capacity_limit))
            
            log = OccupancyLog(
                timestamp=timestamp,
                people_count=people_count,
                previous_count=base_count if h < hours else None,
                zone_name=zone.zone_name,
                entry_count=random.randint(0, 5),
                exit_count=random.randint(0, 5),
                confidence_score=round(random.uniform(0.85, 0.99), 2),
                source="seed_data"
            )
            db.add(log)
            logs_created += 1
            
            base_count = people_count
    
    db.commit()
    logger.info(f"Seeded {logs_created} occupancy logs")


def seed_metrics(db, hours: int = 24):
    """Seed historical metrics."""
    logger.info(f"Seeding metrics for last {hours} hours...")
    
    # Check if we already have metrics
    existing_count = db.query(Metric).count()
    if existing_count >= hours:
        logger.info(f"Already have {existing_count} metrics, skipping")
        return
    
    for h in range(hours, 0, -1):
        timestamp = datetime.utcnow() - timedelta(hours=h)
        period_start = timestamp - timedelta(hours=1)
        
        metric = Metric(
            timestamp=timestamp,
            period_start=period_start,
            period_end=timestamp,
            metric_type="hourly",
            avg_dwell_time=round(random.uniform(20, 60), 2),
            min_dwell_time=round(random.uniform(5, 15), 2),
            max_dwell_time=round(random.uniform(60, 180), 2),
            entry_rate=round(random.uniform(5, 25), 2),
            exit_rate=round(random.uniform(5, 20), 2),
            throughput=round(random.uniform(10, 45), 2),
            total_entries=random.randint(10, 50),
            total_exits=random.randint(10, 45),
            peak_occupancy=random.randint(50, 120),
            avg_occupancy=round(random.uniform(40, 80), 2),
            sample_count=random.randint(50, 100)
        )
        db.add(metric)
    
    db.commit()
    logger.info(f"Seeded {hours} hourly metrics")


def seed_alerts(db, count: int = 5):
    """Seed sample alerts."""
    logger.info(f"Seeding {count} sample alerts...")
    
    # Check if we already have alerts
    existing_count = db.query(Alert).count()
    if existing_count >= count:
        logger.info(f"Already have {existing_count} alerts, skipping")
        return
    
    zones = db.query(Zone).filter(Zone.is_active == True).all()
    zone_names = [z.zone_name for z in zones]
    
    alert_templates = [
        {
            "alert_type": AlertType.CAPACITY_WARNING,
            "severity": AlertSeverity.WARNING,
            "message": "Zone has reached 80% capacity"
        },
        {
            "alert_type": AlertType.LONG_WAIT_TIME,
            "severity": AlertSeverity.INFO,
            "message": "Average wait time exceeds 45 minutes"
        },
        {
            "alert_type": AlertType.UNUSUAL_ACTIVITY,
            "severity": AlertSeverity.WARNING,
            "message": "Unusual occupancy pattern detected"
        }
    ]
    
    for i in range(count - existing_count):
        template = random.choice(alert_templates)
        zone = random.choice(zone_names)
        hours_ago = random.randint(0, 12)
        
        alert = Alert(
            timestamp=datetime.utcnow() - timedelta(hours=hours_ago),
            alert_type=template["alert_type"],
            severity=template["severity"],
            message=f"{template['message']} in {zone}",
            zone_name=zone,
            is_active=random.random() < 0.5,
            acknowledged=random.random() < 0.3
        )
        db.add(alert)
    
    db.commit()
    logger.info(f"Seeded {count - existing_count} new alerts")


def seed_initial_data():
    """
    Main function to seed all initial data.
    Safe to call multiple times - checks for existing data.
    """
    logger.info("=" * 50)
    logger.info("Starting database seeding...")
    logger.info("=" * 50)
    
    try:
        with get_db_context() as db:
            seed_zones(db)
            seed_patients(db, count=50)
            seed_occupancy_logs(db, hours=24)
            seed_metrics(db, hours=24)
            seed_alerts(db, count=5)
        
        logger.info("=" * 50)
        logger.info("Database seeding completed successfully!")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        raise


if __name__ == "__main__":
    """Run seeding script directly."""
    from database import init_db
    init_db()
    seed_initial_data()
