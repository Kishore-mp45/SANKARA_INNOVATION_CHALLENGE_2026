"""
Extended sensitivity tests for the waiting time model.
Tests edge cases, boundary values, and output ranges.
Run with: pytest tests/test_sensitivity_v2.py -v
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
# Valid codes only: 0–6
VALID_DEPT_CODES = list(range(7))


@pytest.fixture(scope="module")
def model():
    if not os.path.exists(MODEL_PATH):
        pytest.skip(f"waiting_model.pkl not found at {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def _predict(model, day=2, hour=10, window=10, dept=1, staff=5, patients=15):
    df = pd.DataFrame([[day, hour, window, dept, staff, patients]], columns=FEATURES)
    return float(model.predict(df)[0])


# --- All valid department codes produce sane output ---

@pytest.mark.parametrize("dept", VALID_DEPT_CODES)
def test_dept_codes_output_range(model, dept):
    pred = _predict(model, dept=dept)
    assert pred >= 0, f"Dept {dept}: negative prediction {pred}"
    assert pred < 200, f"Dept {dept}: prediction exceeds 200 min ({pred}) — check model"


# --- Service time analogue: varying patient load ---

@pytest.mark.parametrize("patients", [0, 5, 15, 30, 60])
def test_patient_load(model, patients):
    pred = _predict(model, patients=patients)
    assert isinstance(pred, (int, float, np.floating))
    assert pred >= 0


# --- Staff count variations ---

@pytest.mark.parametrize("staff", [1, 5, 10, 20])
def test_staff_count(model, staff):
    pred = _predict(model, staff=staff)
    assert pred >= 0
    assert pred < 200


# --- Hour variations ---

@pytest.mark.parametrize("hour", [8, 12, 18, 22])
def test_hour_variations(model, hour):
    pred = _predict(model, hour=hour)
    assert pred >= 0
    assert np.isfinite(pred)


# --- Predictions are deterministic ---

def test_deterministic(model):
    pred1 = _predict(model)
    pred2 = _predict(model)
    assert pred1 == pred2, "Model must produce identical output for identical input"


# --- Edge case: minimum feature values ---

def test_all_minimum_values(model):
    pred = _predict(model, day=0, hour=0, window=0, dept=0, staff=0, patients=0)
    assert np.isfinite(pred)


# --- Edge case: large values don't crash model ---

def test_large_values(model):
    pred = _predict(model, day=6, hour=23, window=100, dept=6, staff=50, patients=500)
    assert np.isfinite(pred)
    assert pred >= 0
