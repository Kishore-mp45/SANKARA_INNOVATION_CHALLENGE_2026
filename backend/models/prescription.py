"""
PatientPath AI - Prescription Model
====================================
Stores doctor prescriptions for patients.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doctor_id = Column(String(100), nullable=False, index=True)
    patient_id = Column(String(100), nullable=False, index=True)
    diagnosis = Column(Text, nullable=False)
    prescription = Column(Text, nullable=False)
    next_visit = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "doctor_id": self.doctor_id,
            "patient_id": self.patient_id,
            "diagnosis": self.diagnosis,
            "prescription": self.prescription,
            "next_visit": self.next_visit,
            "created_at": self.created_at.strftime("%d %b %Y, %H:%M") if self.created_at else None,
        }
