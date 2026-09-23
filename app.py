"""
=============================================================================
Streamlit App - Smart Operator Assistant
Caterpillar Machinery Hackathon
=============================================================================

Purpose:
  Main Streamlit application for the Smart Operator Assistant.
  Includes Pre-Shift Briefing and Shift Handover Checklist features.
=============================================================================
"""

import streamlit as st
import pandas as pd
from briefing import PreShiftBriefing, render_briefing_card
from handover import ShiftHandoverChecklist, render_handover_checklist

# Page configuration
st.set_page_config(
    page_title="Smart Operator Assistant",
    page_icon="🚜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 36px;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 20px;
    }
    .section-header {
        font-size: 24px;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 30px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<div class="main-header">🚜 Smart Operator Assistant</div>', unsafe_allow_html=True)

# Sidebar for operator selection
st.sidebar.header("Operator Selection")

# Get unique operators from data
try:
    df = pd.read_csv("synthetic_operator_data_with_anomalies.csv")
    unique_operators = sorted(df['Operator ID'].unique())
except Exception as e:
    st.error(f"Error loading data: {e}")
    unique_operators = ["OP1007"]  # Fallback

# Operator selection
selected_operator = st.sidebar.selectbox(
    "Select Operator",
    options=unique_operators,
    index=0  # Default to first operator
)

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["Daily Tasks", "Safety Monitor", "Shift Handover", "Settings"])

with tab1:
    st.markdown('<div class="section-header">Daily Tasks</div>', unsafe_allow_html=True)
    
    # Generate and display pre-shift briefing
    try:
        briefing_gen = PreShiftBriefing()
        briefing_data = briefing_gen.generate_briefing(operator_id=selected_operator)
        
        # Render the briefing card
        render_briefing_card(briefing_data)
        
    except Exception as e:
        st.error(f"Error generating briefing: {e}")
        st.info("Please ensure all required model files are present.")

with tab2:
    st.markdown('<div class="section-header">Safety Monitor</div>', unsafe_allow_html=True)
    st.info("Safety Monitor features coming soon...")

with tab3:
    st.markdown('<div class="section-header">Shift Handover Checklist</div>', unsafe_allow_html=True)
    
    # Machine selection for handover
    try:
        df = pd.read_csv("synthetic_operator_data_with_anomalies.csv")
        unique_machines = sorted(df['Machine ID'].unique())
        
        # Machine selection in handover tab
        selected_machine = st.selectbox(
            "Select Machine",
            options=unique_machines,
            index=0
        )
        
        # Incoming operator selection
        unique_operators = sorted(df['Operator ID'].unique())
        incoming_operator = st.selectbox(
            "Incoming Operator",
            options=unique_operators,
            index=1 if len(unique_operators) > 1 else 0
        )
        
        # Generate and display handover checklist
        try:
            handover_gen = ShiftHandoverChecklist()
            checklist_data = handover_gen.generate_checklist(
                machine_id=selected_machine,
                operator_id=selected_operator,
                incoming_operator_id=incoming_operator,
                lang='en'
            )
            
            # Render the handover checklist
            render_handover_checklist(checklist_data, lang='en')
            
        except Exception as e:
            st.error(f"Error generating checklist: {e}")
            st.info("Please ensure all required data files are present.")
            
    except Exception as e:
        st.error(f"Error loading data: {e}")

with tab4:
    st.markdown('<div class="section-header">Settings</div>', unsafe_allow_html=True)
    st.info("Settings features coming soon...")

# Footer
st.markdown("---")
st.markdown("*Smart Operator Assistant - Caterpillar Hackathon*")