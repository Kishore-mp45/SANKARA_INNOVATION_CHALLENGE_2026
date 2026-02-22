"""
PatientPath AI - Zone Model
===========================
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database import Base


class Zone(Base):
    """Zone model representing hospital areas."""
    
    __tablename__ = "zones"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    zone_name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=True)
    description = Column(String(255), nullable=True)
    capacity_limit = Column(Integer, default=50, nullable=False)
    current_occupancy = Column(Integer, default=0)
    zone_type = Column(String(50), nullable=True)  # waiting, entrance, exit, etc.
    floor_number = Column(Integer, nullable=True)
    building = Column(String(100), nullable=True)
    warning_threshold = Column(Float, default=0.8)  # 80%
    critical_threshold = Column(Float, default=0.95)  # 95%
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    @property
    def occupancy_rate(self) -> float:
        if self.capacity_limit == 0:
            return 0.0
        return self.current_occupancy / self.capacity_limit
    
    def to_dict(self):
        return {
            "id": self.id,
            "zone_name": self.zone_name,
            "display_name": self.display_name,
            "description": self.description,
            "capacity_limit": self.capacity_limit,
            "current_occupancy": self.current_occupancy,
            "occupancy_rate": round(self.occupancy_rate, 3),
            "zone_type": self.zone_type,
            "floor_number": self.floor_number,
            "building": self.building,
            "is_active": self.is_active
        }
