"""
PatientPath AI - Metric Model
=============================
"""

from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database import Base


class Metric(Base):
    """Metric model for storing aggregated analytics."""
    
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    metric_type = Column(String(50), default="hourly", index=True)  # hourly, daily, realtime
    zone_name = Column(String(50), nullable=True, index=True)
    
    # Dwell time metrics (in minutes)
    avg_dwell_time = Column(Float, nullable=True)
    min_dwell_time = Column(Float, nullable=True)
    max_dwell_time = Column(Float, nullable=True)
    
    # Flow metrics
    entry_rate = Column(Float, nullable=True)  # entries per hour
    exit_rate = Column(Float, nullable=True)   # exits per hour
    throughput = Column(Float, nullable=True)  # total flow per hour
    
    # Count metrics
    total_entries = Column(Integer, nullable=True)
    total_exits = Column(Integer, nullable=True)
    peak_occupancy = Column(Integer, nullable=True)
    avg_occupancy = Column(Float, nullable=True)
    
    # Sample info
    sample_count = Column(Integer, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metric_type": self.metric_type,
            "zone_name": self.zone_name,
            "avg_dwell_time": self.avg_dwell_time,
            "entry_rate": self.entry_rate,
            "exit_rate": self.exit_rate,
            "throughput": self.throughput,
            "total_entries": self.total_entries,
            "total_exits": self.total_exits,
            "peak_occupancy": self.peak_occupancy,
            "avg_occupancy": self.avg_occupancy
        }
