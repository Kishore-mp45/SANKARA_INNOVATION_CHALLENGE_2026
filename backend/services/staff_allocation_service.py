"""Staff Allocation Service - AI-powered staff recommendation using XGBRegressor model."""

import os
import pickle
import math
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models.zone import Zone
from models.patient import Patient, PatientStatus


class StaffAllocationService:
    _model = None
    _model_path = r"C:\PATIENTPATH-AI\ml_models\staff_allocation_model.pkl"

    # Department code mapping (matching model training)
    DEPARTMENT_MAP = {
        "registration": 0,
        "consultation": 1,
        "diagnostics": 2,
        "vision_lab": 3,
        "dilation_hall": 4,
        "pharmacy": 5,
        "billing_insurance": 6,
    }

    DEPARTMENT_DISPLAY = {
        "registration": "Registration",
        "consultation": "Consultation",
        "diagnostics": "Diagnostics",
        "vision_lab": "Vision Lab",
        "dilation_hall": "Dilation Hall",
        "pharmacy": "Pharmacy",
        "billing_insurance": "Billing & Insurance",
    }

    # Default current staff per department (in-memory tracking)
    _current_staff: Dict[str, int] = {
        "registration": 2,
        "vision_lab": 2,
        "dilation_hall": 1,
        "consultation": 2,
        "diagnostics": 1,
        "pharmacy": 2,
        "billing_insurance": 1,
    }

    @classmethod
    def _load_model(cls):
        """Load the staff allocation model if not already loaded."""
        if cls._model is None:
            if os.path.exists(cls._model_path):
                try:
                    with open(cls._model_path, "rb") as f:
                        cls._model = pickle.load(f)
                    print(f"Loaded staff allocation model from {cls._model_path}")
                except Exception as e:
                    print(f"Error loading staff allocation model: {e}")
            else:
                print(f"Staff allocation model not found at {cls._model_path}")
        return cls._model

    @classmethod
    def _get_active_patients(cls, db: Session, zone_name: str) -> int:
        """Get active patient count for a zone from the database."""
        zone = db.query(Zone).filter(Zone.zone_name == zone_name).first()
        if zone:
            return zone.current_occupancy
        return 0

    @classmethod
    def get_current_staff(cls, zone_name: str) -> int:
        """Get current staff count for a department."""
        return max(0, cls._current_staff.get(zone_name, 1))

    @classmethod
    def predict_optimal_staff(cls, db: Session, zone_name: str) -> Dict[str, Any]:
        """
        Predict optimal staff for a department using the ML model.
        Model features: day_of_week, hour, window, department_code, active_patients
        Returns recommendation with deficit calculation.
        """
        model = cls._load_model()
        dept_code = cls.DEPARTMENT_MAP.get(zone_name)
        display_name = cls.DEPARTMENT_DISPLAY.get(zone_name, zone_name)

        if dept_code is None:
            return {
                "department": zone_name,
                "error": f"Unknown department: {zone_name}",
                "is_bottleneck": False
            }

        active_patients = cls._get_active_patients(db, zone_name)
        current_staff = cls.get_current_staff(zone_name)
        now = datetime.now()

        if not model:
            return {
                "department": display_name,
                "active_patients": active_patients,
                "current_staff": current_staff,
                "optimal_staff": current_staff,
                "deficit": 0,
                "is_bottleneck": False,
                "message": "Model unavailable, using defaults."
            }

        try:
            features = ['day_of_week', 'hour', 'window', 'department_code', 'active_patients']
            input_data = pd.DataFrame([[
                now.weekday(),
                now.hour,
                1,  # window
                dept_code,
                active_patients
            ]], columns=features)

            predicted = float(model.predict(input_data)[0])
            optimal_staff = max(1, math.ceil(predicted))
            deficit = optimal_staff - current_staff
            is_bottleneck = deficit > 0

            return {
                "department": display_name,
                "active_patients": active_patients,
                "current_staff": current_staff,
                "optimal_staff": optimal_staff,
                "deficit": max(0, deficit),
                "is_bottleneck": is_bottleneck
            }
        except Exception as e:
            print(f"Staff allocation prediction error: {e}")
            return {
                "department": display_name,
                "active_patients": active_patients,
                "current_staff": current_staff,
                "optimal_staff": current_staff,
                "deficit": 0,
                "is_bottleneck": False,
                "message": f"Prediction error: {str(e)}"
            }

    @classmethod
    def checkin_staff(cls, zone_name: str, db: Session) -> Dict[str, Any]:
        """
        Check in a staff member to a department.
        Increments current_staff by 1, then recalculates deficit.
        """
        if zone_name not in cls.DEPARTMENT_MAP:
            return {"error": f"Unknown department: {zone_name}"}

        cls._current_staff[zone_name] = cls.get_current_staff(zone_name) + 1

        # Recalculate with updated staff count
        result = cls.predict_optimal_staff(db, zone_name)
        result["message"] = f"Staff checked in to {cls.DEPARTMENT_DISPLAY.get(zone_name, zone_name)}. Current staff: {cls._current_staff[zone_name]}"
        return result

    @classmethod
    def get_all_recommendations(cls, db: Session) -> List[Dict[str, Any]]:
        """Get staff recommendations for all departments."""
        results = []
        for zone_name in cls.DEPARTMENT_MAP:
            rec = cls.predict_optimal_staff(db, zone_name)
            rec["zone_name"] = zone_name
            results.append(rec)
        return results
