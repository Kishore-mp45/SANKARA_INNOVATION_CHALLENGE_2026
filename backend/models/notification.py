"""
PatientPath AI - Notification Model
=====================================
Stores staff deployment notifications and admin alerts.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from database.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recipient_id = Column(String(20), nullable=False, index=True)  # generated_id of recipient
    sender_id = Column(String(20), nullable=True)  # generated_id of sender (admin)
    type = Column(String(30), nullable=False, default="deployment")  # deployment, alert, assignment
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=True)
    target_department = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, accepted, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "sender_id": self.sender_id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "target_department": self.target_department,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
        }
