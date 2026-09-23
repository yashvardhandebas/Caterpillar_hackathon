# PROMPT: Implementation of Layer 3 (Mamdani Fuzzy Risk Engine & Multilingual In-Cab Assistant) & Complete Architecture Guide

You are the Principal Safety Systems and Applied AI Engineer building the complete **Layer 3** for the **Smart Operator Assistant** (Caterpillar Hackathon).

---

### Project Context & System Architecture So Far:
- **Layer 1 (Synthetic Telemetry Pipeline):** Simulates 500–1,000 operation records extending CAT's standard schema (fuel, engine hours, idling, load cycles, seatbelt) with environmental attributes (`Site Type` [Construction, Mining, Underground Hard-Rock Mining], `Proximity Distance`, `Terrain`, `Shift`, `Ambient Temperature`).
- **Layer 2 (Core Intelligence):** An **Isolation Forest** trained on fuel burn, load cycles, idling, and engine hours to output a normalized anomaly score ($0.0\text{--}1.0$), plus an **XGBoost regressor** predicting corrected task durations.
- **Goal for Layer 3:** Replace brittle if-else heuristics with a **Mamdani Fuzzy Inference System (Mamdani FIS)** to compute a continuous, defensible **Operational Risk Score (0–100)**, classify it into 4 actionable risk bands, extract the primary risk drivers, and translate explanations into vernacular Indian languages (Hindi, Tamil, Kannada) using **Sarvam AI** with an offline-first fallback.

---

### Deliverable 1: `layer3_risk_engine.py`

Write a modular, production-ready Python script implementing the full Layer 3 pipeline with the following specifications:

#### 1. Fuzzy Logic Architecture (`scikit-fuzzy`)
Define continuous universes of discourse and membership functions:
- **`proximity_distance` ($0.0$ to $15.0$ meters):**
  - `Critical_Close`: Trapezoidal $[0.0, 0.0, 1.5, 3.0]$
  - `Warning`: Triangular $[2.0, 4.5, 7.0]$
  - `Safe`: Trapezoidal $[5.5, 8.0, 15.0, 15.0]$
- **`ml_anomaly_score` ($0.0$ to $1.0$, from Layer 2 Isolation Forest):**
  - `Normal`: Trapezoidal $[0.0, 0.0, 0.3, 0.5]$
  - `Suspicious`: Triangular $[0.35, 0.6, 0.8]$
  - `High_Anomaly`: Trapezoidal $[0.65, 0.85, 1.0, 1.0]$
- **`seatbelt` ($0.0$ to $1.0$, where $0$ = unbuckled, $1$ = buckled):**
  - `Unbuckled`: Trapezoidal $[0.0, 0.0, 0.2, 0.5]$
  - `Buckled`: Trapezoidal $[0.5, 0.8, 1.0, 1.0]$
- **`risk_score` (Consequent Output: $0.0$ to $100.0$):**
  - Defuzzification method: Centroid (`centroid`).
  - `Low`: Trapezoidal $[0, 0, 20, 35]$
  - `Moderate`: Triangular $[25, 45, 60]$
  - `High`: Triangular $[50, 70, 85]$
  - `Critical`: Trapezoidal $[75, 85, 100, 100]$

#### 2. Industrial Safety Rules & Site Modifier
Implement 8 control rules:
1. `Critical_Close` AND `Unbuckled` $\rightarrow$ `Critical`
2. `Critical_Close` $\rightarrow$ `High`
3. `High_Anomaly` AND `Unbuckled` $\rightarrow$ `High`
4. `High_Anomaly` AND `Warning` $\rightarrow$ `High`
5. `Suspicious` AND `Warning` $\rightarrow$ `Moderate`
6. `Safe` AND `Buckled` AND `Normal` $\rightarrow$ `Low`
7. `Warning` AND `Buckled` $\rightarrow$ `Moderate`
8. **Site Sensitivity Modifier:** If `site_type == "Underground Hard-Rock Mining"` and `ml_anomaly_score > 0.45` (suspicious idling/load indicating underground ventilation or machine stress), add a $+10.0$ offset to the defuzzified score (capped at $100.0$).

#### 3. Risk Discretization & Factor Attribution
- Discretize the crisp score into four bands:
  - `Low`: $0 \le \text{score} \le 29$
  - `Moderate`: $30 \le \text{score} \le 59$
  - `High`: $60 \le \text{score} \le 79$
  - `Critical`: $80 \le \text{score} \le 100$
- Calculate the highest input membership values to identify the **top 1–2 contributing factors** (e.g., `"Unfastened Seatbelt"`, `"Proximity Danger (< 2m)"`, `"Engine Telemetry Anomaly"`).

#### 4. Multilingual Explainability (Sarvam AI + Offline Fallback)
- Implement `generate_explanation(risk_category, score, top_factors, target_lang="hi")`:
  - **Primary Path (Sarvam AI API):** Call Sarvam AI's chat completion endpoint (`https://api.sarvam.ai/v1`) using `openai.OpenAI` or `requests` (`model="sarvam-m"` or `"sarvam-105b"`). Provide a strict system prompt: *"Generate a single, direct in-cab safety warning for a machine operator under 18 words. No markdown, no calculations, no filler."*
  - **Deterministic Local Fallback:** If the API key is missing, network calls fail, or latency exceeds $1.5\text{ s}$, instantly return pre-translated templates across English, Hindi, Tamil, and Kannada without breaking or blocking the interface.

#### 5. Interface & Standalone Verification
- Encapsulate within `class SafetyRiskEngine` exposing `evaluate(telemetry_dict, target_lang="hi")`.
- Expected return schema:
  ```json
  {
    "risk_score": 83.4,
    "risk_category": "Critical",
    "top_factors": ["Unfastened Seatbelt", "Proximity Danger (< 2m)"],
    "explanation_en": "Critical risk: Seatbelt is unfastened and an obstacle is dangerously close.",
    "explanation_regional": "गंभीर खतरा: सीटबेल्ट नहीं बंधी है और बाधा मशीन के बेहद करीब है।"
  }

  * Include an `if __name__ == "__main__":` block evaluating 3 fixed scenarios:
    * **Scenario 1 (Normal Operations):** `proximity=10.0`, `seatbelt=1`, `ml_anomaly_score=0.1`, `site_type="Construction"` \(\rightarrow\) Expect `Low`.
    * **Scenario 2 (Underground Idling Anomaly):** `proximity=4.0`, `seatbelt=1`, `ml_anomaly_score=0.55`, `site_type="Underground Hard-Rock Mining"` \(\rightarrow\) Expect `Moderate / High`.
    * **Scenario 3 (Imminent Hazard):** `proximity=1.2`, `seatbelt=0`, `ml_anomaly_score=0.75`, `site_type="Mining"` \(\rightarrow\) Expect `Critical (80+)`.

**Deliverable 2: LAYER_3_EXPLAINABILITY_GUIDE.md**

Generate a comprehensive engineering document containing:

1. **Mathematical Defense of Mamdani FIS:** Detailed contrast between continuous fuzzy inference vs. brittle edge thresholds in industrial IoT environments.
2. **Fuzzy Membership & Rule Formulation:** Complete mathematical formulas for trapezoidal/triangular curves and the rule activation matrix.
3. **End-to-End Pipeline Summary (Layers 1 to 3):**
    * Layer 1 synthetic telemetry data generation.
    * Layer 2 dual ML models (Isolation Forest + XGBoost task time correction).
    * Layer 3 fuzzy risk defuzzification and Sarvam AI language grounding.
4. **Cab Ergonomics & Industrial Safety Disclaimers:** Explain why the score is framed as an operational decision-support tool rather than an ungrounded probability, and detail the offline fallback fail-safe design.
5. **Panel Defense Cheat Sheet:** Prepared technical responses to common Caterpillar judging questions regarding false alarm reduction, synthetic data limits, and sensor explainability.
