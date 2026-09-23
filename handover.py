"""
=============================================================================
Shift Handover Checklist Module
Smart Operator Assistant (Caterpillar Machinery Hackathon)
=============================================================================

Purpose:
  Generate a shift handover checklist for operators with:
  1. Auto-filled shift events (incident log, anomaly flags, demo sequence)
  2. Outgoing operator quick checks (Yes/No buttons)
  3. Incoming operator sign-off (acknowledgement button)

Design Principles:
  - Glove-friendly: full-width tap targets, no typing
  - Deterministic: no LLM/API calls, uses session state
  - Quick: maximum 5-7 checklist items
  - Connected: ties to Safety Monitor tab's demo sequence
=============================================================================
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------
DATA_PATH = "synthetic_operator_data_with_anomalies.csv"
DEMO_SEED = 42  # For deterministic demo sequence

# Hazard preset choices
HAZARD_PRESETS = ["Loose ground", "Water", "Overhead line", "Other"]

# Language templates (reusing Layer 3 structure)
CHECKLIST_TEMPLATES = {
    "en": {
        "shift_events": "Shift Events",
        "outgoing_checks": "Outgoing Operator Checks",
        "incoming_signoff": "Incoming Operator Sign-off",
        "damage_check": "Any new damage or unusual noise?",
        "fuel_check": "Fuel level OK?",
        "hazard_check": "Any hazard on site the next operator should know about?",
        "hazard_specify": "Specify hazard type:",
        "acknowledge": "I've read this",
        "confirmed": "Checklist confirmed",
        "no_critical_events": "No other critical risk events",
        "extended_idling": "Extended idling flagged",
        "proximity_alert": "Proximity alerts triggered",
        "seatbelt_reminder": "Seatbelt reminders issued",
        "high_risk_event": "High/Critical risk events detected",
        "anomaly_flagged": "Anomaly events flagged"
    },
    "hi": {
        "shift_events": "शिफ्ट घटनाएं",
        "outgoing_checks": "जाने वाले ऑपरेटर की जांच",
        "incoming_signoff": "आने वाले ऑपरेटर की हस्ताक्षर",
        "damage_check": "कोई नया नुकसान या असामान्य शोर?",
        "fuel_check": "ईंधन स्तर ठीक है?",
        "hazard_check": "क्या साइट पर कोई खतरा है जो अगले ऑपरेटर को पता होना चाहिए?",
        "hazard_specify": "खतरे का प्रकार बताएं:",
        "acknowledge": "मैंने इसे पढ़ लिया है",
        "confirmed": "चेकलिस्ट की पुष्टि की गई",
        "no_critical_events": "कोई अन्य महत्वपूर्ण जोखिम घटनाएं नहीं",
        "extended_idling": "विस्तारित आइडलिंग की गई",
        "proximity_alert": "निकटता अलर्ट ट्रिगर किए गए",
        "seatbelt_reminder": "सीटबेल्ट रिमाइंडर जारी किए गए",
        "high_risk_event": "उच्च/महत्वपूर्ण जोखिम घटनाएं का पता चला",
        "anomaly_flagged": "विसंगति घटनाओं को चिह्नित किया गया"
    }
}


class ShiftHandoverChecklist:
    """
    Generate and manage shift handover checklists.
    """
    
    def __init__(self, data_path: str = DATA_PATH):
        """
        Initialize the handover checklist generator.
        """
        self.data_path = data_path
        self.df = pd.read_csv(data_path)
        
        # Set seed for deterministic demo
        np.random.seed(DEMO_SEED)
        
    def _get_shift_events(self, machine_id: str, operator_id: str) -> List[Dict]:
        """
        Get shift events for a machine from incident log, anomaly flags, and demo sequence.
        
        Returns list of events with counts, flagged items first (amber/red), then normal (green).
        """
        # Initialize session state for demo sequence if not exists
        try:
            if 'demo_sequence_events' not in st.session_state:
                self._initialize_demo_sequence()
        except:
            # If streamlit not available, initialize directly
            if not hasattr(self, '_demo_events_initialized'):
                self._initialize_demo_sequence_direct()
                self._demo_events_initialized = True
        
        # Get machine's data from CSV
        machine_data = self.df[self.df['Machine ID'] == machine_id]
        
        # Get operator's data for this shift
        operator_data = machine_data[machine_data['Operator ID'] == operator_id]
        
        events = []
        
        # 1. Extended idling events (idling > 30 min)
        extended_idling = operator_data[operator_data['Idling Time (min)'] > 30]
        if len(extended_idling) > 0:
            events.append({
                'type': 'extended_idling',
                'count': len(extended_idling),
                'machine_id': machine_id,
                'severity': 'amber'  # Flagged item
            })
        
        # 2. Proximity alerts (proximity < 3m)
        proximity_alerts = operator_data[operator_data['Proximity Distance (m)'] < 3.0]
        if len(proximity_alerts) > 0:
            events.append({
                'type': 'proximity_alert',
                'count': len(proximity_alerts),
                'machine_id': machine_id,
                'severity': 'red'  # Flagged item
            })
        
        # 3. Seatbelt reminders (unfastened with safety alert)
        seatbelt_reminders = operator_data[
            (operator_data['Seatbelt Status'] == 'Unfastened') & 
            (operator_data['Safety Alert Triggered'] == 'Yes')
        ]
        if len(seatbelt_reminders) > 0:
            events.append({
                'type': 'seatbelt_reminder',
                'count': len(seatbelt_reminders),
                'machine_id': machine_id,
                'severity': 'amber'  # Flagged item
            })
        
        # 4. Anomaly flags (Unusual)
        anomaly_events = operator_data[operator_data['anomaly_flag'] == 'Unusual']
        if len(anomaly_events) > 0:
            events.append({
                'type': 'anomaly_flagged',
                'count': len(anomaly_events),
                'machine_id': machine_id,
                'severity': 'red'  # Flagged item
            })
        
        # 5. Demo sequence events from session state or direct storage
        try:
            demo_events = st.session_state.get('demo_sequence_events', [])
        except:
            demo_events = getattr(self, '_demo_events', [])
        
        for demo_event in demo_events:
            if demo_event.get('machine_id') == machine_id:
                # Check if this is a high/critical risk event
                if demo_event.get('risk_category') in ['High', 'Critical']:
                    events.append({
                        'type': 'high_risk_event',
                        'count': 1,
                        'machine_id': machine_id,
                        'severity': 'red',
                        'demo_event': True
                    })
        
        # 6. Add normal event if no critical events
        if not events:
            events.append({
                'type': 'no_critical_events',
                'count': 0,
                'machine_id': machine_id,
                'severity': 'green'  # Normal item
            })
        
        # Sort: flagged items (amber/red) first, then normal (green)
        severity_order = {'red': 0, 'amber': 1, 'green': 2}
        events.sort(key=lambda x: severity_order[x['severity']])
        
        return events
        
    def _initialize_demo_sequence(self):
        """
        Initialize demo sequence events in session state for deterministic connection.
        
        This simulates the Safety Monitor tab's DEMO_SEQUENCE events.
        """
        # Create deterministic demo events
        demo_events = [
            {
                'type': 'extended_idling',
                'machine_id': 'EXC103',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'risk_category': 'Moderate'
            },
            {
                'type': 'proximity_alert',
                'machine_id': 'EXC103',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'risk_category': 'High'
            },
            {
                'type': 'seatbelt_reminder',
                'machine_id': 'EXC103',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'risk_category': 'Moderate'
            }
        ]
        
        st.session_state['demo_sequence_events'] = demo_events
        
    def _initialize_demo_sequence_direct(self):
        """
        Initialize demo sequence events directly without Streamlit session state.
        Used for testing and when Streamlit is not available.
        """
        # Create deterministic demo events
        demo_events = [
            {
                'type': 'extended_idling',
                'machine_id': 'EXC103',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'risk_category': 'Moderate'
            },
            {
                'type': 'proximity_alert',
                'machine_id': 'EXC103',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'risk_category': 'High'
            },
            {
                'type': 'seatbelt_reminder',
                'machine_id': 'EXC103',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'risk_category': 'Moderate'
            }
        ]
        
        self._demo_events = demo_events
        
    def _format_event_text(self, event: Dict, lang: str = 'en') -> str:
        """
        Format event text for display.
        """
        templates = CHECKLIST_TEMPLATES.get(lang, CHECKLIST_TEMPLATES['en'])
        
        event_type = event['type']
        count = event['count']
        machine_id = event['machine_id']
        
        if event_type == 'extended_idling':
            return f"{templates['extended_idling']} {count}x ({machine_id})"
        elif event_type == 'proximity_alert':
            return f"{templates['proximity_alert']} {count}x ({machine_id})"
        elif event_type == 'seatbelt_reminder':
            return f"{templates['seatbelt_reminder']} {count}x ({machine_id})"
        elif event_type == 'high_risk_event':
            return f"{templates['high_risk_event']} ({machine_id})"
        elif event_type == 'anomaly_flagged':
            return f"{templates['anomaly_flagged']} {count}x ({machine_id})"
        else:  # no_critical_events
            return templates['no_critical_events']
        
    def _get_event_color(self, severity: str) -> str:
        """
        Get color for event based on severity.
        """
        if severity == 'red':
            return '#ff6b6b'  # Red for critical
        elif severity == 'amber':
            return '#ffd93d'  # Amber for warnings
        else:
            return '#4CAF50'  # Green for normal
        
    def generate_checklist(self, machine_id: str, operator_id: str, 
                         incoming_operator_id: str, lang: str = 'en') -> Dict:
        """
        Generate complete shift handover checklist.
        
        Args:
            machine_id: Machine ID for the shift
            operator_id: Outgoing operator ID
            incoming_operator_id: Incoming operator ID
            lang: Language code (en, hi)
            
        Returns:
            Dictionary with shift events, checklist data
        """
        # Get shift events
        shift_events = self._get_shift_events(machine_id, operator_id)
        
        # Format events for display
        formatted_events = []
        for event in shift_events:
            formatted_events.append({
                'text': self._format_event_text(event, lang),
                'color': self._get_event_color(event['severity']),
                'severity': event['severity']
            })
        
        return {
            'machine_id': machine_id,
            'outgoing_operator_id': operator_id,
            'incoming_operator_id': incoming_operator_id,
            'shift_events': formatted_events,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# ---------------------------------------------------------------------------
# Streamlit UI Component
# ---------------------------------------------------------------------------
def render_handover_checklist(checklist_data: Dict, lang: str = 'en'):
    """
    Render the shift handover checklist in Streamlit.
    
    Designed for glove-wearing operators with full-width tap targets.
    """
    import streamlit as st
    templates = CHECKLIST_TEMPLATES.get(lang, CHECKLIST_TEMPLATES['en'])
    
    # Initialize session state for checklist responses
    if 'handover_responses' not in st.session_state:
        st.session_state['handover_responses'] = {}
    if 'handover_confirmed' not in st.session_state:
        st.session_state['handover_confirmed'] = False
    if 'handover_timestamp' not in st.session_state:
        st.session_state['handover_timestamp'] = None
    
    # Custom CSS for glove-friendly design
    st.markdown("""
    <style>
    .handover-container {
        background-color: #1e1e1e;
        border: 2px solid #2196F3;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .section-title {
        color: #2196F3;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 15px;
    }
    .event-item {
        color: #ffffff;
        font-size: 18px;
        margin: 8px 0;
        padding: 12px;
        border-radius: 5px;
        font-weight: bold;
    }
    .check-button {
        height: 60px;
        font-size: 20px;
        font-weight: bold;
        margin: 10px 0;
    }
    .confirmed-badge {
        background-color: #4CAF50;
        color: white;
        padding: 15px;
        border-radius: 5px;
        font-size: 20px;
        font-weight: bold;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="handover-container">', unsafe_allow_html=True)
    
    # Part 1: Auto-filled shift events (read-only)
    st.markdown(f'<div class="section-title">📋 {templates["shift_events"]}</div>', unsafe_allow_html=True)
    
    for event in checklist_data['shift_events']:
        st.markdown(
            f'<div class="event-item" style="background-color: {event["color"]}20; border-left: 4px solid {event["color"]};">{event["text"]}</div>',
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # Part 2: Outgoing operator quick checks (only if not confirmed)
    if not st.session_state['handover_confirmed']:
        st.markdown(f'<div class="section-title">🔧 {templates["outgoing_checks"]}</div>', unsafe_allow_html=True)
        
        # Damage check
        col1, col2 = st.columns(2)
        with col1:
            damage_yes = st.button(
                f"✅ Yes", 
                key="damage_yes",
                use_container_width=True,
                type="primary"
            )
        with col2:
            damage_no = st.button(
                f"❌ No", 
                key="damage_no",
                use_container_width=True
            )
        
        if damage_yes:
            st.session_state['handover_responses']['damage'] = True
        elif damage_no:
            st.session_state['handover_responses']['damage'] = False
        
        # Fuel check
        col3, col4 = st.columns(2)
        with col3:
            fuel_yes = st.button(
                f"✅ Yes", 
                key="fuel_yes",
                use_container_width=True,
                type="primary"
            )
        with col4:
            fuel_no = st.button(
                f"❌ No", 
                key="fuel_no",
                use_container_width=True
            )
        
        if fuel_yes:
            st.session_state['handover_responses']['fuel'] = True
        elif fuel_no:
            st.session_state['handover_responses']['fuel'] = False
        
        # Hazard check
        col5, col6 = st.columns(2)
        with col5:
            hazard_yes = st.button(
                f"✅ Yes", 
                key="hazard_yes",
                use_container_width=True,
                type="primary"
            )
        with col6:
            hazard_no = st.button(
                f"❌ No", 
                key="hazard_no",
                use_container_width=True
            )
        
        if hazard_yes:
            st.session_state['handover_responses']['hazard'] = True
            # Show hazard preset choices
            st.markdown(f"**{templates['hazard_specify']}**")
            hazard_cols = st.columns(len(HAZARD_PRESETS))
            for i, preset in enumerate(HAZARD_PRESETS):
                with hazard_cols[i]:
                    if st.button(preset, key=f"hazard_{i}", use_container_width=True):
                        st.session_state['handover_responses']['hazard_type'] = preset
        elif hazard_no:
            st.session_state['handover_responses']['hazard'] = False
        
        st.markdown("---")
        
        # Part 3: Incoming operator sign-off
        st.markdown(f'<div class="section-title">✍️ {templates["incoming_signoff"]}</div>', unsafe_allow_html=True)
        
        acknowledge = st.button(
            f"📝 {templates['acknowledge']}",
            key="acknowledge",
            use_container_width=True,
            type="primary"
        )
        
        if acknowledge:
            st.session_state['handover_confirmed'] = True
            st.session_state['handover_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            st.session_state['handover_responses']['incoming_operator'] = checklist_data['incoming_operator_id']
            st.rerun()
    
    else:
        # Show confirmed state
        st.markdown(f'<div class="confirmed-badge">✅ {templates["confirmed"]}</div>', unsafe_allow_html=True)
        st.markdown(f"**Timestamp:** {st.session_state['handover_timestamp']}")
        st.markdown(f"**Incoming Operator:** {st.session_state['handover_responses'].get('incoming_operator', 'N/A')}")
        
        # Show responses
        st.markdown("**Checklist Responses:**")
        if st.session_state['handover_responses'].get('damage') is not None:
            damage_status = "✅ Yes" if st.session_state['handover_responses']['damage'] else "❌ No"
            st.markdown(f"- {templates['damage_check']}: {damage_status}")
        
        if st.session_state['handover_responses'].get('fuel') is not None:
            fuel_status = "✅ Yes" if st.session_state['handover_responses']['fuel'] else "❌ No"
            st.markdown(f"- {templates['fuel_check']}: {fuel_status}")
        
        if st.session_state['handover_responses'].get('hazard') is not None:
            hazard_status = "✅ Yes" if st.session_state['handover_responses']['hazard'] else "❌ No"
            st.markdown(f"- {templates['hazard_check']}: {hazard_status}")
            if st.session_state['handover_responses'].get('hazard_type'):
                st.markdown(f"  - Hazard type: {st.session_state['handover_responses']['hazard_type']}")
    
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Test Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("  SHIFT HANDOVER CHECKLIST TEST")
    print("=" * 70)
    
    # Simple test without Streamlit dependency
    class SimpleSessionState:
        def __init__(self):
            self.state = {}
        
        def get(self, key, default=None):
            return self.state.get(key, default)
        
        def __setitem__(self, key, value):
            self.state[key] = value
    
    # Create a simple mock for testing
    class MockSt:
        session_state = SimpleSessionState()
    
    # Temporarily replace st with mock
    import sys
    original_st = sys.modules.get('streamlit')
    sys.modules['streamlit'] = MockSt()
    
    try:
        # Initialize checklist generator
        checklist_gen = ShiftHandoverChecklist()
        
        # Generate checklist for demo
        checklist_data = checklist_gen.generate_checklist(
            machine_id='EXC103',
            operator_id='OP1007',
            incoming_operator_id='OP1008',
            lang='en'
        )
        
        print(f"\nMachine ID: {checklist_data['machine_id']}")
        print(f"Outgoing Operator: {checklist_data['outgoing_operator_id']}")
        print(f"Incoming Operator: {checklist_data['incoming_operator_id']}")
        print(f"Timestamp: {checklist_data['timestamp']}")
        
        print("\n" + "=" * 70)
        print("SHIFT EVENTS (Auto-filled)")
        print("=" * 70)
        for event in checklist_data['shift_events']:
            color_indicator = "🔴" if event['severity'] == 'red' else "🟡" if event['severity'] == 'amber' else "🟢"
            print(f"{color_indicator} {event['text']}")
        
        print("\n" + "=" * 70)
        print("OUTGOING OPERATOR CHECKS (Interactive)")
        print("=" * 70)
        print("1. Any new damage or unusual noise? [Yes/No]")
        print("2. Fuel level OK? [Yes/No]")
        print("3. Any hazard on site the next operator should know about? [Yes/No]")
        print("   If Yes: [Loose ground/Water/Overhead line/Other]")
        
        print("\n" + "=" * 70)
        print("INCOMING OPERATOR SIGN-OFF")
        print("=" * 70)
        print("[I've read this] button → Records acknowledgement with timestamp")
        
        print("\n" + "=" * 70)
        print("  CHECKLIST TEST COMPLETE")
        print("=" * 70)
        
    finally:
        # Restore original streamlit if it existed
        if original_st:
            sys.modules['streamlit'] = original_st
        else:
            del sys.modules['streamlit']