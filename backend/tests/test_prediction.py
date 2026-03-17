"""
Tests for the waiting time prediction model.
Uses correct model features as defined in PredictionService.WAIT_MODEL_FEATURES.
Run with: pytest tests/test_prediction.py -v
"""
import os
import sys
import pickle
import pytest
import numpy as np

import pandas as pd

# Relative path from backend/tests/ to ml_models/
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_TESTS_DIR))
MODEL_PATH = os.path.join(_PROJECT_ROOT, "ml_models", "waiting_model.pkl")

FEATURES = ['day_of_week', 'hour', 'window', 'department_code', 'current_staff', 'active_patients']
VALID_DEPT_CODES = [0, 1, 2, 3, 4, 5, 6]


@pytest.fixture(scope="module")
def model():
    if not os.path.exists(MODEL_PATH):
        pytest.skip(f"waiting_model.pkl not found at {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def _predict(model, dept_code, hour=10, day=2, window=10, staff=5, patients=15):
    df = pd.DataFrame(
        [[day, hour, window, dept_code, staff, patients]],
        columns=FEATURES
    )
    return float(model.predict(df)[0])


# --- Basic validity tests ---

@pytest.mark.parametrize("dept_code", VALID_DEPT_CODES)
def test_valid_department_codes(model, dept_code):
    pred = _predict(model, dept_code)
    assert pred >= 0, f"Negative wait time for dept {dept_code}: {pred}"
    assert pred < 500, f"Unreasonably large prediction for dept {dept_code}: {pred}"


def test_prediction_is_numeric(model):
    pred = _predict(model, dept_code=0)
    assert isinstance(pred, (int, float, np.floating)), "Prediction must be numeric"


def test_zero_patients(model):
    pred = _predict(model, dept_code=0, patients=0)
    assert pred >= 0, "Wait time cannot be negative with 0 patients"


def test_high_patient_count(model):
    pred = _predict(model, dept_code=0, patients=100)
    assert pred >= 0


# --- Boundary value tests ---

@pytest.mark.parametrize("hour", [0, 6, 12, 18, 23])
def test_boundary_hours(model, hour):
    pred = _predict(model, dept_code=1, hour=hour)
    assert pred >= 0, f"Negative prediction at hour {hour}"


@pytest.mark.parametrize("day", [0, 1, 2, 3, 4, 5, 6])
def test_boundary_days_of_week(model, day):
    pred = _predict(model, dept_code=1, day=day)
    assert pred >= 0, f"Negative prediction on day_of_week={day}"


def test_all_zero_features(model):
    df = pd.DataFrame([[0, 0, 0, 0, 0, 0]], columns=FEATURES)
    pred = float(model.predict(df)[0])
    assert isinstance(pred, (int, float, np.floating)), "All-zero input must yield numeric output"


# --- Sensitivity tests ---

def test_more_patients_increases_or_equal_wait(model):
    low = _predict(model, dept_code=0, patients=5)
    high = _predict(model, dept_code=0, patients=50)
    assert high >= low - 1, "More patients should not dramatically decrease wait time"


def test_more_staff_does_not_increase_wait(model):
    few = _predict(model, dept_code=0, staff=1)
    many = _predict(model, dept_code=0, staff=20)
    assert many <= few + 5, "Many staff should not greatly increase wait time vs few"
