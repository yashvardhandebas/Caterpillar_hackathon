"""
=============================================================================
Layer 2: Core Intelligence — Task Time Prediction
Smart Operator Assistant (Caterpillar Machinery Hackathon)
=============================================================================

Purpose:
  Accurately forecast 'Actual Time (min)' required to complete heavy machinery
  tasks based on site environmental factors, machine state, operator skill,
  and initial time estimates using an XGBoost Regressor.

Explainability for Judges:
  XGBoost (Extreme Gradient Boosting) is an ensemble of decision trees.
  Each successive tree corrects the residual errors of prior trees. It captures
  non-linear relationships (e.g. how severe weather combined with beginner skill
  causes disproportionate delays) without needing complex deep learning.

Features Used:
  - Categorical (Label Encoded):
      'Task Type', 'Site Type', 'Weather', 'Terrain', 'Shift', 'Operator Skill'
  - Numerical:
      'Machine Age (yrs)', 'Ambient Temperature (C)', 'Idling Time (min)',
      'Estimated Time (min)'

Outputs:
  - Trained XGBoost model: 'xgboost_time_model.joblib' (and .json)
  - Fitted Label Encoders: 'label_encoders.joblib'
  - Regression metrics & Feature Importances updated in: 'metrics.json'
=============================================================================
"""

import os
import json
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
import xgboost as xgb

# ---------------------------------------------------------------------------
# Configuration & Feature Definitions
# ---------------------------------------------------------------------------
DATA_PATH = "synthetic_operator_data.csv"
MODEL_SAVE_PATH = "xgboost_time_model.joblib"
MODEL_JSON_PATH = "xgboost_time_model.json"
ENCODERS_SAVE_PATH = "label_encoders.joblib"
METRICS_PATH = "metrics.json"

TARGET_COL = "Actual Time (min)"

CATEGORICAL_FEATURES = [
    "Task Type",
    "Site Type",
    "Weather",
    "Terrain",
    "Shift",
    "Operator Skill"
]

NUMERICAL_FEATURES = [
    "Machine Age (yrs)",
    "Ambient Temperature (C)",
    "Idling Time (min)",
    "Estimated Time (min)"
]

ALL_FEATURES = CATEGORICAL_FEATURES + NUMERICAL_FEATURES


def train_time_predictor(data_path=DATA_PATH):
    """
    Trains the XGBoost regressor, evaluates on an 80/20 train/test split,
    saves the model, encoders, and writes evaluation metrics to metrics.json.
    """
    print("=" * 60)
    print("  LAYER 2: TASK TIME PREDICTION (XGBOOST REGRESSION)")
    print("=" * 60)

    # 1. Load dataset
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Input file not found: {data_path}")

    df = pd.read_csv(data_path)
    print(f"Loaded dataset: {data_path} ({df.shape[0]} rows)")

    # 2. Encode categorical columns using LabelEncoder
    # Save encoders in a dictionary keyed by column name for Layer 3 dashboard
    encoders = {}
    X = pd.DataFrame()

    print("\nEncoding categorical features:")
    for col in CATEGORICAL_FEATURES:
        le = LabelEncoder()
        X[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le
        classes_str = ", ".join(map(str, le.classes_[:4]))
        if len(le.classes_) > 4:
            classes_str += ", ..."
        print(f"  - {col} [{len(le.classes_)} classes]: {classes_str}")

    # Copy numerical features
    for col in NUMERICAL_FEATURES:
        X[col] = df[col].astype(float)

    # Reorder columns to ensure strict feature order alignment
    X = X[ALL_FEATURES]
    y = df[TARGET_COL].astype(float)

    # 3. Train/Test split: 80% train, 20% test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    print(f"\nTrain/Test Split: {len(X_train)} train rows (80%), {len(X_test)} test rows (20%)")

    # 4. Train XGBoost Regressor
    # Parameters are standard, shallow, and fast to prevent overfitting
    model = xgb.XGBRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        random_state=42,
        objective="reg:squarederror"
    )
    print("Fitting XGBoost regressor...")
    model.fit(X_train, y_train)

    # 5. Evaluate on Test Set
    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))

    print("\n--- Model Evaluation (Test Set) ---")
    print(f"  Mean Absolute Error (MAE) : {mae:.2f} minutes")
    print(f"  R-squared Score (R2)      : {r2:.4f}")
    print(f"  Explanation: On average, task predictions are within ~{mae:.1f} minutes of reality.")

    # 6. Feature Importances
    importances = model.feature_importances_
    sorted_features = sorted(
        zip(ALL_FEATURES, importances),
        key=lambda x: x[1],
        reverse=True
    )

    print("\n--- Feature Importances (What drives task duration?) ---")
    feature_importance_dict = {}
    for rank, (feat, imp) in enumerate(sorted_features, start=1):
        pct = imp * 100
        feature_importance_dict[feat] = round(float(imp), 4)
        print(f"  {rank:2d}. {feat:<25} : {imp:.4f} ({pct:5.1f}%)")

    # 7. Save model and encoders
    joblib.dump(model, MODEL_SAVE_PATH)
    model.get_booster().save_model(MODEL_JSON_PATH)
    joblib.dump(encoders, ENCODERS_SAVE_PATH)
    print(f"\n[Saved] Trained XGBoost Model   -> {MODEL_SAVE_PATH}")
    print(f"[Saved] XGBoost JSON format     -> {MODEL_JSON_PATH}")
    print(f"[Saved] Label Encoders Dict     -> {ENCODERS_SAVE_PATH}")

    # 8. Update metrics.json
    metrics_data = {}
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, "r") as f:
                metrics_data = json.load(f)
        except Exception:
            metrics_data = {}

    metrics_data["task_time_prediction"] = {
        "model": "XGBoost Regressor",
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "mae_minutes": round(mae, 2),
        "r2_score": round(r2, 4),
        "feature_importances": feature_importance_dict
    }

    with open(METRICS_PATH, "w") as f:
        json.dump(metrics_data, f, indent=4)
    print(f"[Saved] Regression Metrics      -> {METRICS_PATH}")

    print("=" * 60)
    print("  Task Time Prediction Layer 2 Complete!")
    print("=" * 60)

    return model, encoders, metrics_data["task_time_prediction"]


def predict_task_time(input_dict, model_path=MODEL_SAVE_PATH, encoders_path=ENCODERS_SAVE_PATH):
    """
    Helper for Layer 3 (Dashboard / Live input):
    Takes a dictionary of feature values, encodes categorical fields using the
    saved LabelEncoders, and returns the predicted task duration in minutes.

    Example input_dict:
      {
        'Task Type': 'Demolition',
        'Site Type': 'Construction',
        'Weather': 'Cloudy',
        'Terrain': 'Incline',
        'Shift': 'Day',
        'Operator Skill': 'Beginner',
        'Machine Age (yrs)': 5,
        'Ambient Temperature (C)': 35.5,
        'Idling Time (min)': 37,
        'Estimated Time (min)': 90
      }
    """
    model = joblib.load(model_path)
    encoders = joblib.load(encoders_path)

    row = {}
    # Encode categorical fields
    for col in CATEGORICAL_FEATURES:
        val = str(input_dict[col])
        le = encoders[col]
        # Handle unseen classes gracefully if necessary
        if val in le.classes_:
            row[col] = le.transform([val])[0]
        else:
            # Fallback to class 0
            row[col] = 0

    # Numerical fields
    for col in NUMERICAL_FEATURES:
        row[col] = float(input_dict[col])

    # Convert to DataFrame with strict column order
    X_input = pd.DataFrame([row])[ALL_FEATURES]
    pred_time = model.predict(X_input)[0]
    return float(pred_time)


if __name__ == "__main__":
    train_time_predictor()
