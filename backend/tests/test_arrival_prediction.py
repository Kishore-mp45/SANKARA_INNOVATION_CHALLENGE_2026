import pickle
import pandas as pd
import numpy as np

model_path = r"C:\PATIENTPATH-AI\ml_models\arrival_model.pkl"

with open(model_path, 'rb') as f:
    model = pickle.load(f)

# Features: day_of_week, hour, window, lag1, rolling_mean_3, rolling_std_3
features = ['day_of_week', 'hour', 'window', 'lag1', 'rolling_mean_3', 'rolling_std_3']

print("--- Testing Arrival Model Sensitivity ---")

# Base case: Monday (0), 10 AM, window=10, lag=20, mean=20, std=2
base_row = [0, 10, 10, 20, 20.0, 2.0]
base_df = pd.DataFrame([base_row], columns=features)
base_pred = model.predict(base_df)[0]
print(f"Base: {base_pred}")

# Test Window Sensitivity
for w in [0, 10, 20, 100]:
    row = list(base_row)
    row[2] = w # window
    df = pd.DataFrame([row], columns=features)
    pred = model.predict(df)[0]
    print(f"Window {w}: {pred}")

# Test Lag Sensitivity
for l in [0, 10, 50]:
    row = list(base_row)
    row[3] = l # lag1
    df = pd.DataFrame([row], columns=features)
    pred = model.predict(df)[0]
    print(f"Lag {l}: {pred}")
