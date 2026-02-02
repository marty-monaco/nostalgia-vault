import streamlit as st
import pandas as pd  # <--- MUST HAVE THIS
import os             # <--- MUST HAVE THIS
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="centered")

# --- CUSTOM CSS FOR BRANDING ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { background-color: #ff00ff; color: white; border-radius: 8px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- APP NAVIGATION ---
st.title("⚡ The Nostalgia Vault")
topic = st.sidebar.selectbox("Select a Vault Story", ["DNA Fingerprinting", "The Titanic", "The Space Shuttle Columbia"])

# --- DYNAMIC CONTENT LOGIC ---
if topic == "DNA Fingerprinting":
    st.subheader("🧬 The Biological Barcode")
    st.video("https://youtube.com/shorts/T_UJBPRYvcg?si=wMzt-I5iB0eLs0cN") 
    
    st.write("### 🧠 DNA Pulse Check")
    q1 = st.radio("Who made the discovery that DNA was as unique as a fingerprint?", ["Dr Alec Jeffries", "Dr Henry Lees", "Dr Michael Baden"], index=None)
    q2 = st.radio("True or False: DNA is now widely used to determine paternity?.", ["True", "False"], index=None)
    interest = st.select_slider("Rate your interest in Forensic Science:", options=["1", "2", "3", "4", "5"], value="3")

elif topic == "The Titanic":
    st.subheader("🚢 The Unsinkable Physics")
    st.video("https://youtube.com/shorts/YOUR_TITANIC_LINK") 
    
    st.write("### 🧠 Buoyancy Pulse Check")
    q1 = st.radio("What method did Robert Ballard use to search?", ["SONAR", "RADAR", "Argo Robot"], index=None)
    q2 = st.radio("What was the original reason for the mission?", ["Map the floor of the North Atlantic", "Search for lost Nuclear Subs", "Searching for hydrothermal vents"], index=None)
    interest = st.select_slider("Rate your interest in Marine Engineering:", options=["1", "2", "3", "4", "5"], value="3")

elif topic == "The Space Shuttle Columbia":
    st.subheader("🚀 The Thermal Shield")
    st.video("https://youtube.com/shorts/UyeVqTkuPAM?si=G1AJoxY2dDwELXPT") 
    
    st.write("### 🧠 Engineering Pulse Check")
    q1 = st.radio("What was the visionary idea that Space Shuttle Columbia was built for??", ["Rapid Transit to the Moon", "Unmanned Mars MIssion", "FIrst Re-Usable Spacecraft"], index=None)
    q2 = st.radio("What was the Space Shuttle's biggest challenge?", ["Launch", "Atmospheric Re-entry", "Orbit"], index=None)
    interest = st.select_slider("Rate your interest in Aerospace Engineering:", options=["1", "2", "3", "4", "5"], value="3")
    
# --- UNIFIED SUBMISSION LOGIC ---
st.divider()
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        class_code = st.text_input("Class Code", placeholder="e.g. WI-RAPIDS-01")
    with col2:
        student_id = st.text_input("Initials", placeholder="e.g. ML")

    if st.button("🚀 SUBMIT TO THE VAULT"):
        if not class_code or not student_id or q1 is None:
            st.error("Please answer the questions and provide your ID.")
        else:
            # For now, we simulate success without the buggy Sheets connection
            st.success(f"Success! Your {topic} data has been logged to the Vault.")
            st.balloons()
            
          # --- ADMIN SECTION (Add this at the bottom of app.py) ---
st.divider()
with st.expander("🔐 Admin: Download Data"):
    if os.path.isfile("vault_data.csv"):
        with open("vault_data.csv", "rb") as file:
            st.download_button(
                label="Download CSV for Analysis",
                data=file,
                file_name=f"vault_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        # Optional: Show a preview of the last 5 entries
        st.write("### Recent Activity Preview")
        df_preview = pd.read_csv("vault_data.csv")
        st.dataframe(df_preview.tail(5))
    else:
        st.info("No data has been collected in the Vault yet. Once a student submits, the file will appear here.")


