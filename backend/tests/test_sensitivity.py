"""
Feature sensitivity tests for the waiting time model.
Tests how predictions respond to changes in each input feature.
Run with: pytest tests/test_sensitivity.py -v
"""
import os
import pickle
import pytest
import numpy as np
import pandas as pd

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_TESTS_DIR))
MODEL_PATH = os.path.join(_PROJECT_ROOT, "ml_models", "waiting_model.pkl")

FEATURES = ['day_of_week', 'hour', 'window', 'department_code', 'current_staff', 'active_patients']
# Valid department codes: 0=registration, 1=vision_lab, 2=dilation_hall,
# 3=diagnostics, 4=consultation, 5=pharmacy, 6=billing_insurance
VALID_DEPT_CODES = [0, 1, 2, 3, 4, 5, 6]


@pytest.fixture(scope="module")
def model():
    if not os.path.exists(MODEL_PATH):
        pytest.skip(f"waiting_model.pkl not found at {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def _base(model, **overrides):
    row = dict(day_of_week=2, hour=10, window=10, department_code=0, current_staff=5, active_patients=15)
    row.update(overrides)
    df = pd.DataFrame([[row[c] for c in FEATURES]], columns=FEATURES)
    return float(model.predict(df)[0])


# --- Department code sensitivity ---

@pytest.mark.parametrize("dept_code", VALID_DEPT_CODES)
def test_all_valid_department_codes(model, dept_code):
    pred = _base(model, department_code=dept_code)
    assert isinstance(pred, (int, float, np.floating)), f"Dept {dept_code}: non-numeric output"
    assert pred >= 0, f"Dept {dept_code}: negative wait time {pred}"
    assert pred < 500, f"Dept {dept_code}: unreasonably large {pred}"


# --- Staff sensitivity ---

@pytest.mark.parametrize("staff", [1, 3, 5, 10, 20])
def test_staff_count_sensitivity(model, staff):
    pred = _base(model, current_staff=staff)
    assert pred >= 0, f"Negative prediction with {staff} staff"


# --- Patient count sensitivity ---

@pytest.mark.parametrize("patients", [0, 5, 15, 50, 100])
def test_patient_count_sensitivity(model, patients):
    pred = _base(model, active_patients=patients)
    assert pred >= 0, f"Negative prediction with {patients} patients"


# --- Hour sensitivity ---

@pytest.mark.parametrize("hour", [8, 12, 18, 22])
def test_hour_sensitivity(model, hour):
    pred = _base(model, hour=hour)
    assert pred >= 0, f"Negative prediction at hour {hour}"


# --- Predictions are finite ---

def test_predictions_are_finite(model):
    for dept in VALID_DEPT_CODES:
        pred = _base(model, department_code=dept)
        assert np.isfinite(pred), f"Non-finite prediction for dept {dept}"
