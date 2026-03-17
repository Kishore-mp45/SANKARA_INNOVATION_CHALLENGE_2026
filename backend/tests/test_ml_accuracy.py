"""
ML Model accuracy and consistency tests.
Tests output ranges, feature sensitivity, and edge cases for all 5 models.
Run with: pytest tests/test_ml_accuracy.py -v
"""
import os
import pickle
import pytest
import numpy as np
import pandas as pd

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_TESTS_DIR))
MODEL_DIR = os.path.join(_PROJECT_ROOT, "ml_models")

VALID_DEPT_CODES = list(range(7))  # 0–6

# Feature sets per model
WAIT_FEATURES = ['day_of_week', 'hour', 'window', 'department_code', 'current_staff', 'active_patients']
ARRIVAL_FEATURES = ['day_of_week', 'hour', 'window', 'lag1', 'rolling_mean_3', 'rolling_std_3']
EXIT_FEATURES = ['day', 'day_of_week', 'hour', 'window', 'is_peak_hour', 'is_low_hour', 'is_week_start']
BOTTLENECK_FEATURES = ['day_of_week', 'hour', 'window', 'department_code', 'current_staff', 'active_patients']
STAFF_FEATURES = ['day_of_week', 'hour', 'window', 'department_code', 'active_patients']


def _load(filename):
    path = os.path.join(MODEL_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"{filename} not found at {path}")
    with open(path, "rb") as f:
        return pickle.load(f)


@pytest.fixture(scope="module")
def wait_model():
    return _load("waiting_model.pkl")


@pytest.fixture(scope="module")
def arrival_model():
    return _load("arrival_model.pkl")


@pytest.fixture(scope="module")
def exit_model():
    return _load("exit_rate_model.pkl")


@pytest.fixture(scope="module")
def bottleneck_model():
    return _load("bottleneck_classification_model.pkl")


@pytest.fixture(scope="module")
def staff_model():
    return _load("staff_allocation_model.pkl")


# =============================================================================
# WAITING TIME MODEL
# =============================================================================

@pytest.mark.parametrize("dept_code", VALID_DEPT_CODES)
def test_wait_model_all_departments(wait_model, dept_code):
    df = pd.DataFrame([[2, 10, 10, dept_code, 5, 15]], columns=WAIT_FEATURES)
    pred = float(wait_model.predict(df)[0])
    assert pred >= 0, f"Negative prediction for dept {dept_code}"
    assert pred < 300, f"Unreasonably large prediction for dept {dept_code}: {pred}"


def test_wait_model_zero_patients(wait_model):
    df = pd.DataFrame([[2, 10, 10, 0, 5, 0]], columns=WAIT_FEATURES)
    pred = float(wait_model.predict(df)[0])
    assert isinstance(pred, (int, float, np.floating))
    assert pred >= 0


@pytest.mark.parametrize("hour", [0, 6, 12, 18, 23])
def test_wait_model_boundary_hours(wait_model, hour):
    df = pd.DataFrame([[2, hour, hour, 0, 5, 10]], columns=WAIT_FEATURES)
    pred = float(wait_model.predict(df)[0])
    assert pred >= 0, f"Negative prediction at hour {hour}"


def test_wait_model_deterministic(wait_model):
    df = pd.DataFrame([[2, 10, 10, 1, 5, 15]], columns=WAIT_FEATURES)
    p1 = float(wait_model.predict(df)[0])
    p2 = float(wait_model.predict(df)[0])
    assert p1 == p2


# =============================================================================
# ARRIVAL MODEL
# =============================================================================

@pytest.mark.parametrize("day", range(7))
def test_arrival_model_all_days(arrival_model, day):
    df = pd.DataFrame([[day, 10, 10, 20, 20.0, 2.0]], columns=ARRIVAL_FEATURES)
    pred = float(arrival_model.predict(df)[0])
    assert pred >= 0, f"Negative arrival prediction for day {day}"


def test_arrival_model_zero_lag(arrival_model):
    df = pd.DataFrame([[0, 10, 10, 0, 0.0, 0.0]], columns=ARRIVAL_FEATURES)
    pred = float(arrival_model.predict(df)[0])
    assert isinstance(pred, (int, float, np.floating))
    assert pred >= 0


def test_arrival_model_uniform_std_zero(arrival_model):
    df = pd.DataFrame([[2, 10, 10, 20, 20.0, 0.0]], columns=ARRIVAL_FEATURES)
    pred = float(arrival_model.predict(df)[0])
    assert pred >= 0


# =============================================================================
# BOTTLENECK CLASSIFICATION MODEL
# =============================================================================

@pytest.mark.parametrize("dept_code", VALID_DEPT_CODES)
def test_bottleneck_model_output_classes(bottleneck_model, dept_code):
    df = pd.DataFrame([[2, 10, 10, dept_code, 5, 15]], columns=BOTTLENECK_FEATURES)
    pred = int(bottleneck_model.predict(df)[0])
    assert pred in (0, 1, 2), f"Invalid bottleneck class {pred} for dept {dept_code}"


def test_bottleneck_model_proba_sums_to_one(bottleneck_model):
    df = pd.DataFrame([[2, 10, 10, 0, 5, 15]], columns=BOTTLENECK_FEATURES)
    if hasattr(bottleneck_model, 'predict_proba'):
        proba = bottleneck_model.predict_proba(df)[0]
        assert abs(sum(proba) - 1.0) < 0.01, f"Probabilities don't sum to 1: {sum(proba)}"


def test_bottleneck_model_high_load(bottleneck_model):
    """High patient count should not cause errors."""
    df = pd.DataFrame([[2, 10, 10, 0, 1, 200]], columns=BOTTLENECK_FEATURES)
    pred = int(bottleneck_model.predict(df)[0])
    assert pred in (0, 1, 2)


# =============================================================================
# EXIT RATE MODEL
# =============================================================================

def test_exit_model_base_case(exit_model):
    df = pd.DataFrame([[15, 2, 10, 10, 1, 0, 0]], columns=EXIT_FEATURES)
    pred = float(exit_model.predict(df)[0])
    assert pred >= 0


@pytest.mark.parametrize("hour", [0, 8, 12, 18, 23])
def test_exit_model_hours(exit_model, hour):
    is_peak = 1 if 8 <= hour <= 18 else 0
    is_low = 1 if hour < 7 or hour > 21 else 0
    df = pd.DataFrame([[15, 2, hour, hour, is_peak, is_low, 0]], columns=EXIT_FEATURES)
    pred = float(exit_model.predict(df)[0])
    assert pred >= 0, f"Negative exit rate at hour {hour}"


# =============================================================================
# STAFF ALLOCATION MODEL
# =============================================================================

@pytest.mark.parametrize("dept_code", VALID_DEPT_CODES)
def test_staff_model_all_departments(staff_model, dept_code):
    df = pd.DataFrame([[2, 10, 10, dept_code, 15]], columns=STAFF_FEATURES)
    pred = float(staff_model.predict(df)[0])
    assert pred >= 0, f"Negative staff prediction for dept {dept_code}"
    assert pred < 100, f"Unreasonably large staff count for dept {dept_code}: {pred}"
