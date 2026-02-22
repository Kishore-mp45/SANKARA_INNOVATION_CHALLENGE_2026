import pickle
import pandas as pd
import numpy as np

model_path = r"C:\PATIENTPATH-AI\ml_models\waiting_model.pkl"
output_file = "sensitivity_v2_output.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    try:
        with open(model_path, 'rb') as mf:
            model = pickle.load(mf)

        features = ['department_code', 'hour', 'day_of_week', 'staff_count', 'service_time']

        f.write("--- Testing Feature Sensitivity (Integers) ---\n")

        # varied dept codes
        for code in [0, 1, 2, 3, 4, 5, 10, 100]:
            df = pd.DataFrame([[code, 10, 2, 5, 15.0]], columns=features)
            try:
                pred = model.predict(df)[0]
                f.write(f"Dept {code}: {pred}\n")
            except Exception as e:
                f.write(f"Dept {code} failed: {e}\n")

        # Change Service Time
        f.write("\n--- Service Time ---\n")
        for st in [5.0, 15.0, 30.0, 60.0]:
            df = pd.DataFrame([[1, 10, 2, 5, st]], columns=features)
            pred = model.predict(df)[0]
            f.write(f"Service Time {st}: {pred}\n")

        # Change Staff Count
        f.write("\n--- Staff Count ---\n")
        for sc in [1, 5, 10, 20]:
            df = pd.DataFrame([[1, 10, 2, sc, 15.0]], columns=features)
            pred = model.predict(df)[0]
            f.write(f"Staff Count {sc}: {pred}\n")

        # Change Hour
        f.write("\n--- Hour ---\n")
        for h in [8, 12, 18, 22]:
            df = pd.DataFrame([[1, h, 2, 5, 15.0]], columns=features)
            pred = model.predict(df)[0]
            f.write(f"Hour {h}: {pred}\n")

    except Exception as e:
        f.write(f"Script failed: {e}\n")
