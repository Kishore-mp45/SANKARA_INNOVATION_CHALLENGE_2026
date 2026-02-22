"""
PatientPath AI - Alert Model
============================
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, Text
from datetime import datetime
import enum
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database import Base


class AlertType(str, enum.Enum):
    """Alert type enumeration."""
    CAPACITY_WARNING = "capacity_warning"
    CAPACITY_CRITICAL = "capacity_critical"
    LONG_WAIT_TIME = "long_wait_time"
    UNUSUAL_ACTIVITY = "unusual_activity"
    SYSTEM_ERROR = "system_error"
    CUSTOM = "custom"


class AlertSeverity(str, enum.Enum):
    """Alert severity enumeration."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(Base):
    """Alert model for system notifications."""
    
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.INFO, nullable=False)
    message = Column(Text, nullable=False)
    zone_name = Column(String(50), nullable=True, index=True)
    patient_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON string for extra data
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "alert_type": self.alert_type.value if self.alert_type else None,
            "severity": self.severity.value if self.severity else None,
            "message": self.message,
            "zone_name": self.zone_name,
            "is_active": self.is_active,
            "acknowledged": self.acknowledged
        }
