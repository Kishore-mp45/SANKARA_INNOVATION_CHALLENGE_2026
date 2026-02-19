"""
PatientPath AI - Occupancy Log Model
====================================
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database import Base


class OccupancyLog(Base):
    """Occupancy log model for tracking zone occupancy over time."""
    
    __tablename__ = "occupancy_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    people_count = Column(Integer, nullable=False)
    previous_count = Column(Integer, nullable=True)
    zone_name = Column(String(50), ForeignKey("zones.zone_name"), nullable=False, index=True)
    entry_count = Column(Integer, default=0)
    exit_count = Column(Integer, default=0)
    confidence_score = Column(Float, nullable=True)
    source = Column(String(50), default="cv_detection")  # cv_detection, manual, api
    unique_ids = Column(String, nullable=True)  # JSON string of unique IDs

    @property
    def delta(self):
        if self.previous_count is None:
            return 0
        return self.people_count - self.previous_count
        
    @property
    def net_flow(self):
        return self.entry_count - self.exit_count
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "people_count": self.people_count,
            "previous_count": self.previous_count,
            "zone_name": self.zone_name,
            "entry_count": self.entry_count,
            "exit_count": self.exit_count,
            "confidence_score": self.confidence_score,
            "source": self.source,
            "unique_ids": self.unique_ids
        }
