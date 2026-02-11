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
    st.video("https://www.youtube.com/watch?v=T_UJBPRYvcg") 
    
    st.write("### 🧠 DNA Pulse Check")
    q1 = st.radio("Who made the discovery that DNA was as unique as a fingerprint?", ["Dr Alec Jeffries", "Dr Henry Lees", "Dr Michael Baden"], index=None)
    q2 = st.radio("True or False: DNA is now widely used to determine paternity?.", ["True", "False"], index=None)
    nps_score = st.select_slider("How likely are you to recommend The Vault to a friend or classmate?", options=list(range(0, 11)), value=8, help="0 = Not at all likely, 10 = Extremely likely")

elif topic == "The Titanic":
    st.subheader("🚢 The Unsinkable Physics")
    st.video("https://www.youtube.com/watch?v=UyeVqTkuPAM") 
    
    st.write("### 🧠 Buoyancy Pulse Check")
    q1 = st.radio("What method did Robert Ballard use to search?", ["SONAR", "RADAR", "Argo Robot"], index=None)
    q2 = st.radio("What was the original reason for the mission?", ["Map the floor of the North Atlantic", "Search for lost Nuclear Subs", "Searching for hydrothermal vents"], index=None)
    nps_score = st.select_slider("How likely are you to recommend The Vault to a friend or classmate?", options=list(range(0, 11)), value=8, help="0 = Not at all likely, 10 = Extremely likely")

elif topic == "The Space Shuttle Columbia":
    st.subheader("🚀 The Thermal Shield")
    st.video("https://www.youtube.com/watch?v=PmUwi8E_bzk") 
    
    st.write("### 🧠 Engineering Pulse Check")
    q1 = st.radio("What was the visionary idea that Space Shuttle Columbia was built for??", ["Rapid Transit to the Moon", "Unmanned Mars MIssion", "FIrst Re-Usable Spacecraft"], index=None)
    q2 = st.radio("What was the Space Shuttle's biggest challenge?", ["Launch", "Atmospheric Re-entry", "Orbit"], index=None)
    nps_score = st.select_slider("How likely are you to recommend The Vault to a friend or classmate?", options=list(range(0, 11)), value=8, help="0 = Not at all likely, 10 = Extremely likely")
    
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
            # 1. Create the data row
            new_data = {
                "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                "Class": [class_code],
                "Student": [student_id],
                "Topic": [topic],
                "Q1": [q1],
                "Q2": [q2],
                "NPS_Score": [nps_score]
            }
            new_df = pd.DataFrame(new_data)

            # 2. Save to CSV (This is the missing "Engine"!)
            # If the file doesn't exist, create it with headers. 
            # If it does, append the new row.
            if not os.path.isfile("vault_data.csv"):
                new_df.to_csv("vault_data.csv", index=False)
            else:
                new_df.to_csv("vault_data.csv", mode='a', header=False, index=False)

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








