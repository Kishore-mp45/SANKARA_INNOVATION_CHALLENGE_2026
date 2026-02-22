import pickle
import sys
import os
import pandas as pd
import numpy as np
import xgboost as xgb

model_path = r"C:\PATIENTPATH-AI\ml_models\arrival_model.pkl"

if not os.path.exists(model_path):
    print(f"Error: Model file not found at {model_path}")
    sys.exit(1)

try:
    with open(model_path, 'rb') as mf:
        model = pickle.load(mf)
    
    print(f"Model Type: {type(model)}")
    
    if hasattr(model, 'feature_names_in_'):
        print("Feature names:")
        for feature in model.feature_names_in_:
            print(f"- {feature}")
        
except Exception as e:
    print(f"Error loading model: {e}")
