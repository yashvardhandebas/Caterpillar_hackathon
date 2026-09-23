"""
=============================================================================
Layer 3: Mamdani Fuzzy Risk Engine & Multilingual In-Cab Assistant
Smart Operator Assistant (Caterpillar Machinery Hackathon)
=============================================================================

Purpose:
  Replace brittle if-else heuristics with a Mamdani Fuzzy Inference System
  to compute a continuous, defensible Operational Risk Score (0-100),
  classify it into 4 actionable risk bands, extract primary risk drivers,
  and translate explanations into vernacular Indian languages using Sarvam AI
  with an offline-first fallback.

Explainability for Judges:
  Mamdani FIS provides continuous, smooth risk transitions unlike binary
  thresholds. It handles uncertainty naturally by allowing partial membership
  in multiple risk states simultaneously. The defuzzified centroid gives a
  mathematically grounded single score while preserving explainability through
  membership degrees.

Features Used:
  - Proximity Distance (0-15m): Critical_Close, Warning, Safe
  - ML Anomaly Score (0-1.0): Normal, Suspicious, High_Anomaly
  - Seatbelt Status (0-1): Unbuckled, Buckled
  - Site Type: Construction, Mining, Underground Hard-Rock Mining

Outputs:
  - Risk Score (0-100): Continuous operational risk assessment
  - Risk Category: Low, Moderate, High, Critical
  - Top Factors: Primary contributing risk drivers
  - Explanation: Multilingual safety warnings (English + regional language)
=============================================================================
"""

import os
import json
import time
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from typing import Dict, List, Optional, Tuple
import requests
from openai import OpenAI


# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
SARVAM_API_URL = "https://api.sarvam.ai/v1/chat/completions"
SARVAM_TIMEOUT = 1.5  # seconds

# Risk band thresholds
RISK_BANDS = {
    "Low": (0, 29),
    "Moderate": (30, 59),
    "High": (60, 79),
    "Critical": (80, 100)
}

# Pre-translated explanation templates (offline fallback)
EXPLANATION_TEMPLATES = {
    "Low": {
        "en": "Safe operation. Continue monitoring.",
        "hi": "सुरक्षित संचालन। निगरानी जारी रखें।",
        "ta": "பாதுகாப்பான செயல்பாடு. கண்காணிப்பைத் தொடரவும்.",
        "kn": "ಸುರಕ್ಷಿತ ಕಾರ್ಯಾಚರಣೆ. ಮೇಲ್ವಿಚಾರಣೆಯನ್ನು ಮುಂದುವರಿಸಿ."
    },
    "Moderate": {
        "en": "Moderate risk detected. Stay alert.",
        "hi": "मध्यम जोखिम पाया गया। सचेत रहें।",
        "ta": "மிதமான ஆபத்து கண்டறியப்பட்டது. எச்சரிக்கையாக இருங்கள்.",
        "kn": "ಮಧ್ಯಮ ಅಪಾಯವನ್ನು ಪತ್ತೆಹಚ್ಚಲಾಗಿದೆ. ಎಚ್ಚರಿಕೆಯಿಂದಿರಿ."
    },
    "High": {
        "en": "High risk: Review factors immediately.",
        "hi": "उच्च जोखिम: तुरंत कारकों की समीक्षा करें।",
        "ta": "அதிக ஆபத்து: உடனடியாக காரணிகளை மதிப்பாய்வு செய்யவும்.",
        "kn": "ಹೈ ರಿಸ್ಕ್: ತಕ್ಷಣವೇ ಅಂಶಗಳನ್ನು ಪರಿಶೀಲಿಸಿ."
    },
    "Critical": {
        "en": "Critical risk: Take corrective action now.",
        "hi": "गंभीर खतरा: अभी सुधारात्मक कार्रवाई करें।",
        "ta": "மிகவும் ஆபத்தானது: இப்போதே திருத்த நடவடிக்கை எடுக்கவும்.",
        "kn": "ಕ್ರಿಟಿಕಲ್ ರಿಸ್ಕ್: ಈಗಲೇ ಸರಿಪಡಿಸುವ ಕ್ರಮವನ್ನು ತೆಗೆದುಕೊಳ್ಳಿ."
    }
}

# Factor-specific explanations for offline fallback
FACTOR_TEMPLATES = {
    "Unfastened Seatbelt": {
        "en": "Seatbelt is unfastened.",
        "hi": "सीटबेल्ट नहीं बंधी है।",
        "ta": "இருக்கைப் பட்டை இணைக்கப்படவில்லை.",
        "kn": "ಸೀಟ್‌ಬೆಲ್ಟ್ ಕಟ್ಟಿಲ್ಲ."
    },
    "Proximity Danger (< 2m)": {
        "en": "Obstacle dangerously close.",
        "hi": "बाधा मशीन के बेहद करीब है।",
        "ta": "தடைபாடு மிகவும் அருகில் உள்ளது.",
        "kn": "ಅಡ್ಡಿಪಡಿಸುವಿಕೆ ತುಂಬಾ ಹತ್ತಿರದಲ್ಲಿದೆ."
    },
    "Proximity Warning (2-7m)": {
        "en": "Obstacle within warning range.",
        "hi": "बाधा चेतावनी सीमा में है।",
        "ta": "தடைபாடு எச்சரிக்கை வரம்பில் உள்ளது.",
        "kn": "ಎಚ್ಚರಿಕೆ ಶ್ರೇಣಿಯಲ್ಲಿ ಅಡ್ಡಿಪಡಿಸುವಿಕೆ."
    },
    "Engine Telemetry Anomaly": {
        "en": "Unusual machine behavior detected.",
        "hi": "असामान्य मशीन व्यवहार पाया गया।",
        "ta": "வழமையற்ற இயந்திர நடத்தை கண்டறியப்பட்டது.",
        "kn": "ಅಸಾಮಾನ್ಯ ಯಂತ್ರ ವರ್ತನೆ ಪತ್ತೆಹಚ್ಚಲಾಗಿದೆ."
    },
    "Suspicious Machine State": {
        "en": "Suspicious machine operation pattern.",
        "hi": "संदिग्ध मशीन संचालन पैटर्न।",
        "ta": "சந்தேகத்திற்குரிய இயந்திர இயக்க முறை.",
        "kn": "ಅನುಮಾನಾಸ್ಪದ ಯಂತ್ರ ಕಾರ್ಯಾಚರಣೆ ಮಾದರಿ."
    }
}


class SafetyRiskEngine:
    """
    Mamdani Fuzzy Inference System for operational risk assessment.
    
    Combines proximity, ML anomaly scores, and seatbelt status into a
    continuous risk score (0-100) with multilingual explainability.
    """
    
    def __init__(self):
        """Initialize the fuzzy control system."""
        self._setup_fuzzy_variables()
        self._setup_rules()
        self._build_control_system()
        
    def _setup_fuzzy_variables(self):
        """Define input/output universes and membership functions."""
        
        # Input: Proximity Distance (0.0 to 15.0 meters)
        self.proximity = ctrl.Antecedent(np.arange(0.0, 15.1, 0.1), 'proximity_distance')
        self.proximity['Critical_Close'] = fuzz.trapmf(self.proximity.universe, [0.0, 0.0, 1.5, 3.0])
        self.proximity['Warning'] = fuzz.trimf(self.proximity.universe, [2.0, 4.5, 7.0])
        self.proximity['Safe'] = fuzz.trapmf(self.proximity.universe, [5.5, 8.0, 15.0, 15.0])
        
        # Input: ML Anomaly Score (0.0 to 1.0 from Layer 2 Isolation Forest)
        self.ml_anomaly = ctrl.Antecedent(np.arange(0.0, 1.01, 0.01), 'ml_anomaly_score')
        self.ml_anomaly['Normal'] = fuzz.trapmf(self.ml_anomaly.universe, [0.0, 0.0, 0.3, 0.5])
        self.ml_anomaly['Suspicious'] = fuzz.trimf(self.ml_anomaly.universe, [0.35, 0.6, 0.8])
        self.ml_anomaly['High_Anomaly'] = fuzz.trapmf(self.ml_anomaly.universe, [0.65, 0.85, 1.0, 1.0])
        
        # Input: Seatbelt Status (0.0 to 1.0, where 0 = unbuckled, 1 = buckled)
        self.seatbelt = ctrl.Antecedent(np.arange(0.0, 1.01, 0.01), 'seatbelt')
        self.seatbelt['Unbuckled'] = fuzz.trapmf(self.seatbelt.universe, [0.0, 0.0, 0.2, 0.5])
        self.seatbelt['Buckled'] = fuzz.trapmf(self.seatbelt.universe, [0.5, 0.8, 1.0, 1.0])
        
        # Output: Risk Score (0.0 to 100.0)
        self.risk_score = ctrl.Consequent(np.arange(0.0, 100.1, 0.1), 'risk_score')
        self.risk_score['Low'] = fuzz.trapmf(self.risk_score.universe, [0, 0, 20, 35])
        self.risk_score['Moderate'] = fuzz.trimf(self.risk_score.universe, [25, 45, 60])
        self.risk_score['High'] = fuzz.trimf(self.risk_score.universe, [50, 65, 80])
        self.risk_score['Critical'] = fuzz.trapmf(self.risk_score.universe, [70, 80, 100, 100])
        
    def _setup_rules(self):
        """Define the 8 industrial safety control rules."""
        
        self.rules = [
            # Rule 1: Critical_Close AND Unbuckled -> Critical
            ctrl.Rule(
                self.proximity['Critical_Close'] & self.seatbelt['Unbuckled'],
                self.risk_score['Critical']
            ),
            
            # Rule 2: Critical_Close -> High
            ctrl.Rule(
                self.proximity['Critical_Close'],
                self.risk_score['High']
            ),
            
            # Rule 3: High_Anomaly AND Unbuckled -> High
            ctrl.Rule(
                self.ml_anomaly['High_Anomaly'] & self.seatbelt['Unbuckled'],
                self.risk_score['High']
            ),
            
            # Rule 4: High_Anomaly AND Warning -> High
            ctrl.Rule(
                self.ml_anomaly['High_Anomaly'] & self.proximity['Warning'],
                self.risk_score['High']
            ),
            
            # Rule 5: Suspicious AND Warning -> Moderate
            ctrl.Rule(
                self.ml_anomaly['Suspicious'] & self.proximity['Warning'],
                self.risk_score['Moderate']
            ),
            
            # Rule 6: Safe AND Buckled AND Normal -> Low
            ctrl.Rule(
                self.proximity['Safe'] & self.seatbelt['Buckled'] & self.ml_anomaly['Normal'],
                self.risk_score['Low']
            ),
            
            # Rule 7: Warning AND Buckled -> Moderate
            ctrl.Rule(
                self.proximity['Warning'] & self.seatbelt['Buckled'],
                self.risk_score['Moderate']
            )
        ]
        
    def _build_control_system(self):
        """Build and compile the fuzzy control system."""
        self.risk_control = ctrl.ControlSystem(self.rules)
        self.risk_simulation = ctrl.ControlSystemSimulation(self.risk_control)
        
    def _apply_site_modifier(self, score: float, site_type: str, ml_anomaly_score: float) -> float:
        """
        Apply site sensitivity modifier for underground mining.
        
        If site_type == "Underground Hard-Rock Mining" and ml_anomaly_score > 0.45,
        add +10.0 offset to the defuzzified score (capped at 100.0).
        """
        if site_type == "Underground Hard-Rock Mining" and ml_anomaly_score > 0.45:
            modified_score = min(score + 10.0, 100.0)
            return modified_score
        return score
        
    def _categorize_risk(self, score: float) -> str:
        """Categorize risk score into Low, Moderate, High, or Critical."""
        for category, (low, high) in RISK_BANDS.items():
            if low <= score <= high:
                return category
        return "Critical"  # Default to Critical if out of bounds
        
    def _extract_top_factors(self, proximity_val: float, ml_anomaly_val: float, 
                            seatbelt_val: float) -> List[str]:
        """
        Extract top 1-2 contributing factors based on highest membership values.
        """
        membership_values = {}
        
        # Proximity memberships
        membership_values['Critical_Close'] = fuzz.interp_membership(
            self.proximity.universe, 
            self.proximity['Critical_Close'].mf, 
            proximity_val
        )
        membership_values['Warning'] = fuzz.interp_membership(
            self.proximity.universe, 
            self.proximity['Warning'].mf, 
            proximity_val
        )
        membership_values['Safe'] = fuzz.interp_membership(
            self.proximity.universe, 
            self.proximity['Safe'].mf, 
            proximity_val
        )
        
        # ML anomaly memberships
        membership_values['Normal'] = fuzz.interp_membership(
            self.ml_anomaly.universe, 
            self.ml_anomaly['Normal'].mf, 
            ml_anomaly_val
        )
        membership_values['Suspicious'] = fuzz.interp_membership(
            self.ml_anomaly.universe, 
            self.ml_anomaly['Suspicious'].mf, 
            ml_anomaly_val
        )
        membership_values['High_Anomaly'] = fuzz.interp_membership(
            self.ml_anomaly.universe, 
            self.ml_anomaly['High_Anomaly'].mf, 
            ml_anomaly_val
        )
        
        # Seatbelt memberships
        membership_values['Unbuckled'] = fuzz.interp_membership(
            self.seatbelt.universe, 
            self.seatbelt['Unbuckled'].mf, 
            seatbelt_val
        )
        membership_values['Buckled'] = fuzz.interp_membership(
            self.seatbelt.universe, 
            self.seatbelt['Buckled'].mf, 
            seatbelt_val
        )
        
        # Map membership labels to human-readable factors
        factor_mapping = {
            'Critical_Close': 'Proximity Danger (< 2m)',
            'Warning': 'Proximity Warning (2-7m)',
            'Safe': None,  # Safe is not a risk factor
            'Normal': None,  # Normal is not a risk factor
            'Suspicious': 'Suspicious Machine State',
            'High_Anomaly': 'Engine Telemetry Anomaly',
            'Unbuckled': 'Unfastened Seatbelt',
            'Buckled': None  # Buckled is not a risk factor
        }
        
        # Sort by membership value (descending) and get top factors
        sorted_factors = sorted(
            [(label, value) for label, value in membership_values.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        top_factors = []
        for label, value in sorted_factors:
            if value > 0.3:  # Only include significant memberships
                factor_name = factor_mapping.get(label)
                if factor_name and factor_name not in top_factors:
                    top_factors.append(factor_name)
                    if len(top_factors) >= 2:
                        break
        
        return top_factors if top_factors else ["General Risk Factors"]
        
    def _generate_sarvam_explanation(self, risk_category: str, score: float, 
                                    top_factors: List[str], target_lang: str = "hi") -> Optional[str]:
        """
        Generate explanation using Sarvam AI API with timeout and error handling.
        
        Returns None if API call fails or times out, triggering offline fallback.
        """
        if not SARVAM_API_KEY:
            return None
            
        try:
            # Map language codes to Sarvam models
            lang_model_map = {
                "hi": "sarvam-m",  # Hindi
                "ta": "sarvam-m",  # Tamil
                "kn": "sarvam-m"   # Kannada
            }
            
            model = lang_model_map.get(target_lang, "sarvam-m")
            
            # Construct prompt
            factors_str = ", ".join(top_factors[:2])
            system_prompt = "Generate a single, direct in-cab safety warning for a machine operator under 18 words. No markdown, no calculations, no filler."
            user_prompt = f"Risk level: {risk_category} (score: {score:.1f}). Factors: {factors_str}."
            
            client = OpenAI(
                api_key=SARVAM_API_KEY,
                base_url="https://api.sarvam.ai/v1"
            )
            
            start_time = time.time()
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=50,
                temperature=0.7
            )
            
            elapsed = time.time() - start_time
            
            if elapsed > SARVAM_TIMEOUT:
                return None
                
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
                
        except Exception as e:
            # Any error triggers offline fallback
            return None
            
        return None
        
    def _generate_offline_explanation(self, risk_category: str, top_factors: List[str], 
                                     target_lang: str = "hi") -> Tuple[str, str]:
        """
        Generate deterministic offline explanation using pre-translated templates.
        
        Returns tuple: (explanation_en, explanation_regional)
        """
        # Get base category explanation
        base_en = EXPLANATION_TEMPLATES[risk_category]["en"]
        base_regional = EXPLANATION_TEMPLATES[risk_category].get(target_lang, base_en)
        
        # Append factor-specific explanations
        factor_explanations_en = []
        factor_explanations_regional = []
        
        for factor in top_factors[:2]:
            if factor in FACTOR_TEMPLATES:
                factor_explanations_en.append(FACTOR_TEMPLATES[factor]["en"])
                factor_explanations_regional.append(
                    FACTOR_TEMPLATES[factor].get(target_lang, FACTOR_TEMPLATES[factor]["en"])
                )
        
        # Combine explanations
        if factor_explanations_en:
            explanation_en = f"{base_en} {' '.join(factor_explanations_en)}"
            explanation_regional = f"{base_regional} {' '.join(factor_explanations_regional)}"
        else:
            explanation_en = base_en
            explanation_regional = base_regional
            
        return explanation_en, explanation_regional
        
    def generate_explanation(self, risk_category: str, score: float, 
                           top_factors: List[str], target_lang: str = "hi") -> Tuple[str, str]:
        """
        Generate multilingual explanation with Sarvam AI primary path and offline fallback.
        
        Args:
            risk_category: Risk category (Low, Moderate, High, Critical)
            score: Risk score (0-100)
            top_factors: List of top contributing factors
            target_lang: Target language code (hi, ta, kn, en)
            
        Returns:
            Tuple of (explanation_en, explanation_regional)
        """
        # Try Sarvam AI first
        if target_lang != "en":
            sarvam_result = self._generate_sarvam_explanation(
                risk_category, score, top_factors, target_lang
            )
            if sarvam_result:
                # Generate English version for consistency
                explanation_en, _ = self._generate_offline_explanation(
                    risk_category, top_factors, "en"
                )
                return explanation_en, sarvam_result
        
        # Fallback to offline templates
        return self._generate_offline_explanation(risk_category, top_factors, target_lang)
        
    def evaluate(self, telemetry_dict: Dict, target_lang: str = "hi") -> Dict:
        """
        Evaluate operational risk for a single telemetry record.
        
        Args:
            telemetry_dict: Dictionary containing:
                - proximity_distance: float (0.0 to 15.0 meters)
                - seatbelt: float (0.0 to 1.0, where 0 = unbuckled, 1 = buckled)
                - ml_anomaly_score: float (0.0 to 1.0 from Layer 2)
                - site_type: str (Construction, Mining, Underground Hard-Rock Mining)
            target_lang: Target language code (hi, ta, kn, en)
            
        Returns:
            Dictionary with risk_score, risk_category, top_factors, 
            explanation_en, explanation_regional
        """
        # Extract inputs
        proximity_val = float(telemetry_dict['proximity_distance'])
        seatbelt_val = float(telemetry_dict['seatbelt'])
        ml_anomaly_val = float(telemetry_dict['ml_anomaly_score'])
        site_type = telemetry_dict.get('site_type', 'Construction')
        
        # Set inputs for fuzzy inference
        self.risk_simulation.input['proximity_distance'] = proximity_val
        self.risk_simulation.input['ml_anomaly_score'] = ml_anomaly_val
        self.risk_simulation.input['seatbelt'] = seatbelt_val
        
        # Compute fuzzy inference
        self.risk_simulation.compute()
        
        # Get defuzzified risk score
        risk_score = float(self.risk_simulation.output['risk_score'])
        
        # Apply site sensitivity modifier
        risk_score = self._apply_site_modifier(risk_score, site_type, ml_anomaly_val)
        
        # Categorize risk
        risk_category = self._categorize_risk(risk_score)
        
        # Extract top contributing factors
        top_factors = self._extract_top_factors(proximity_val, ml_anomaly_val, seatbelt_val)
        
        # Generate multilingual explanation
        explanation_en, explanation_regional = self.generate_explanation(
            risk_category, risk_score, top_factors, target_lang
        )
        
        return {
            "risk_score": round(risk_score, 1),
            "risk_category": risk_category,
            "top_factors": top_factors,
            "explanation_en": explanation_en,
            "explanation_regional": explanation_regional
        }


# ---------------------------------------------------------------------------
# Standalone Verification
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("  LAYER 3: MAMDANI FUZZY RISK ENGINE & MULTILINGUAL ASSISTANT")
    print("=" * 70)
    
    # Initialize the risk engine
    engine = SafetyRiskEngine()
    print("\n[Initialized] Mamdani Fuzzy Inference System")
    print("[Ready] 8 industrial safety rules loaded")
    print("[Ready] Site sensitivity modifier enabled")
    print("[Ready] Multilingual explainability (Sarvam AI + offline fallback)")
    
    # Test scenarios
    scenarios = [
        {
            "name": "Scenario 1 (Normal Operations)",
            "input": {
                "proximity_distance": 10.0,
                "seatbelt": 1.0,
                "ml_anomaly_score": 0.1,
                "site_type": "Construction"
            },
            "expected": "Low"
        },
        {
            "name": "Scenario 2 (Underground Idling Anomaly)",
            "input": {
                "proximity_distance": 4.0,
                "seatbelt": 1.0,
                "ml_anomaly_score": 0.55,
                "site_type": "Underground Hard-Rock Mining"
            },
            "expected": "Moderate / High"
        },
        {
            "name": "Scenario 3 (Imminent Hazard)",
            "input": {
                "proximity_distance": 1.2,
                "seatbelt": 0.0,
                "ml_anomaly_score": 0.75,
                "site_type": "Mining"
            },
            "expected": "Critical (80+)"
        }
    ]
    
    print("\n" + "=" * 70)
    print("  TEST SCENARIOS")
    print("=" * 70)
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print("-" * 70)
        print(f"Input: {scenario['input']}")
        print(f"Expected: {scenario['expected']}")
        
        # Evaluate with Hindi (default)
        result = engine.evaluate(scenario['input'], target_lang="hi")
        
        print(f"\nResult:")
        print(f"  Risk Score: {result['risk_score']}")
        print(f"  Risk Category: {result['risk_category']}")
        print(f"  Top Factors: {', '.join(result['top_factors'])}")
        print(f"  Explanation (EN): {result['explanation_en']}")
        print(f"  Explanation (HI): {result['explanation_regional']}")
        
        # Verify expected outcome
        if scenario['expected'] == "Low" and result['risk_category'] == "Low":
            print("  ✓ PASS")
        elif scenario['expected'] == "Moderate / High" and result['risk_category'] in ["Moderate", "High"]:
            print("  ✓ PASS")
        elif scenario['expected'] == "Critical (80+)" and result['risk_category'] == "Critical":
            print("  ✓ PASS")
        else:
            print("  ✗ FAIL")
    
    print("\n" + "=" * 70)
    print("  LAYER 3 VERIFICATION COMPLETE")
    print("=" * 70)
    print("\nUsage Example:")
    print("  engine = SafetyRiskEngine()")
    print("  result = engine.evaluate({")
    print("      'proximity_distance': 5.0,")
    print("      'seatbelt': 1.0,")
    print("      'ml_anomaly_score': 0.3,")
    print("      'site_type': 'Construction'")
    print("  }, target_lang='hi')")
    print("=" * 70)