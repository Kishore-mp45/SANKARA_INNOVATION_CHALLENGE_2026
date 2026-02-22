"""
PatientPath AI - Patient Model
==============================
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum, Index, Text
from datetime import datetime
import enum
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database import Base


# Force reload for model update 2026-02-13 22:30

class PatientStatus(str, enum.Enum):
    """Patient status enumeration."""
    ENTERED = "entered"
    WAITING = "waiting"
    IN_ROOM = "in_room"
    EXITED = "exited"


class Patient(Base):
    """Patient model for tracking individuals."""
    
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=True)
    tracking_id = Column(String(50), unique=True, nullable=False, index=True)
    mobile = Column(String(20), nullable=True)
    entry_time = Column(DateTime, default=datetime.now, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    status = Column(Enum(PatientStatus), default=PatientStatus.ENTERED, nullable=False)
    current_zone = Column(String(50), nullable=True, index=True)
    last_action = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    action_history = Column(Text, nullable=True, default="[]")
    
    __table_args__ = (
        Index('ix_patients_status_zone', 'status', 'current_zone'),
    )
    
    @property
    def is_active(self):
        """Check if patient is currently active (not exited)."""
        return self.status != PatientStatus.EXITED

    @property
    def dwell_time_minutes(self):
        """Calculate dwell time in minutes."""
        if not self.entry_time:
            return 0.0
        end_time = self.exit_time or datetime.now()
        delta = end_time - self.entry_time
        return round(delta.total_seconds() / 60, 2)

    @property
    def dept_dwell_time_minutes(self):
        """Calculate time elapsed in current department (since last stage update)."""
        reference_time = self.updated_at or self.entry_time
        if not reference_time:
            return 0.0
        end_time = self.exit_time or datetime.now()
        delta = end_time - reference_time
        return round(delta.total_seconds() / 60, 2)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "tracking_id": self.tracking_id,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "status": self.status.value if self.status else None,
            "current_zone": self.current_zone,
            "mobile": self.mobile,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "dwell_time_minutes": self.dwell_time_minutes,
            "dept_dwell_time_minutes": self.dept_dwell_time_minutes,
            "is_active": self.is_active,
            "last_action": self.last_action,
            "action_history": json.loads(self.action_history) if self.action_history else []
        }
