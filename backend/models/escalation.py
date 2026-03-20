"""
PatientPath AI - Escalation Model
==================================
Stores staff-reported operational issues that need admin attention.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SAEnum
from datetime import datetime
import enum
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database import Base


class EscalationStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class Escalation(Base):
    """Model for staff-reported escalation issues."""

    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    staff_id = Column(String(100), nullable=False, index=True)
    department = Column(String(100), nullable=False)
    issue_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SAEnum(EscalationStatus), default=EscalationStatus.OPEN, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self):
        return {
            "issue_id": f"E{self.id}",
            "id": self.id,
            "staff_id": self.staff_id,
            "department": self.department,
            "issue_type": self.issue_type,
            "description": self.description,
            "status": self.status.value if self.status else "OPEN",
            "timestamp": (self.timestamp.isoformat() + "Z") if self.timestamp else None,
        }
