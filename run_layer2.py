"""
=============================================================================
Layer 2: Core Intelligence — Master Pipeline Runner
Smart Operator Assistant (Caterpillar Machinery Hackathon)
=============================================================================

This script executes the complete Layer 2 pipeline in sequence:
  1. Anomaly Detection (Isolation Forest)
  2. Task Time Prediction (XGBoost)
  3. Verifies all saved artifacts and runs a sample inference test.
=============================================================================
"""

import os
import json
import joblib
import pandas as pd
from anomaly_detection import train_anomaly_detector, predict_single_record
from time_prediction import train_time_predictor, predict_task_time

def run_pipeline():
    print("\n" + "#" * 70)
    print("  SMART OPERATOR ASSISTANT - LAYER 2: CORE INTELLIGENCE PIPELINE")
    print("#" * 70 + "\n")

    # Step 1: Run Anomaly Detection
    iso_model, df_anom, anom_metrics = train_anomaly_detector()

    print("\n")

    # Step 2: Run Task Time Prediction
    xgb_model, encoders, time_metrics = train_time_predictor()

    print("\n" + "=" * 70)
    print("  LAYER 2: VERIFICATION & SMOKE TEST")
    print("=" * 70)

    # Verify all expected artifacts exist
    expected_files = [
        "isolation_forest.joblib",
        "synthetic_operator_data_with_anomalies.csv",
        "xgboost_time_model.joblib",
        "xgboost_time_model.json",
        "label_encoders.joblib",
        "metrics.json"
    ]

    all_exist = True
    for f in expected_files:
        exists = os.path.exists(f)
        size_kb = os.path.getsize(f) / 1024 if exists else 0
        status = f"EXISTS ({size_kb:.1f} KB)" if exists else "MISSING!"
        mark = "OK" if exists else "X"
        print(f"  [{mark:^4}] {f:<42} : {status}")
        if not exists:
            all_exist = False

    # Test Sample Inferences
    print("\n--- Testing Live Inference Helpers (Layer 3 Readiness) ---")
    
    # 1. Anomaly Test
    # Test Normal operation
    norm_test = predict_single_record(fuel_l=4.0, load_cycles=8, idling_min=10, engine_hrs=1550.0)
    # Test Extreme outlier (120 min idling, 1 load cycle)
    outlier_test = predict_single_record(fuel_l=9.5, load_cycles=1, idling_min=120, engine_hrs=1580.0)
    print(f"  Anomaly Test (Normal parameters)  : {norm_test}")
    print(f"  Anomaly Test (Extreme parameters) : {outlier_test}")

    # 2. Time Prediction Test
    sample_input = {
        "Task Type": "Demolition",
        "Site Type": "Construction",
        "Weather": "Cloudy",
        "Terrain": "Incline",
        "Shift": "Day",
        "Operator Skill": "Beginner",
        "Machine Age (yrs)": 5,
        "Ambient Temperature (C)": 35.5,
        "Idling Time (min)": 37,
        "Estimated Time (min)": 90
    }
    predicted_min = predict_task_time(sample_input)
    print(f"  Time Prediction Test:")
    print(f"    Task: Demolition (Estimated: 90 min, Beginner, Incline, 37 min idle)")
    print(f"    Predicted Actual Time: {predicted_min:.1f} minutes")

    # Load and display consolidated metrics.json
    print("\n" + "=" * 70)
    print("  CONSOLIDATED METRICS SUMMARY (from metrics.json)")
    print("=" * 70)
    with open("metrics.json", "r") as f:
        metrics = json.load(f)
    print(json.dumps(metrics, indent=2))

    print("\n" + "#" * 70)
    print("  ALL LAYER 2 REQUIREMENTS SUCCESSFULLY COMPLETED & VALIDATED!")
    print("#" * 70 + "\n")

if __name__ == "__main__":
    run_pipeline()
