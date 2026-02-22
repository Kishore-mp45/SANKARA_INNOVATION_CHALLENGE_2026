import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database.database import SessionLocal
from models.patient import Patient, PatientStatus

from models.zone import Zone

db = SessionLocal()
count = db.query(Patient).filter(Patient.status != PatientStatus.EXITED).count()
print(f"Active Patients: {count}")

zones = db.query(Zone).all()
for z in zones:
    print(f"Zone: {z.zone_name}, ID: {z.id}")

db.close()
