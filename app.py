import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="Nostalgia Vault: Pilot", page_icon="⚡", layout="centered")

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HEADER & STYLING ---
st.title("⚡ The Nostalgia Vault")
st.subheader("Middle School Pilot: Pulse Check")

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
st.write("### 🧠 2. 8-Second Knowledge Check")

q1 = st.radio(
    "Which '80s icon was originally called 'Puck-Man'?",
    ["The Walkman", "Pac-Man", "Mongoose BMX"],
    index=None
)

q2 = st.radio(
    "True or False: The Titanic was found during a secret Cold War mission.",
    ["True", "False"],
    index=None
)

q3 = st.select_slider(
    "How much did this help you understand the topic?",
    options=["1", "2", "3", "4", "5"],
    value="3"
)

# --- 3. SUBMIT LOGIC ---
st.divider()
if st.button("🚀 LOG DATA TO THE VAULT"):
    if not class_code or not student_id or q1 is None or q2 is None:
        st.error("Please fill out all fields before submitting!")
    else:
        try:
            # Create the data row
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Class": class_code,
                "Student": student_id,
                "Q1": q1,
                "Q2": q2,
                "Interest": q3
            }])
            
            # Pull existing data from the new tab and add the new row
            # Use ttl=0 to ensure we don't use old, 'Bad Request' cached data
            existing_data = conn.read(worksheet="DataCapture", ttl=0)
            updated_df = pd.concat([existing_data, new_row], ignore_index=True)
            
            # Push back to Google
            conn.update(worksheet="DataCapture", data=updated_df)
            
            st.success(f"Success, {student_id}! Data synced to the Vault.")
            st.balloons()
            
        except Exception as e:
            st.error(f"Vault Connection Error: {e}")
            st.info("Ensure your Google Sheet tab is named 'DataCapture' and Row 1 has the correct headers.")
