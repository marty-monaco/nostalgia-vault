import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os
from datetime import datetime

# --- 1. APP CONFIG ---   
st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="centered")

# --- 2. CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { 
        background-color: #ff00ff; 
        color: white; 
        border-radius: 8px; 
        font-weight: bold; 
        width: 100%; 
        border: none;
        padding: 10px;
    }
    .stButton>button:hover {
        background-color: #00ffff;
        color: black;
    }
    .privacy-box { 
        border: 1px solid #ff00ff; 
        padding: 15px; 
        border-radius: 8px; 
        font-size: 0.85em; 
        margin-bottom: 20px; 
        background-color: #1a1c24; 
    }
    .stRadio > label { font-weight: bold; color: #ff00ff; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONNECT TO CMS (Google Sheets) ---
try:
    # This connection looks for the URL in your Streamlit Cloud Secrets
    conn = st.connection("gsheets", type=GSheetsConnection)
    # worksheet="Curriculum" must match your Google Sheet tab name exactly
    df_cms = conn.read(worksheet="Curriculum", ttl="1m") 
except Exception as e:
    st.error("⚠️ CMS Connection Error. Check your Streamlit Secrets and ensure the Google Sheet is shared as 'Anyone with the link'.")
    st.stop()

# --- 4. DYNAMIC SIDEBAR ---
st.sidebar.title("⚡ The Vault")
topic_list = df_cms["Topic"].tolist()
topic = st.sidebar.selectbox("Select a Vault Story", topic_list)

# Filter the specific row of data for the chosen topic
row = df_cms[df_cms["Topic"] == topic].iloc[0]

# --- 5. SESSION STATE & TOPIC MONITOR ---
if 'step' not in st.session_state:
    st.session_state.step = "pre_test"
if 'current_topic' not in st.session_state:
    st.session_state.current_topic = topic

# RESET: If the user switches topics in the sidebar, reset to the Pre-Test
if st.session_state.current_topic != topic:
    st.session_state.current_topic = topic
    st.session_state.step = "pre_test"
    st.rerun()

# --- 6. STEP 1: PRE-TEST ---
if st.session_state.step == "pre_test":
    st.title(f"🔍 Pre-Assessment: {topic}")
    st.write("Before we enter the Vault, let's establish a baseline.")

    # Load Question from the CMS row
    pre_q1 = st.radio(
        row["Pre_Q1"], 
        [row["Pre_Opt1"], row["Pre_Opt2"], row["Pre_Opt3"]], 
        index=None
    )

    st.divider()
    st.markdown('<div class="privacy-box"><b>Privacy Notice:</b> Please use initials or a nickname only for the pilot.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        class_code = st.text_input("Class Code", placeholder="e.g. IVY-HS-101")
    with col2:
        student_id = st.text_input("Initials/Nickname", placeholder="e.g. MM")

    if st.button("ENTER THE VAULT ⚡"):
        if not class_code or not student_id or pre_q1 is None:
            st.error("Please answer the question and provide your identification.")
        else:
            st.session_state.class_code = class_code
            st.session_state.student_id = student_id
            st.session_state.pre_q1 = pre_q1
            st.session_state.step = "vault_content"
            st.rerun()

# --- 7. STEP 2: VIDEO & PULSE CHECK ---
elif st.session_state.step == "vault_content":
    st.title(f"⚡ {topic}")
    
    # Inject the YouTube video link from the Google Sheet
    st.video(row["Video_URL"])
    
    st.write("### 🧠 Pulse Check")
    # Load Mirrored Post-Test Question from the CMS row
    q1 = st.radio(
        row["Post_Q1"], 
        [row["Post_Opt1"], row["Post_Opt2"], row["Post_Opt3"]], 
        index=None
    )

    st.divider()
    nps_score = st.select_slider("Rate this learning experience (0-10):", options=list(range(0, 11)), value=8)

    if st.button("SUBMIT FINAL RESULTS 🚀"):
        if q1 is None:
            st.error("Please complete the Pulse Check to log your mastery.")
        else:
            # Package data for local CSV storage
            final_data = {
                "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                "Class": [st.session_state.class_code],
                "Student": [st.session_state.student_id],
                "Topic": [topic],
                "Pre_Answer": [st.session_state.pre_q1],
                "Post_Answer": [q1],
                "NPS_Score": [nps_score]
            }
            
            # Write to CSV
            csv_file = "vault_data.csv"
            new_df = pd.DataFrame(final_data)
            if not os.path.isfile(csv_file):
                new_df.to_csv(csv_file, index=False)
            else:
                new_df.to_csv(csv_file, mode='a', header=False, index=False)
            
            st.success("Mastery Logged! Data synced to the Vault.")
            st.balloons()
            
            if st.button("Explore Another Vault Story"):
                st.session_state.step = "pre_test"
                st.rerun()

# --- 8. ADMIN DASHBOARD (For Pilot Monitoring) ---
st.divider()
with st.expander("🔐 Admin: Pilot Data Logs"):
    if os.path.isfile("vault_data.csv"):
        df_log = pd.read_csv("vault_data.csv")
        st.write(f"Total Student Submissions: {len(df_log)}")
        st.dataframe(df_log.tail(10)) # Show the 10 most recent entries
        st.download_button(
            label="Download All Pilot Data",
            data=df_log.to_csv(index=False),
            file_name=f"vault_pilot_export_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("The Vault is awaiting its first student submission.")

