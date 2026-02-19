"""
PatientPath AI - Prediction Router
==================================
API endpoints for AI forecasting.
"""

from fastapi import APIRouter
from services.prediction_service import PredictionService

router = APIRouter(prefix="/prediction", tags=["Prediction"])

@router.get(
    "/forecast",
    summary="Get AI Forecast",
    description="Get real-time AI predictions and decision support items."
)
async def get_forecast():
    """
    Get current AI predictions and recommended actions.
    
    Returns:
        JSON object containing 'predictions' list and 'decisions' list.
    """
    return PredictionService.get_forecast()
