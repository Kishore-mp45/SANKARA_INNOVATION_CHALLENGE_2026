"""
Risk Engine - AI-powered Alert Severity Classification & Department Risk Scoring
=================================================================================
Collects prediction outputs from all 5 ML models for each hospital department
and calculates:
  1. Alert Severity Level (CRITICAL / WARNING / INFO)
  2. Department Risk Score (0-100)
"""

import math
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from services.prediction_service import PredictionService
from services.staff_allocation_service import StaffAllocationService
from models.zone import Zone
from models.patient import Patient, PatientStatus


class RiskEngine:
    """Aggregates ML model outputs into severity levels and risk scores."""

    # Display names for departments
    DEPARTMENT_DISPLAY = PredictionService.DEPARTMENT_DISPLAY

    # Department-specific waiting time thresholds (minutes)
    WAIT_THRESHOLDS = {
        "registration": 15,
        "consultation": 25,
        "diagnostics": 30,
        "vision_lab": 20,
        "dilation_hall": 45,
        "pharmacy": 15,
        "billing_insurance": 10,
    }

    # Max expected values for normalisation
    MAX_WAITING_TIME = 60.0    # minutes
    MAX_ARRIVAL_RATE = 30.0    # patients/hour
    MAX_STAFF_DEFICIT = 5.0
    MAX_EXIT_RATE = 25.0       # patients/hour

    # Risk score weights (must sum to 1.0)
    W_WAITING    = 0.30
    W_BOTTLENECK = 0.25
    W_ARRIVAL    = 0.15  # reduced to give more weight to exit slowdown
    W_STAFF      = 0.15
    W_EXIT       = 0.15  # increased: a zone with 0 exits is a strong risk signal

    # Hysteresis state — prevent alert flapping on small value changes
    _last_severity: Dict[str, str] = {}
    _severity_streak: Dict[str, int] = {}

    # Severity icons
    SEVERITY_ICONS = {
        "CRITICAL": "\U0001f534",   # 🔴
        "WARNING":  "\U0001f7e1",   # 🟡
        "INFO":     "\U0001f535",   # 🔵
    }

    SEVERITY_MESSAGES = {
        "CRITICAL": "Severe congestion detected. Immediate intervention recommended.",
        "WARNING":  "Elevated load detected. Monitor closely and prepare to act.",
        "INFO":     "Operating within normal parameters. No action required.",
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def get_intelligent_alerts(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Gather predictions from all 5 ML models for every department,
        classify severity, compute risk score, and return sorted results.
        """
        now = datetime.now()

        # ---- Collect global predictions (computed once) ----
        arrival_data = PredictionService.predict_arrival_rate(db)
        exit_data = PredictionService.predict_exit_rate(db)
        bottleneck_data = PredictionService.predict_bottleneck(db)
        staff_data = StaffAllocationService.get_all_recommendations(db)

        # Index bottleneck predictions by zone_name
        bottleneck_by_zone: Dict[str, Dict] = {}
        for p in bottleneck_data.get("predictions", []):
            bottleneck_by_zone[p["zone_name"]] = p

        # Index staff data by zone_name
        staff_by_zone: Dict[str, Dict] = {}
        for s in staff_data:
            staff_by_zone[s.get("zone_name", "")] = s

        predicted_arrival_rate = arrival_data.get("predicted_arrival_rate", 0)
        predicted_exit_rate = exit_data.get("predicted_exit_rate", 0)

        results: List[Dict[str, Any]] = []

        for zone_name in PredictionService.DEPARTMENT_MAP:
            try:
                alert = cls._evaluate_department(
                    db=db,
                    zone_name=zone_name,
                    bottleneck_info=bottleneck_by_zone.get(zone_name, {}),
                    staff_info=staff_by_zone.get(zone_name, {}),
                    predicted_arrival_rate=predicted_arrival_rate,
                    predicted_exit_rate=predicted_exit_rate,
                )
                results.append(alert)
            except Exception as e:
                # Graceful fallback — INFO level if prediction fails
                display_name = cls.DEPARTMENT_DISPLAY.get(zone_name, zone_name)
                results.append({
                    "department": display_name,
                    "zone_name": zone_name,
                    "severity": "INFO",
                    "icon": cls.SEVERITY_ICONS["INFO"],
                    "risk_score": 0,
                    "predicted_waiting_time": 0,
                    "staff_required": 0,
                    "staff_available": 0,
                    "staff_deficit": 0,
                    "bottleneck_probability": 0.0,
                    "arrival_rate": predicted_arrival_rate,
                    "exit_rate": predicted_exit_rate,
                    "message": f"Prediction unavailable: {str(e)}. Defaulting to INFO.",
                })

        # Sort by risk_score descending (highest risk first)
        results.sort(key=lambda x: x["risk_score"], reverse=True)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _evaluate_department(
        cls,
        db: Session,
        zone_name: str,
        bottleneck_info: Dict,
        staff_info: Dict,
        predicted_arrival_rate: float,
        predicted_exit_rate: float,
    ) -> Dict[str, Any]:
        """Evaluate a single department and return its alert dict."""

        display_name = cls.DEPARTMENT_DISPLAY.get(zone_name, zone_name)

        # ---- 1. Predicted waiting time (per department) ----
        wait_data = PredictionService.predict_department_wait(db, zone_name)
        predicted_waiting = wait_data.get("predicted_minutes") or 0.0

        # ---- 2. Bottleneck probability ----
        # predict_proba gives class probabilities; class_id 2 = severe
        bn_class_id = bottleneck_info.get("class_id", 0)
        bn_confidence_value = bottleneck_info.get("confidence_value", 0.0)
        # Convert to a 0-1 probability representing congestion risk
        if bn_class_id == 2:
            bottleneck_prob = bn_confidence_value / 100.0
        elif bn_class_id == 1:
            bottleneck_prob = (bn_confidence_value / 100.0) * 0.6
        else:
            bottleneck_prob = (1.0 - bn_confidence_value / 100.0) * 0.2

        # ---- 3. Staff info ----
        optimal_staff = staff_info.get("optimal_staff", 1)
        current_staff = staff_info.get("current_staff", 1)
        staff_deficit = max(0, optimal_staff - current_staff)

        # ---- 4. Exit rate slowdown ----
        # Higher exit rate = good (patients leaving); lower = slowdown risk
        # Invert so that low exit = high risk contribution
        exit_rate_slowdown = max(0.0, 1.0 - (predicted_exit_rate / cls.MAX_EXIT_RATE)) if cls.MAX_EXIT_RATE > 0 else 0.0

        # ---- Determine severity ----
        wait_threshold = cls.WAIT_THRESHOLDS.get(zone_name, 20)

        severity = cls._classify_severity(
            bottleneck_prob=bottleneck_prob,
            predicted_waiting=predicted_waiting,
            wait_threshold=wait_threshold,
            staff_deficit=staff_deficit,
            predicted_arrival_rate=predicted_arrival_rate,
            bn_class_id=bn_class_id,
            zone_name=zone_name,
        )

        # ---- Compute risk score (0 – 100) ----
        risk_score = cls._compute_risk_score(
            predicted_waiting=predicted_waiting,
            bottleneck_prob=bottleneck_prob,
            predicted_arrival_rate=predicted_arrival_rate,
            staff_deficit=staff_deficit,
            exit_rate_slowdown=exit_rate_slowdown,
        )

        message = cls.SEVERITY_MESSAGES[severity]

        return {
            "department": display_name,
            "zone_name": zone_name,
            "severity": severity,
            "icon": cls.SEVERITY_ICONS[severity],
            "risk_score": risk_score,
            "predicted_waiting_time": round(predicted_waiting, 1),
            "staff_required": optimal_staff,
            "staff_available": current_staff,
            "staff_deficit": staff_deficit,
            "bottleneck_probability": round(bottleneck_prob, 2),
            "arrival_rate": predicted_arrival_rate,
            "exit_rate": predicted_exit_rate,
            "message": message,
        }

    @classmethod
    def _raw_classify_severity(
        cls,
        bottleneck_prob: float,
        predicted_waiting: float,
        wait_threshold: float,
        staff_deficit: int,
        predicted_arrival_rate: float,
        bn_class_id: int,
    ) -> str:
        """Raw severity classification without hysteresis."""
        # --- CRITICAL conditions ---
        if bottleneck_prob > 0.8 and staff_deficit >= 2:
            return "CRITICAL"
        if predicted_waiting > wait_threshold and staff_deficit >= 2:
            return "CRITICAL"
        if bn_class_id == 2 and staff_deficit >= 2:
            return "CRITICAL"
        if bn_class_id == 2 and predicted_waiting > wait_threshold:
            return "CRITICAL"

        # --- WARNING conditions ---
        if predicted_arrival_rate > (cls.MAX_ARRIVAL_RATE * 0.5):
            return "WARNING"
        if predicted_waiting > (wait_threshold * 0.7):
            return "WARNING"
        if staff_deficit >= 1:
            return "WARNING"
        if bn_class_id == 1:
            return "WARNING"

        # --- INFO ---
        return "INFO"

    @classmethod
    def _classify_severity(
        cls,
        bottleneck_prob: float,
        predicted_waiting: float,
        wait_threshold: float,
        staff_deficit: int,
        predicted_arrival_rate: float,
        bn_class_id: int,
        zone_name: str = "",
    ) -> str:
        """
        Severity classification with hysteresis to prevent alert flapping.
        A new severity level is only adopted after 2 consecutive identical readings.

        CRITICAL (🔴): severe bottleneck + staff shortage, or very high wait + no staff
        WARNING  (🟡): elevated load, high arrivals, or mild staff deficit
        INFO     (🔵): operating normally
        """
        new_severity = cls._raw_classify_severity(
            bottleneck_prob, predicted_waiting, wait_threshold,
            staff_deficit, predicted_arrival_rate, bn_class_id
        )

        if not zone_name:
            return new_severity

        last = cls._last_severity.get(zone_name, new_severity)
        if new_severity == last:
            cls._severity_streak[zone_name] = cls._severity_streak.get(zone_name, 0) + 1
        else:
            cls._severity_streak[zone_name] = 1

        # Adopt new severity only after 2 consecutive identical readings (hysteresis)
        if cls._severity_streak.get(zone_name, 0) >= 2:
            cls._last_severity[zone_name] = new_severity

        return cls._last_severity.get(zone_name, new_severity)

    @classmethod
    def _compute_risk_score(
        cls,
        predicted_waiting: float,
        bottleneck_prob: float,
        predicted_arrival_rate: float,
        staff_deficit: int,
        exit_rate_slowdown: float,
    ) -> int:
        """
        Weighted risk score 0-100:
            0.30 * normalised_waiting_time
          + 0.25 * bottleneck_probability
          + 0.20 * normalised_arrival_rate
          + 0.15 * staff_deficit_ratio
          + 0.10 * exit_rate_slowdown
        """
        norm_waiting = min(predicted_waiting / cls.MAX_WAITING_TIME, 1.0)
        norm_bottleneck = min(bottleneck_prob, 1.0)
        norm_arrival = min(predicted_arrival_rate / cls.MAX_ARRIVAL_RATE, 1.0)
        norm_staff = min(staff_deficit / cls.MAX_STAFF_DEFICIT, 1.0)
        norm_exit = min(exit_rate_slowdown, 1.0)

        raw = (
            cls.W_WAITING    * norm_waiting
            + cls.W_BOTTLENECK * norm_bottleneck
            + cls.W_ARRIVAL    * norm_arrival
            + cls.W_STAFF      * norm_staff
            + cls.W_EXIT       * norm_exit
        )

        score = int(round(raw * 100))
        return max(0, min(score, 100))
