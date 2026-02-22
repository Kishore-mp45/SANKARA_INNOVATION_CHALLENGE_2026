import pickle
import pandas as pd
import numpy as np

model_path = r"C:\PATIENTPATH-AI\ml_models\waiting_model.pkl"

with open(model_path, 'rb') as f:
    model = pickle.load(f)

features = ['department_code', 'hour', 'day_of_week', 'staff_count', 'service_time']

print("--- Testing Feature Sensitivity ---")

# Base case
base_df = pd.DataFrame([['REGISTRATION', 10, 2, 5, 15.0]], columns=features)
base_pred = model.predict(base_df)[0]
print(f"Base (REGISTRATION, 10h, Tue, 5 staff, 15m service): {base_pred}")

# Change Department
dept_df = pd.DataFrame([['TRIAGE', 10, 2, 5, 15.0]], columns=features)
dept_pred = model.predict(dept_df)[0]
print(f"TRIAGE: {dept_pred}")

# Change Service Time (expect big change?)
service_df = pd.DataFrame([['REGISTRATION', 10, 2, 5, 30.0]], columns=features)
service_pred = model.predict(service_df)[0]
print(f"Service Time 30m: {service_pred}")

# Change Staff Count (expect big change?)
staff_df = pd.DataFrame([['REGISTRATION', 10, 2, 1, 15.0]], columns=features)
staff_pred = model.predict(staff_df)[0]
print(f"Staff Count 1: {staff_pred}")

# Change Dept to Number
num_dept_df = pd.DataFrame([[1, 10, 2, 5, 15.0]], columns=features)
num_dept_pred = model.predict(num_dept_df)[0]
print(f"Dept 1 (int): {num_dept_pred}")
