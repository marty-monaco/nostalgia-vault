import streamlit as st
import pandas as pd
from st_gsheets_connection import GSheetsConnection

# 1. Page Configuration & Branding
st.set_page_config(
    page_title="The Vault",
    page_icon="🔒",
    layout="wide"
)

# Custom Title for "The Vault"
st.title("The Vault")
st.markdown("### *Complex concepts, unlocked through metaphor.*")

# 2. Sidebar Navigation (Switcher for Demoing)
st.sidebar.title("Navigation")
access_mode = st.sidebar.radio(
    "Access Level:", 
    ["Student Learning Portal", "The Vault CMS (Admin)"]
)

# 3. Initialize Google Sheets Connection
# Ensure your secrets.toml or Streamlit Cloud Secrets has the correct GSheets info
conn = st.connection("gsheets", type=GSheetsConnection)

# --- STUDENT LEARNING PORTAL ---
if access_mode == "Student Learning Portal":
    st.header("🔓 Learning Portal")
    st.write("Experience universal metaphor-based learning.")

    with st.form("learning_map_form"):
        concept = st.text_input(
            "What complex concept are you looking to master?",
            placeholder="e.g., Quantum Entanglement, Blockchain, Photosynthesis..."
        )
        
        metaphor_type = st.selectbox(
            "Select a Metaphor Lens:",
            [
                "Common Household Objects", 
                "Architectural & Building", 
                "Sports & Team Dynamics", 
                "Nature & Biological Systems",
                "Culinary & Cooking",
                "Universal (Let the AI decide)"
            ]
        )
        
        submit_button = st.form_submit_button("Generate Learning Map")

    if submit_button and concept:
        with st.spinner(f"Orchestrating {concept} through the lens of {metaphor_type}..."):
            # This is a placeholder for your AI Orchestrator Logic
            st.success("Mapping Successful")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("The Mapping")
                st.write(f"**Target Concept:** {concept}")
                st.write(f"**Metaphor Lens:** {metaphor_type}")
            
            with col2:
                st.subheader("The Lesson")
                st.info(f"Imagine {concept} as a {metaphor_type.lower()}... [AI Orchestrator output goes here]")

            # DATA CAPTURE: Logging the interaction to Google Sheets
            new_data = pd.DataFrame([{
                "Timestamp": pd.Timestamp.now(),
                "Concept": concept,
                "Metaphor": metaphor_type,
                "Role": "Student"
            }])
            # Note: This requires your sheet to have these headers ready
            # conn.create(data=new_data) 

# --- ADMIN / CMS VIEW ---
elif access_mode == "The Vault CMS (Admin)":
    st.header("🛠️ The Vault CMS")
    st.subheader("AI Orchestrator & Data Capture")
    
    # Optional password gate for the demo
    password = st.sidebar.text_input("Admin Password", type="password")
    
    if password == "vault2026": # Replace with your preferred demo password
        st.write("Current Pulse Check Data:")
        try:
            # Fetch existing data from Google Sheets to show off your data capture
            existing_data = conn.read()
            st.dataframe(existing_data)
        except Exception as e:
            st.error("Connect your Google Sheet in Streamlit Secrets to view live capture data.")
            
        st.divider()
        st.write("#### Orchestrator Controls")
        st.button("Reset Learning Maps")
        st.button("Export Pilot Data")
    else:
        st.warning("Please enter the Admin password in the sidebar to view data capture.")

# Footer
st.sidebar.markdown("---")
st.sidebar.write("© 2026 The Vault | Universal Metaphor Learning")
