# Smart Operator Assistant — Caterpillar Hackathon

## Layer 2: Core Intelligence (Anomaly Detection & Task Time Prediction)

This repository contains **Layer 2 (Core Intelligence)** of the Smart Operator Assistant built for the Caterpillar machinery hackathon.

Layer 2 provides fast, explainable, lightweight machine learning models with zero external API dependencies or deep learning overhead.

---

### Features & Architecture

1. **Anomaly Detection (Isolation Forest)**
   - Unsupervised outlier detection built on scikit-learn's `IsolationForest`.
   - Trained on 4 core telemetry features:
     - `Fuel Used (L)`
     - `Load Cycles`
     - `Idling Time (min)`
     - `Engine Hours`
   - Classifies operations into **Normal (90.0%)** and **Unusual (10.0%)**.
   - Model saved as: `isolation_forest.joblib`

2. **Task Time Prediction (XGBoost Regressor)**
   - Supervised gradient-boosted regression predicting `Actual Time (min)`.
   - Features: `Task Type`, `Site Type`, `Weather`, `Terrain`, `Shift`, `Operator Skill`, `Machine Age (yrs)`, `Ambient Temperature (C)`, `Idling Time (min)`, `Estimated Time (min)`.
   - Categorical fields encoded via `LabelEncoder` (stored in `label_encoders.joblib`).
   - Performance:
     - **MAE:** 4.46 minutes
     - **R² Score:** 0.9724 (97.2% variance explained)
   - Models saved as: `xgboost_time_model.joblib` and `xgboost_time_model.json`

---

### Repository Structure

```text
├── anomaly_detection.py                       # Standalone Anomaly Detection module
├── time_prediction.py                          # Standalone Task Time Prediction module
├── run_layer2.py                               # Master pipeline runner and verification
├── EXPLAINABILITY_GUIDE.md                     # Judge Q&A & non-technical pitch guide
├── synthetic_operator_data.csv                 # Layer 1 dataset (800 records)
├── synthetic_operator_data_with_anomalies.csv  # Augmented dataset with anomaly_flag
├── isolation_forest.joblib                     # Trained Isolation Forest model
├── xgboost_time_model.joblib                   # Trained XGBoost model
├── xgboost_time_model.json                     # Native XGBoost JSON booster
├── label_encoders.joblib                       # Saved LabelEncoders dictionary
├── metrics.json                                # Performance metrics & feature importances
└── README.md
```

---

### How to Run

#### 1. Run Anomaly Detection Only
```bash
python anomaly_detection.py
```

#### 2. Run Task Time Prediction Only
```bash
python time_prediction.py
```

#### 3. Run Complete Pipeline & Smoke Tests
```bash
python run_layer2.py
```

---

### Metrics Summary (`metrics.json`)

```json
{
  "anomaly_detection": {
    "model": "IsolationForest",
    "total_records": 800,
    "normal_count": 720,
    "unusual_count": 80,
    "anomaly_rate": 0.1,
    "anomaly_rate_percentage": "10.0%"
  },
  "task_time_prediction": {
    "model": "XGBoost Regressor",
    "mae_minutes": 4.46,
    "r2_score": 0.9724,
    "feature_importances": {
      "Task Type": 0.7816,
      "Operator Skill": 0.0981,
      "Estimated Time (min)": 0.0733,
      "Terrain": 0.0183,
      "Weather": 0.0108,
      "Idling Time (min)": 0.0106,
      "Machine Age (yrs)": 0.0031,
      "Ambient Temperature (C)": 0.0019,
      "Site Type": 0.0012,
      "Shift": 0.0011
    }
  }
}
```
