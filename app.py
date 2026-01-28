import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Nostalgia Vault: Pilot", page_icon="⚡", layout="centered")

# --- HEADER ---
st.title("⚡ The Nostalgia Vault")
st.subheader("Middle School Pilot: Local Archive Mode")

# --- 1. STUDENT INFO ---
with st.container():
    st.write("### 📝 1. Your Info")
    col1, col2 = st.columns(2)
    with col1:
        class_code = st.text_input("Class Code", placeholder="e.g. WI-RAPIDS-01")
    with col2:
        student_id = st.text_input("Initials", placeholder="e.g. MM")

# --- 2. KNOWLEDGE CHECK ---
st.divider()
st.write("### 🧠 2. 8-Second Knowledge Check: Titanic")

q1 = st.radio(
    "What was the 'Secret Mission' that led Dr. Ballard to the Titanic?",
    ["Finding lost Cold War submarines", "Searching for Atlantis", "Testing a new sonar for NASA"],
    index=None
)

q2 = st.radio(
    "What method did Ballard use to finally spot the debris field?",
    ["Sonar", "Argo", "Radar"],
    index=None
)

q3 = st.select_slider(
    "Rate your 'Nostalgia Spark' (How much did this make you want to learn more?)",
    options=["1 (Low)", "2", "3", "4", "5 (High)"],
    value="3"
)

# --- 3. LOCAL CSV LOGIC ---
if st.button("🚀 LOG DATA TO THE VAULT"):
    if not class_code or not student_id or q1 is None or q2 is None:
        st.error("Please fill out all fields!")
    else:
        # Create the data row
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Class": class_code,
            "Student": student_id,
            "Q1": q1,
            "Q2": q2,
            "Interest": q3
        }])
        
        # Save to local CSV (creates it if it doesn't exist)
        csv_file = "pilot_data.csv"
        if not os.path.isfile(csv_file):
            new_row.to_csv(csv_file, index=False)
        else:
            new_row.to_csv(csv_file, mode='a', header=False, index=False)
        
        st.success(f"Success, {student_id}! Response archived locally.")
        st.balloons()

# --- 4. ADMIN VIEW (To show the judges the data is real) ---
with st.expander("Admin: View Archived Data"):
    if os.path.isfile("pilot_data.csv"):
        df = pd.read_csv("pilot_data.csv")
        st.dataframe(df)
        # Add a download button so you can get the data out
        st.download_button("Download CSV", df.to_csv(index=False), "pilot_data.csv", "text/csv")
    else:
        st.write("No data archived yet.")

