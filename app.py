import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. APP CONFIG ---
st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="centered")

# --- 2. CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { 
        background-color: #ff00ff; color: white; border-radius: 8px; 
        font-weight: bold; width: 100%; border: none; padding: 10px;
    }
    .stButton>button:hover { background-color: #00ffff; color: black; }
    .privacy-box { 
        border: 1px solid #ff00ff; padding: 15px; border-radius: 8px; 
        font-size: 0.85em; margin-bottom: 20px; background-color: #1a1c24; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DIRECT PANDAS CONNECTION (The Debugger Method) ---
@st.cache_data(ttl=60) # Caches data for 60 seconds
def load_cms_data():
    try:
        # Pull the URL from your Secrets
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        # Convert the standard URL to the "Export" URL that worked in debug
        csv_url = raw_url.replace('/edit?usp=sharing', '/export?format=csv')
        csv_url = csv_url.split('/edit')[0] + '/export?format=csv'
        
        # Add the specific worksheet (tab) name if it's not the first tab
        # If your tab is named 'Curriculum', we add it here:
        final_url = f"{csv_url}&gid=0" # Default is first tab. Change gid if needed.
        
        return pd.read_csv(final_url)
    except Exception as e:
        st.error(f"Failed to load CMS: {e}")
        return None

df_cms = load_cms_data()

if df_cms is not None:
    # --- 4. DYNAMIC SIDEBAR ---
    st.sidebar.title("⚡ The Vault")
    topic_list = df_cms["Topic"].tolist()
    topic = st.sidebar.selectbox("Select a Vault Story", topic_list)
    row = df_cms[df_cms["Topic"] == topic].iloc[0]

    # --- 5. SESSION STATE ---
    if 'step' not in st.session_state:
        st.session_state.step = "pre_test"
    if 'current_topic' not in st.session_state:
        st.session_state.current_topic = topic

    if st.session_state.current_topic != topic:
        st.session_state.current_topic = topic
        st.session_state.step = "pre_test"
        st.rerun()

    # --- 6. STEP 1: PRE-TEST ---
    if st.session_state.step == "pre_test":
        st.title(f"🔍 Pre-Assessment: {topic}")
        pre_q1 = st.radio(row["Pre_Q1"], [row["Pre_Opt1"], row["Pre_Opt2"], row["Pre_Opt3"]], index=None)
        
        st.divider()
        st.markdown('<div class="privacy-box"><b>Privacy Notice:</b> Please use initials or a nickname.</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: class_code = st.text_input("Class Code", placeholder="e.g. IVY-HS-101")
        with col2: student_id = st.text_input("Initials/Nickname", placeholder="e.g. MM")

        if st.button("ENTER THE VAULT ⚡"):
            if not class_code or not student_id or pre_q1 is None:
                st.error("Please answer and provide your ID.")
            else:
                st.session_state.class_code = class_code
                st.session_state.student_id = student_id
                st.session_state.pre_q1 = pre_q1
                st.session_state.step = "vault_content"
                st.rerun()

    # --- 7. STEP 2: VIDEO & PULSE CHECK ---
    elif st.session_state.step == "vault_content":
        st.title(f"⚡ {topic}")
        st.video(row["Video_URL"])
        st.write("### 🧠 Pulse Check")
        q1 = st.radio(row["Post_Q1"], [row["Post_Opt1"], row["Post_Opt2"], row["Post_Opt3"]], index=None)

        if st.button("SUBMIT FINAL RESULTS 🚀"):
            if q1 is None:
                st.error("Please complete the Pulse Check.")
            else:
                final_data = {
                    "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "Class": [st.session_state.class_code],
                    "Student": [st.session_state.student_id],
                    "Topic": [topic],
                    "Pre_Answer": [st.session_state.pre_q1],
                    "Post_Answer": [q1]
                }
                csv_file = "vault_data.csv"
                new_df = pd.DataFrame(final_data)
                if not os.path.isfile(csv_file): new_df.to_csv(csv_file, index=False)
                else: new_df.to_csv(csv_file, mode='a', header=False, index=False)
                
                st.success("Mastery Logged!")
                st.balloons()
                if st.button("Start New Topic"):
                    st.session_state.step = "pre_test"
                    st.rerun()

    # --- 8. ADMIN LOGS ---
    st.divider()
    with st.expander("🔐 Admin: Live Insights"):
        if os.path.isfile("vault_data.csv"):
            df_log = pd.read_csv("vault_data.csv")
            st.dataframe(df_log.tail(5))
            st.download_button("Download Data", df_log.to_csv(index=False), "vault_data.csv")
