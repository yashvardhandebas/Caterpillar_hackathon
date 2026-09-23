"""
=============================================================================
Layer 2: Core Intelligence — Anomaly Detection
Smart Operator Assistant (Caterpillar Machinery Hackathon)
=============================================================================

Purpose:
  Detect operational anomalies (e.g. excessive idling, abnormal fuel burn,
  or irregular load cycles) using an Isolation Forest algorithm.
  
Explainability for Judges:
  Isolation Forest is an unsupervised tree-based algorithm. It isolates
  outliers by randomly partitioning feature values. Outliers and abnormal
  machine states require significantly fewer partitions to isolate than
  normal operating cycles because their metrics deviate from typical patterns.

Features Used:
  - Fuel Used (L)
  - Load Cycles
  - Idling Time (min)
  - Engine Hours

Outputs:
  - Trained model: 'isolation_forest.joblib'
  - Annotated dataset: 'synthetic_operator_data_with_anomalies.csv'
  - Anomaly metrics updated in: 'metrics.json'
=============================================================================
"""

import os
import json
import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

# ---------------------------------------------------------------------------
# Configuration & Paths
# ---------------------------------------------------------------------------
DATA_PATH = "synthetic_operator_data.csv"
OUTPUT_CSV_PATH = "synthetic_operator_data_with_anomalies.csv"
MODEL_SAVE_PATH = "isolation_forest.joblib"
METRICS_PATH = "metrics.json"

ANOMALY_FEATURES = [
    "Fuel Used (L)",
    "Load Cycles",
    "Idling Time (min)",
    "Engine Hours"
]

def train_anomaly_detector(data_path=DATA_PATH):
    """
    Trains the Isolation Forest model on machinery telemetry features,
    adds the anomaly_flag column to the dataframe, and saves the artifacts.
    """
    print("=" * 60)
    print("  LAYER 2: ANOMALY DETECTION (ISOLATION FOREST)")
    print("=" * 60)

    # 1. Load dataset
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Input file not found: {data_path}")
    
    df = pd.read_csv(data_path)
    print(f"Loaded dataset: {data_path} ({df.shape[0]} rows, {df.shape[1]} columns)")

    # 2. Extract anomaly features
    X = df[ANOMALY_FEATURES].copy()
    print(f"Training features ({len(ANOMALY_FEATURES)}): {', '.join(ANOMALY_FEATURES)}")

    # 3. Train Isolation Forest
    # - contamination=0.10: Expected proportion of anomalies (~10% unusual machine events)
    # - random_state=42: Ensures reproducible tree partitions
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.10,
        random_state=42,
        n_jobs=-1
    )
    print("\nFitting Isolation Forest...")
    iso_forest.fit(X)

    # 4. Predict anomaly labels
    # IsolationForest outputs: 1 for inliers (Normal), -1 for outliers (Unusual)
    raw_preds = iso_forest.predict(X)
    df["anomaly_flag"] = ["Normal" if p == 1 else "Unusual" for p in raw_preds]

    # 5. Print class counts and anomaly rate
    counts = df["anomaly_flag"].value_counts()
    normal_count = int(counts.get("Normal", 0))
    unusual_count = int(counts.get("Unusual", 0))
    total_count = len(df)
    anomaly_rate = round(unusual_count / total_count, 4)

    print("\n--- Model Output Class Counts ---")
    print(f"  Normal  : {normal_count} ({normal_count / total_count * 100:.1f}%)")
    print(f"  Unusual : {unusual_count} ({unusual_count / total_count * 100:.1f}%)")
    print(f"  Anomaly Rate : {anomaly_rate * 100:.2f}%\n")

    # 6. Save the trained model
    joblib.dump(iso_forest, MODEL_SAVE_PATH)
    print(f"[Saved] Trained Isolation Forest -> {MODEL_SAVE_PATH}")

    # 7. Save the annotated dataframe
    df.to_csv(OUTPUT_CSV_PATH, index=False)
    print(f"[Saved] Annotated Dataset        -> {OUTPUT_CSV_PATH}")

    # 8. Update metrics.json
    metrics_data = {}
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, "r") as f:
                metrics_data = json.load(f)
        except Exception:
            metrics_data = {}

    metrics_data["anomaly_detection"] = {
        "model": "IsolationForest",
        "features": ANOMALY_FEATURES,
        "total_records": total_count,
        "normal_count": normal_count,
        "unusual_count": unusual_count,
        "anomaly_rate": anomaly_rate,
        "anomaly_rate_percentage": f"{anomaly_rate * 100:.1f}%"
    }

    with open(METRICS_PATH, "w") as f:
        json.dump(metrics_data, f, indent=4)
    print(f"[Saved] Anomaly Metrics          -> {METRICS_PATH}")

    print("=" * 60)
    print("  Anomaly Detection Layer 2 Complete!")
    print("=" * 60)

    return iso_forest, df, metrics_data["anomaly_detection"]


def predict_single_record(fuel_l, load_cycles, idling_min, engine_hrs, model_path=MODEL_SAVE_PATH):
    """
    Helper for Layer 3 (Dashboard / Live input):
    Predicts whether a single machine operation record is Normal or Unusual.
    """
    model = joblib.load(model_path)
    sample = pd.DataFrame([{
        "Fuel Used (L)": fuel_l,
        "Load Cycles": load_cycles,
        "Idling Time (min)": idling_min,
        "Engine Hours": engine_hrs
    }])
    pred = model.predict(sample)[0]
    return "Normal" if pred == 1 else "Unusual"


if __name__ == "__main__":
    train_anomaly_detector()
