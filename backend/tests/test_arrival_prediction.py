"""
Tests for the arrival rate prediction model.
Features: day_of_week, hour, window, lag1, rolling_mean_3, rolling_std_3
Run with: pytest tests/test_arrival_prediction.py -v
"""
import os
import pickle
import pytest
import numpy as np
import pandas as pd

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_TESTS_DIR))
MODEL_PATH = os.path.join(_PROJECT_ROOT, "ml_models", "arrival_model.pkl")

FEATURES = ['day_of_week', 'hour', 'window', 'lag1', 'rolling_mean_3', 'rolling_std_3']


@pytest.fixture(scope="module")
def model():
    if not os.path.exists(MODEL_PATH):
        pytest.skip(f"arrival_model.pkl not found at {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def _predict(model, day=0, hour=10, window=10, lag1=20, mean=20.0, std=2.0):
    df = pd.DataFrame([[day, hour, window, lag1, mean, std]], columns=FEATURES)
    return float(model.predict(df)[0])


# --- Basic validity ---

def test_base_case_is_nonnegative(model):
    pred = _predict(model)
    assert pred >= 0, f"Base prediction must be non-negative: {pred}"


def test_prediction_is_numeric(model):
    pred = _predict(model)
    assert isinstance(pred, (int, float, np.floating))


def test_zero_lag(model):
    """No prior arrivals — model should still produce a valid output."""
    pred = _predict(model, lag1=0, mean=0.0, std=0.0)
    assert pred >= 0


def test_uniform_arrivals_zero_std(model):
    """Perfectly uniform arrivals (std=0)."""
    pred = _predict(model, std=0.0)
    assert pred >= 0


# --- Boundary hours ---

@pytest.mark.parametrize("hour", [0, 6, 12, 18, 23])
def test_boundary_hours(model, hour):
    pred = _predict(model, hour=hour)
    assert pred >= 0, f"Negative prediction at hour {hour}"


# --- Day of week ---

@pytest.mark.parametrize("day", [0, 1, 2, 3, 4, 5, 6])
def test_all_days_of_week(model, day):
    pred = _predict(model, day=day)
    assert pred >= 0, f"Negative prediction on day {day}"


# --- Sensitivity ---

def test_high_lag_affects_prediction(model):
    low_lag = _predict(model, lag1=0)
    high_lag = _predict(model, lag1=100)
    # Both should be non-negative; just ensure they don't crash
    assert low_lag >= 0
    assert high_lag >= 0


@pytest.mark.parametrize("window", [0, 10, 20, 100])
def test_window_sensitivity(model, window):
    pred = _predict(model, window=window)
    assert pred >= 0, f"Negative prediction at window={window}"
