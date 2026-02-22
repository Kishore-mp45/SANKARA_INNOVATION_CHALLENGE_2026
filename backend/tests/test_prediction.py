import pickle
import pandas as pd
import numpy as np

model_path = r"C:\PATIENTPATH-AI\ml_models\waiting_model.pkl"

with open(model_path, 'rb') as f:
    model = pickle.load(f)

# Features: ['department_code', 'hour', 'day_of_week', 'staff_count', 'service_time']
features = ['department_code', 'hour', 'day_of_week', 'staff_count', 'service_time']

# Test with String
print("Testing with String department_code...")
try:
    df = pd.DataFrame([['REGISTRATION', 10, 2, 5, 15.0]], columns=features)
    pred = model.predict(df)
    print(f"Success with String! Prediction: {pred[0]}")
except Exception as e:
    print(f"Failed with String: {e}")

# Test with Integer
print("\nTesting with Integer department_code...")
try:
    df = pd.DataFrame([[1, 10, 2, 5, 15.0]], columns=features)
    pred = model.predict(df)
    print(f"Success with Integer! Prediction: {pred[0]}")
except Exception as e:
    print(f"Failed with Integer: {e}")
