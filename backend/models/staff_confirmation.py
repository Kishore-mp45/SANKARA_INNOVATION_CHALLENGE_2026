"""
PatientPath AI - Staff Confirmation Model
==========================================
Pending Re-ID matches awaiting staff review.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text, Index
from datetime import datetime, timezone
import enum
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database import Base


class ConfirmationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class StaffConfirmation(Base):
    """Pending Re-ID matches that need staff approval."""

    __tablename__ = "staff_confirmations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, nullable=False, index=True)
    tracking_id = Column(String(50), nullable=False)
    candidate_zone = Column(String(50), nullable=False)
    from_zone = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=False)
    status = Column(Enum(ConfirmationStatus, values_callable=lambda x: [e.value for e in x]), default=ConfirmationStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    movement_event_id = Column(Integer, nullable=True)

    __table_args__ = (
        Index('ix_confirmation_status', 'status'),
        Index('ix_confirmation_patient', 'patient_id', 'status'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "tracking_id": self.tracking_id,
            "candidate_zone": self.candidate_zone,
            "from_zone": self.from_zone,
            "confidence": self.confidence,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.strftime("%d %b %Y, %I:%M %p") if self.created_at else None,
            "reviewed_at": self.reviewed_at.strftime("%d %b %Y, %I:%M %p") if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
            "rejection_reason": self.rejection_reason,
            "movement_event_id": self.movement_event_id,
        }
