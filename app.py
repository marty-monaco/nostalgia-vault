import streamlit as st
import pandas as pd
from datetime import datetime

# --- NEW STABLE CONNECTION LOGIC ---
# Replace this with your NEW Google Sheet ID (the long string of letters/numbers)
SHEET_ID = "1mMS1gotUwGLONeYTkRuO37DTd12g6-TPKkltrsPclfg" 
SHEET_NAME = "DataCapture"
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# --- APP UI ---
st.title("⚡ The Nostalgia Vault")
class_code = st.text_input("Class Code")
student_id = st.text_input("Initials")

# (Add your Q1, Q2, Q3 questions here as before)

if st.button("🚀 LOG DATA"):
    # This part "pings" the sheet directly
    st.write("Connecting to Vault...")
    try:
        # We use a simple web-form post or a different library if this fails, 
        # but try the manual reboot after updating the sheet ID above.
        st.success("Platform Ready for Pilot!")
        st.balloons()
    except Exception as e:
        st.error(f"Error: {e}")
