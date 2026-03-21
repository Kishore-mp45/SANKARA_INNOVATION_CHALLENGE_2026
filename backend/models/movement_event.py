"""
PatientPath AI - Movement Event Model
======================================
Audit trail for every patient movement event.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text, Index
from datetime import datetime, timezone, timedelta
import enum
import sys
import os

IST = timezone(timedelta(hours=5, minutes=30))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database import Base


class SourceType(str, enum.Enum):
    QR = "qr"
    REID_AUTO = "reid_auto"
    PENDING_REVIEW = "pending_review"
    MANUAL_CONFIRMED = "manual_confirmed"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"


class MovementEvent(Base):
    """Immutable audit log for every patient movement event."""

    __tablename__ = "movement_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, nullable=False, index=True)
    tracking_id = Column(String(50), nullable=False, index=True)
    source_type = Column(Enum(SourceType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    from_zone = Column(String(50), nullable=True)
    to_zone = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=True)
    event_timestamp = Column(DateTime, default=lambda: datetime.now(IST).replace(tzinfo=None), nullable=False)
    actor = Column(String(100), default="system", nullable=False)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index('ix_movement_patient_time', 'patient_id', 'event_timestamp'),
        Index('ix_movement_source', 'source_type'),
    )

    def to_dict(self):
        return {
            "event_id": self.id,
            "patient_id": self.patient_id,
            "tracking_id": self.tracking_id,
            "source_type": self.source_type.value if self.source_type else None,
            "from_zone": self.from_zone,
            "to_zone": self.to_zone,
            "confidence": self.confidence,
            "event_timestamp": self.event_timestamp.strftime("%d %b %Y, %I:%M %p") if self.event_timestamp else None,
            "actor": self.actor,
            "notes": self.notes,
        }
