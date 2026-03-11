import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. APP CONFIG ---
st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="wide")

# --- 2. CUSTOM CSS (Neon "Vault" Theme) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { 
        background-color: #ff00ff; color: white; border-radius: 8px; 
        font-weight: bold; width: 100%; border: none; padding: 12px;
    }
    .stButton>button:hover { background-color: #00ffff; color: black; }
    .metric-card {
        background-color: #1a1c24; border: 1px solid #ff00ff;
        padding: 20px; border-radius: 10px; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA ORCHESTRATION (The Pandas Direct Method) ---
@st.cache_data(ttl=60)
def load_cms_data():
    try:
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        csv_url = raw_url.replace('/edit?usp=sharing', '/export?format=csv').split('/edit')[0] + '/export?format=csv&gid=0'
        return pd.read_csv(csv_url)
    except Exception as e:
        st.error(f"Vault Connection Error: {e}")
        return None

df_cms = load_cms_data()

# --- 4. NAVIGATION & SIDEBAR ---
st.sidebar.title("⚡ THE VAULT")
nav = st.sidebar.radio("Navigation", ["Learning Portal", "Pilot Summary (Admin)"])

if df_cms is not None:
    topic_list = df_cms["Topic"].tolist()
    
    # --- 5. PAGE: LEARNING PORTAL ---
    if nav == "Learning Portal":
        topic = st.sidebar.selectbox("Select a Vault Story", topic_list)
        row = df_cms[df_cms["Topic"] == topic].iloc[0]

        # Reset logic if topic changes
        if 'current_topic' not in st.session_state or st.session_state.current_topic != topic:
            st.session_state.current_topic = topic
            st.session_state.step = "pre_test"

        # STEP 1: PRE-TEST
        if st.session_state.step == "pre_test":
            st.title(f"🔍 Pre-Assessment: {topic}")
            st.info("Establish your baseline before entering the Vault.")
            
            ans_pre1 = st.radio(row["Pre_Q1"], [row["Pre_Opt1"], row["Pre_Opt2"], row["Pre_Opt3"]], index=None, key="p1")
            ans_pre2 = st.radio(row["Pre_Q2"], [row["Pre_Opt1_Q2"], row["Pre_Opt2_Q2"], row["Pre_Opt3_Q2"]], index=None, key="p2")
            
            st.divider()
            col1, col2 = st.columns(2)
            with col1: class_code = st.text_input("Class Code (e.g., IVY-HS-101)")
            with col2: student_id = st.text_input("Student Initials")

            if st.button("ENTER THE VAULT ⚡"):
                if not class_code or not student_id or ans_pre1 is None or ans_pre2 is None:
                    st.warning("Please complete all fields to proceed.")
                else:
                    st.session_state.update({"class_code": class_code, "student_id": student_id, 
                                            "ans_pre1": ans_pre1, "ans_pre2": ans_pre2, "step": "vault_content"})
                    st.rerun()

        # STEP 2: VIDEO & PULSE CHECK
        elif st.session_state.step == "vault_content":
            st.title(f"⚡ {topic}")
            v_url = str(row.get("Video_URL", "")).strip()
            final_video = v_url if v_url != "nan" and v_url !=
