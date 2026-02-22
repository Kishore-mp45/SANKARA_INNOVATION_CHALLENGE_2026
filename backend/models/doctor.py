from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database.database import Base
from datetime import datetime
import enum

class DoctorStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    role = Column(String(50), default="doctor")
    status = Column(Enum(DoctorStatus), default=DoctorStatus.OFFLINE)
    last_check_in = Column(DateTime, nullable=True)
    last_check_out = Column(DateTime, nullable=True)
    
    consultations = relationship("ConsultationLog", back_populates="doctor")

class ConsultationLog(Base):
    __tablename__ = "consultation_logs"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    patient_id = Column(String(50), nullable=False) # Tracking ID (e.g., CV-12345)
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)
    notes = Column(String(500), nullable=True)
    
    doctor = relationship("Doctor", back_populates="consultations")
