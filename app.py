import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="centered")

# --- INITIALIZE SESSION STATE ---
# This tracks if the student has finished the Pre-Test
if 'step' not in st.session_state:
    st.session_state.step = "pre_test"

# --- TOPIC MONITOR ---
# If the user picks a new topic, reset the step to 'pre_test'
if 'current_topic' not in st.session_state:
    st.session_state.current_topic = topic

if st.session_state.current_topic != topic:
    st.session_state.current_topic = topic
    st.session_state.step = "pre_test"
    st.rerun()

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { background-color: #ff00ff; color: white; border-radius: 8px; width: 100%; }
    .privacy-box { border: 1px solid #ff00ff; padding: 10px; border-radius: 5px; font-size: 0.8em; margin-bottom: 20px; color: #bbbbbb; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (Persistent) ---
st.sidebar.title("⚡ The Vault")
topic = st.sidebar.selectbox("Select a Vault Story", ["DNA Fingerprinting", "The Titanic", "The Space Shuttle Columbia"])

# --- STEP 1: PRE-TEST & IDENTIFICATION ---
if st.session_state.step == "pre_test":
    st.title(f"🔍 Pre-Assessment: {topic}")
    st.write("Before we enter the Vault, let's see what you already know! (It's okay to guess)")

    # Dynamic Pre-Test Questions
    if topic == "DNA Fingerprinting":
        pre_q1 = st.radio("What year was DNA fingerprinting first used in a forensic case?", ["1974", "1986", "1992"], index=None)
        pre_q2 = st.radio("DNA is found in which part of the cell?", ["Ribosomes", "Nucleus", "Wall"], index=None)
    
    elif topic == "The Titanic":
        pre_q1 = st.radio("How deep does the Titanic wreck lie?", ["2,500 ft", "12,500 ft", "22,000 ft"], index=None)
        pre_q2 = st.radio("Which ship was famously closest but failed to respond?", ["Californian", "Carpathia", "Olympic"], index=None)
    
    elif topic == "The Space Shuttle Columbia":
        pre_q1 = st.radio("What material was the Shuttle's thermal shield made of?", ["Steel", "Ceramic Tiles", "Aluminum"], index=None)
        pre_q2 = st.radio("How many successful missions did Columbia fly before 2003?", ["5", "15", "27"], index=None)

    st.divider()
    st.markdown('<div class="privacy-box"><b>Privacy Notice:</b> Please use initials or a nickname only.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        class_code = st.text_input("Class Code", placeholder="e.g. WI-RAPIDS-01")
    with col2:
        student_id = st.text_input("Initials/Nickname", placeholder="e.g. ML")

    if st.button("ENTER THE VAULT ⚡"):
        if not class_code or not student_id or pre_q1 is None:
            st.error("Please answer the pre-test and provide your code/initials.")
        else:
            # Save Pre-Test Data to Session State to log later
            st.session_state.class_code = class_code
            st.session_state.student_id = student_id
            st.session_state.pre_q1 = pre_q1
            st.session_state.pre_q2 = pre_q2
            
            # Advance to the Video/Pulse Check
            st.session_state.step = "vault_content"
            st.rerun()

# --- STEP 2: VIDEO & PULSE CHECK ---
elif st.session_state.step == "vault_content":
    st.title(f"⚡ {topic}")
    
    # 1. Video Content
    if topic == "DNA Fingerprinting":
        st.video("https://www.youtube.com/watch?v=T_UJBPRYvcg")
    elif topic == "The Titanic":
        st.video("https://www.youtube.com/watch?v=UyeVqTkuPAM")
    elif topic == "The Space Shuttle Columbia":
        st.video("https://www.youtube.com/watch?v=PmUwi8E_bzk")

    # 2. Pulse Check (Post-Test)
    st.write("### 🧠 Pulse Check")
    if topic == "DNA Fingerprinting":
        q1 = st.radio("Who made the discovery that DNA was as unique as a fingerprint?", ["Dr Alec Jeffries", "Dr Henry Lees", "Dr Michael Baden"], index=None)
        q2 = st.radio("True or False: DNA is now widely used for paternity?", ["True", "False"], index=None)
    elif topic == "The Titanic":
        q1 = st.radio("What method did Robert Ballard use to search?", ["SONAR", "RADAR", "Argo Robot"], index=None)
        q2 = st.radio("What was the original reason for the mission?", ["Map the floor", "Search for lost Nuclear Subs", "Hydrothermal vents"], index=None)
    elif topic == "The Space Shuttle Columbia":
        q1 = st.radio("Columbia was the first visionary idea for...?", ["Transit to Moon", "Mars Mission", "Re-Usable Spacecraft"], index=None)
        q2 = st.radio("Biggest challenge?", ["Launch", "Atmospheric Re-entry", "Orbit"], index=None)

    # 3. NPS
    st.divider()
    nps_score = st.select_slider("How likely are you to recommend this Vault lesson?", options=list(range(0, 11)), value=8)

    if st.button("SUBMIT FINAL RESULTS 🚀"):
        if q1 is None:
            st.error("Please complete the Pulse Check before submitting.")
        else:
            # 1. Build the data row
            final_data = {
                "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                "Class": [st.session_state.class_code],
                "Student": [st.session_state.student_id],
                "Topic": [topic],
                "Pre_Q1": [st.session_state.pre_q1],
                "Pre_Q2": [st.session_state.pre_q2],
                "Post_Q1": [q1],
                "Post_Q2": [q2],
                "NPS_Score": [nps_score]
            }
            
            # 2. Save to CSV
            df = pd.DataFrame(final_data)
            if not os.path.isfile("vault_data.csv"):
                df.to_csv("vault_data.csv", index=False)
            else:
                df.to_csv("vault_data.csv", mode='a', header=False, index=False)

            st.success("Data logged! You have mastered this Vault story.")
            st.balloons()
            
            # Option to reset for another topic
            if st.button("Explore Another Story"):
                st.session_state.step = "pre_test"
                st.rerun()

# --- ADMIN SECTION ---
st.divider()
with st.expander("🔐 Admin: View Results"):
    if os.path.isfile("vault_data.csv"):
        df_view = pd.read_csv("vault_data.csv")
        st.dataframe(df_view.tail(5))
        st.download_button("Download CSV", data=df_view.to_csv(index=False), file_name="vault_data.csv")

