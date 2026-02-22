import pickle
import sys
import os
import sklearn
import numpy as np
import pandas as pd
import xgboost as xgb

model_path = r"C:\PATIENTPATH-AI\ml_models\waiting_model.pkl"
output_file = "inspect_output.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    if not os.path.exists(model_path):
        f.write(f"Error: Model file not found at {model_path}\n")
        sys.exit(1)

    try:
        with open(model_path, 'rb') as mf:
            model = pickle.load(mf)
        
        f.write(f"Model Type: {type(model)}\n")
        f.write(f"Model Object: {model}\n")
        
        if hasattr(model, 'n_features_in_'):
            f.write(f"Number of features expected: {model.n_features_in_}\n")
        else:
            f.write("Attribute 'n_features_in_' not found.\n")

        if hasattr(model, 'feature_names_in_'):
            f.write(f"Feature names: {list(model.feature_names_in_)}\n")
        else:
            f.write("Attribute 'feature_names_in_' not found.\n")
            
        # Try to predict with dummy data if we know expected features
        if hasattr(model, 'n_features_in_'):
            n = model.n_features_in_
            f.write(f"Attempting prediction with {n} zeros...\n")
            try:
                # Reshape to 2D array
                dummy_input = np.zeros((1, n))
                # If it expects pandas dataframe, we might need to use feature names
                if hasattr(model, 'feature_names_in_'):
                     dummy_input = pd.DataFrame(dummy_input, columns=model.feature_names_in_)
                
                pred = model.predict(dummy_input)
                f.write(f"Prediction result: {pred}\n")
            except Exception as e:
                f.write(f"Prediction failed: {e}\n")

    except Exception as e:
        f.write(f"Error loading model: {e}\n")
