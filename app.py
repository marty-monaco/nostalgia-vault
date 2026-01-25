import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- APP CONFIG & STYLING ---
st.set_page_config(page_title="Nostalgia Vault: Pulse Check", page_icon="🕹️", layout="centered")

# Custom CSS for that 80s/Neon Startup vibe
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { background-color: #ff007f; color: white; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.title("🕹️ The Nostalgia Vault")
st.subheader("8-Second Pulse Check: Student Edition")
st.write("Complete this quick check to unlock your 'Vault' points!")

# --- STEP 1: IDENTIFICATION ---
with st.expander("Step 1: Your Info", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        class_code = st.text_input("Class Code", placeholder="e.g. ND-HIST-101")
    with col2:
        student_id = st.text_input("Student Initials", placeholder="e.g. MM")

# --- STEP 2: THE CONTENT CHECK ---
# (Note: In production, these questions would pull from a database based on the Video ID)
st.divider()
st.write("### Step 2: Knowledge Check")

q1 = st.selectbox(
    "1. What was the secret mission behind finding the Titanic?",
    ["Select an answer...", "A tourism promo", "A secret Cold War Navy mission", "A movie production"]
)

q2 = st.radio(
    "2. Why is the Titanic currently disappearing?",
    ["Rust from the salt water", "Iron-eating bacteria", "Giant squid attacks"]
)

q3 = st.select_slider(
    "3. On a scale of 1-5, how much do you want to learn more about this?",
    options=[1, 2, 3, 4, 5], value=3
)

# --- STEP 3: DATA LOGGING ---
if st.button("🚀 SUBMIT TO THE VAULT"):
    if q1 == "Select an answer..." or not class_code:
        st.error("Please provide your class code and answer all questions!")
    else:
        # Create a dictionary for the new data
        new_data = {
            "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            "Class_Code": [class_code],
            "Student": [student_id],
            "Q1_Response": [q1],
            "Q2_Response": [q2],
            "Engagement_Score": [q3],
            "Correct": [1 if q1 == "A secret Cold War Navy mission" and q2 == "Iron-eating bacteria" else 0]
        }
        
        df_new = pd.DataFrame(new_data)

        # Save to CSV (Appends if file exists, creates if not)
        file_path = "pilot_data_log.csv"
        if not os.path.isfile(file_path):
            df_new.to_csv(file_path, index=False)
        else:
            df_new.to_csv(file_path, mode='a', header=False, index=False)

        st.success("Data Logged! You've successfully contributed to the pilot.")
        st.balloons()