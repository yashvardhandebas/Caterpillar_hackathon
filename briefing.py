"""
=============================================================================
Pre-Shift Briefing Module
Smart Operator Assistant (Caterpillar Machinery Hackathon)
=============================================================================

Purpose:
  Generate a concise pre-shift briefing for operators showing:
  1. Today's tasks with time predictions vs CAT estimates
  2. Today's biggest risk task with risk band and contributing factors
  3. One thing to watch based on operator's historical issues

Design Principles:
  - Large text, high contrast for glove-wearing operators
  - Readable in ~10 seconds
  - Deterministic logic (no LLM/API calls)
  - Uses existing Layer 2 and Layer 3 components
=============================================================================
"""

import pandas as pd
import joblib
import numpy as np
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Configuration & Paths
# ---------------------------------------------------------------------------
DATA_PATH = "synthetic_operator_data_with_anomalies.csv"
TIME_MODEL_PATH = "xgboost_time_model.joblib"
ENCODERS_PATH = "label_encoders.joblib"

# Fixed seed for deterministic demo
DEMO_SEED = 42
DEMO_OPERATOR_ID = "OP1007"  # Fixed operator for demo consistency

# Feature definitions from time_prediction.py
CATEGORICAL_FEATURES = [
    "Task Type", "Site Type", "Weather", "Terrain", "Shift", "Operator Skill"
]

NUMERICAL_FEATURES = [
    "Machine Age (yrs)", "Ambient Temperature (C)", "Idling Time (min)", "Estimated Time (min)"
]

ALL_FEATURES = CATEGORICAL_FEATURES + NUMERICAL_FEATURES


class PreShiftBriefing:
    """
    Generate pre-shift briefings for operators using existing Layer 2 and Layer 3 components.
    """
    
    def __init__(self, data_path: str = DATA_PATH, 
                 time_model_path: str = TIME_MODEL_PATH,
                 encoders_path: str = ENCODERS_PATH):
        """
        Initialize the briefing generator with required models and data.
        """
        self.data_path = data_path
        self.time_model_path = time_model_path
        self.encoders_path = encoders_path
        
        # Load data and models
        self.df = pd.read_csv(data_path)
        self.time_model = joblib.load(time_model_path)
        self.encoders = joblib.load(encoders_path)
        
        # Set random seed for deterministic demo
        np.random.seed(DEMO_SEED)
        
    def _predict_task_time(self, task_row: pd.Series) -> float:
        """
        Predict task time using Layer 2 XGBoost model.
        
        Uses the existing predict_task_time logic from time_prediction.py.
        """
        # Build input dictionary from task row
        input_dict = {
            'Task Type': task_row['Task Type'],
            'Site Type': task_row['Site Type'],
            'Weather': task_row['Weather'],
            'Terrain': task_row['Terrain'],
            'Shift': task_row['Shift'],
            'Operator Skill': task_row['Operator Skill'],
            'Machine Age (yrs)': task_row['Machine Age (yrs)'],
            'Ambient Temperature (C)': task_row['Ambient Temperature (C)'],
            'Idling Time (min)': task_row['Idling Time (min)'],
            'Estimated Time (min)': task_row['Estimated Time (min)']
        }
        
        # Encode categorical fields
        row = {}
        for col in CATEGORICAL_FEATURES:
            val = str(input_dict[col])
            le = self.encoders[col]
            if val in le.classes_:
                row[col] = le.transform([val])[0]
            else:
                row[col] = 0  # Fallback to class 0
        
        # Numerical fields
        for col in NUMERICAL_FEATURES:
            row[col] = float(input_dict[col])
        
        # Convert to DataFrame with strict column order
        X_input = pd.DataFrame([row])[ALL_FEATURES]
        pred_time = self.time_model.predict(X_input)[0]
        return float(pred_time)
        
    def _calculate_ml_anomaly_score(self, task_row: pd.Series) -> float:
        """
        Calculate a normalized anomaly score for Layer 3 fuzzy engine.
        
        Since we don't have the isolation forest model loaded, we use the
        existing anomaly_flag column and create a deterministic score.
        """
        # Use anomaly_flag to create a deterministic score
        anomaly_flag = task_row.get('anomaly_flag', 'Normal')
        
        # Deterministic mapping based on task characteristics
        # Higher anomaly for unusual combinations
        base_score = 0.1 if anomaly_flag == 'Normal' else 0.7
        
        # Adjust based on idling time (higher idling = more suspicious)
        idling = task_row['Idling Time (min)']
        if idling > 30:
            base_score += 0.2
        elif idling > 20:
            base_score += 0.1
            
        # Adjust based on fuel usage
        fuel = task_row['Fuel Used (L)']
        if fuel > 5.0:
            base_score += 0.1
            
        # Cap at 1.0
        return min(base_score, 1.0)
        
    def _evaluate_task_risk(self, task_row: pd.Series) -> Dict:
        """
        Evaluate risk for a single task using deterministic heuristic logic.
        
        Uses simplified risk assessment that's deterministic and fast for briefing.
        """
        # Get task parameters
        proximity = float(task_row['Proximity Distance (m)'])
        seatbelt = 1.0 if task_row['Seatbelt Status'] == 'Fastened' else 0.0
        anomaly = self._calculate_ml_anomaly_score(task_row)
        site_type = task_row['Site Type']
        
        # Deterministic risk score calculation
        risk_score = 0
        
        # Proximity risk
        if proximity < 2.0:
            risk_score += 50  # Critical proximity
        elif proximity < 4.0:
            risk_score += 30  # Warning proximity
        elif proximity < 7.0:
            risk_score += 15  # Caution proximity
        
        # Seatbelt risk
        if seatbelt == 0.0:
            risk_score += 35  # Unfastened seatbelt
        
        # Anomaly risk
        if anomaly > 0.7:
            risk_score += 40  # High anomaly
        elif anomaly > 0.5:
            risk_score += 25  # Suspicious anomaly
        elif anomaly > 0.3:
            risk_score += 10  # Mild anomaly
        
        # Site modifier for underground mining
        if site_type == "Underground Hard-Rock Mining" and anomaly > 0.45:
            risk_score += 10
        
        # Cap at 100
        risk_score = min(risk_score, 100)
        
        # Determine category
        if risk_score >= 80:
            category = "Critical"
        elif risk_score >= 60:
            category = "High"
        elif risk_score >= 30:
            category = "Moderate"
        else:
            category = "Low"
        
        # Determine factors in priority order
        factors = []
        if proximity < 2.0:
            factors.append("Proximity Danger (< 2m)")
        elif proximity < 7.0:
            factors.append("Proximity Warning (2-7m)")
        if seatbelt == 0.0:
            factors.append("Unfastened Seatbelt")
        if anomaly > 0.5:
            factors.append("Engine Telemetry Anomaly")
        elif anomaly > 0.3:
            factors.append("Suspicious Machine State")
        
        # Add terrain factor if relevant
        terrain = task_row.get('Terrain', 'Flat')
        if terrain == 'Incline':
            factors.append("Incline Terrain")
        
        # Add weather factor if relevant
        weather = task_row.get('Weather', 'Sunny')
        if weather in ['Rainy', 'Windy']:
            factors.append(f"{weather} Conditions")
        
        if not factors:
            factors = ["General Risk Factors"]
        
        return {
            'risk_score': risk_score,
            'risk_category': category,
            'top_factors': factors[:2],
            'explanation_en': f"{category} risk detected.",
            'explanation_regional': f"{category} risk detected."
        }
        
    def _get_operator_tasks(self, operator_id: str) -> pd.DataFrame:
        """
        Get today's tasks for a specific operator.
        
        For demo purposes, we select 3-5 tasks deterministically.
        """
        # Filter by operator
        operator_tasks = self.df[self.df['Operator ID'] == operator_id].copy()
        
        if len(operator_tasks) == 0:
            # Fallback to first operator if specified operator not found
            operator_tasks = self.df[self.df['Operator ID'] == self.df['Operator ID'].iloc[0]].copy()
        
        # Deterministically select 3-5 tasks for today's briefing
        # Use first 3 tasks for consistency
        today_tasks = operator_tasks.head(3).copy()
        
        return today_tasks
        
    def _get_operator_historical_issues(self, operator_id: str) -> str:
        """
        Analyze operator's historical data to find most frequent issue.
        
        Returns a short sentence describing the top issue.
        """
        # Get operator's historical data
        operator_data = self.df[self.df['Operator ID'] == operator_id]
        
        if len(operator_data) == 0:
            return "No historical data available."
        
        # Count issues (only count significant occurrences)
        seatbelt_issues = (operator_data['Seatbelt Status'] == 'Unfastened').sum()
        proximity_issues = (operator_data['Proximity Distance (m)'] < 3.0).sum()
        anomaly_issues = (operator_data['anomaly_flag'] == 'Unusual').sum()
        
        # Find most frequent issue
        issue_counts = {
            'seatbelt': seatbelt_issues,
            'proximity': proximity_issues,
            'anomaly': anomaly_issues
        }
        
        top_issue = max(issue_counts, key=issue_counts.get)
        
        if issue_counts[top_issue] == 0:
            return "Good safety record - no recurring issues."
        
        # Generate short, action-oriented sentence
        if top_issue == 'seatbelt':
            return f"Fasten seatbelt before starting ({seatbelt_issues} reminders needed)."
        elif top_issue == 'proximity':
            return f"Maintain safe distance from obstacles ({proximity_issues} close calls)."
        else:  # anomaly
            return f"Monitor for unusual machine behavior ({anomaly_issues} events flagged)."
            
    def generate_briefing(self, operator_id: str = None) -> Dict:
        """
        Generate complete pre-shift briefing for an operator.
        
        Args:
            operator_id: Operator ID (uses DEMO_OPERATOR_ID if None for demo)
            
        Returns:
            Dictionary with three sections:
            - today_tasks: List of task predictions
            - biggest_risk: Highest risk task with details
            - one_thing_to_watch: Historical issue summary
        """
        # Use demo operator if none specified
        if operator_id is None:
            operator_id = DEMO_OPERATOR_ID
        
        # Get today's tasks
        today_tasks = self._get_operator_tasks(operator_id)
        
        # Generate task predictions
        task_predictions = []
        for idx, task in today_tasks.iterrows():
            cat_estimate = task['Estimated Time (min)']
            model_prediction = self._predict_task_time(task)
            diff = model_prediction - cat_estimate
            diff_str = f"+{diff:.0f} min" if diff > 0 else f"{diff:.0f} min"
            
            task_predictions.append({
                'task_id': task['Task ID'],
                'task_type': task['Task Type'],
                'machine_id': task['Machine ID'],
                'cat_estimate': cat_estimate,
                'model_prediction': round(model_prediction, 1),
                'difference': diff_str
            })
        
        # Find biggest risk task
        highest_risk_task = None
        highest_risk_score = -1
        
        for idx, task in today_tasks.iterrows():
            risk_result = self._evaluate_task_risk(task)
            if risk_result['risk_score'] > highest_risk_score:
                highest_risk_score = risk_result['risk_score']
                highest_risk_task = {
                    'task_id': task['Task ID'],
                    'task_type': task['Task Type'],
                    'risk_score': risk_result['risk_score'],
                    'risk_category': risk_result['risk_category'],
                    'top_factors': risk_result['top_factors']
                }
        
        # Format biggest risk description
        if highest_risk_task:
            factors_str = " + ".join(highest_risk_task['top_factors'][:2])
            biggest_risk_desc = (
                f"Task {highest_risk_task['task_id']}: {highest_risk_task['risk_category']} risk "
                f"mainly due to {factors_str}"
            )
        else:
            biggest_risk_desc = "No significant risks identified for today's tasks."
        
        # Get one thing to watch
        one_thing_to_watch = self._get_operator_historical_issues(operator_id)
        
        return {
            'operator_id': operator_id,
            'today_tasks': task_predictions,
            'biggest_risk': biggest_risk_desc,
            'one_thing_to_watch': one_thing_to_watch
        }


# ---------------------------------------------------------------------------
# Streamlit UI Component
# ---------------------------------------------------------------------------
def render_briefing_card(briefing_data: Dict):
    """
    Render the pre-shift briefing card in Streamlit.
    
    Designed for glove-wearing operators with large text and high contrast.
    """
    import streamlit as st
    
    # Card container with high contrast
    st.markdown("""
    <style>
    .briefing-card {
        background-color: #1e1e1e;
        border: 2px solid #4CAF50;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .section-title {
        color: #4CAF50;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .task-item {
        color: #ffffff;
        font-size: 18px;
        margin: 8px 0;
        padding: 8px;
        background-color: #2d2d2d;
        border-radius: 5px;
    }
    .risk-highlight {
        color: #ff6b6b;
        font-size: 20px;
        font-weight: bold;
    }
    .watch-item {
        color: #ffd93d;
        font-size: 20px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="briefing-card">', unsafe_allow_html=True)
    
    # Section 1: Today's Tasks
    st.markdown('<div class="section-title">📋 Today\'s Tasks</div>', unsafe_allow_html=True)
    for task in briefing_data['today_tasks']:
        task_text = (
            f"{task['task_type']} on {task['machine_id']} | "
            f"CAT: {task['cat_estimate']}min | "
            f"AI: {task['model_prediction']}min ({task['difference']})"
        )
        st.markdown(f'<div class="task-item">{task_text}</div>', unsafe_allow_html=True)
    
    # Section 2: Biggest Risk
    st.markdown('<div class="section-title">⚠️ Today\'s Biggest Risk</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="risk-highlight">{briefing_data["biggest_risk"]}</div>', unsafe_allow_html=True)
    
    # Section 3: One Thing to Watch
    st.markdown('<div class="section-title">👀 One Thing to Watch</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="watch-item">{briefing_data["one_thing_to_watch"]}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Test Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("  PRE-SHIFT BRIEFING TEST")
    print("=" * 70)
    
    # Initialize briefing generator
    briefing_gen = PreShiftBriefing()
    
    # Generate briefing for demo operator
    briefing = briefing_gen.generate_briefing(operator_id=DEMO_OPERATOR_ID)
    
    print(f"\nOperator ID: {briefing['operator_id']}")
    print("\n" + "=" * 70)
    print("TODAY'S TASKS")
    print("=" * 70)
    for task in briefing['today_tasks']:
        print(f"{task['task_type']} on {task['machine_id']}")
        print(f"  CAT Estimate: {task['cat_estimate']} min")
        print(f"  AI Prediction: {task['model_prediction']} min ({task['difference']})")
        print()
    
    print("=" * 70)
    print("BIGGEST RISK")
    print("=" * 70)
    print(briefing['biggest_risk'])
    print()
    
    print("=" * 70)
    print("ONE THING TO WATCH")
    print("=" * 70)
    print(briefing['one_thing_to_watch'])
    print()
    
    print("=" * 70)
    print("  BRIEFING TEST COMPLETE")
    print("=" * 70)