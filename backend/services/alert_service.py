"""Alert Service"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.alert import Alert, AlertType, AlertSeverity
from schemas.alert import AlertCreate
from models.zone import Zone


class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Alert]:
        return self.db.query(Alert).order_by(desc(Alert.timestamp)).offset(skip).limit(limit).all()
    
    def get_active(self) -> List[Alert]:
        return self.db.query(Alert).filter(Alert.is_active == True).order_by(desc(Alert.timestamp)).all()
    
    def get_by_id(self, alert_id: int) -> Optional[Alert]:
        return self.db.query(Alert).filter(Alert.id == alert_id).first()
    
    def get_by_zone(self, zone_name: str) -> List[Alert]:
        return self.db.query(Alert).filter(Alert.zone_name == zone_name).order_by(desc(Alert.timestamp)).all()
    
    def create(self, data: AlertCreate) -> Alert:
        alert = Alert(
            alert_type=AlertType(data.alert_type.value),
            severity=AlertSeverity(data.severity.value),
            message=data.message,
            zone_name=data.zone_name,
            patient_id=data.patient_id,
            timestamp=datetime.utcnow()
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def acknowledge(self, alert_id: int, acknowledged_by: str = None) -> Optional[Alert]:
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None
        alert.acknowledged = True
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def resolve(self, alert_id: int) -> Optional[Alert]:
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None
        alert.is_active = False
        alert.resolved_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def delete(self, alert_id: int) -> bool:
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return False
        self.db.delete(alert)
        self.db.commit()
        return True
    
    def count_active(self) -> int:
        return self.db.query(Alert).filter(Alert.is_active == True).count()

    def check_zone_thresholds(self, zone: Zone):
        """
        Check if zone occupancy exceeds thresholds and create alerts.
        """
        if not zone:
            return

        current = zone.current_occupancy or 0
        warning = zone.warning_threshold
        critical = zone.critical_threshold
        
        # Simple logic: avoid spamming alerts (needs deduplication logic in real app)
        # Checking if there is already an active alert for this zone of this type
        existing_warning = self.db.query(Alert).filter(
            Alert.zone_name == zone.zone_name,
            Alert.is_active == True,
            Alert.severity == AlertSeverity.WARNING
        ).first()
        
        existing_critical = self.db.query(Alert).filter(
            Alert.zone_name == zone.zone_name,
            Alert.is_active == True,
            Alert.severity == AlertSeverity.CRITICAL
        ).first()

        if critical and current >= critical:
            if not existing_critical:
                self.create(AlertCreate(
                    alert_type=AlertType.CAPACITY_CRITICAL,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Critical overcrowding in {zone.zone_name}: {current}/{zone.capacity_limit}",
                    zone_name=zone.zone_name
                ))
        elif warning and current >= warning:
            if not existing_warning:
                # If critical exists, we don't need warning? Or keeping both?
                # Usually keep higher severity.
                self.create(AlertCreate(
                    alert_type=AlertType.CAPACITY_WARNING,
                    severity=AlertSeverity.WARNING,
                    message=f"High occupancy in {zone.zone_name}: {current}/{zone.capacity_limit}",
                    zone_name=zone.zone_name
                ))
