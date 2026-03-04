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
        font-weight: bold; width: 100%; border: none; padding: 12px;
    }
    .stButton>button:hover { background-color: #00ffff; color: black; }
    .privacy-box { 
        border: 1px solid #ff00ff; padding: 15px; border-radius: 8px; 
        font-size: 0.85em; margin-bottom: 20px; background-color: #1a1c24; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOAD DATA (Pandas Export Method) ---
@st.cache_data(ttl=60)
def load_cms_data():
    try:
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        csv_url = raw_url.replace('/edit?usp=sharing', '/export?format=csv').split('/edit')[0] + '/export?format=csv&gid=0'
        return pd.read_csv(csv_url)
    except Exception as e:
        st.error(f"CMS Load Error: {e}")
        return None

df_cms = load_cms_data()

if df_cms is not None:
    # --- 4. SIDEBAR ---
    st.sidebar.title("⚡ The Vault")
    topic_list = df_cms["Topic"].tolist()
    topic = st.sidebar.selectbox("Select a Vault Story", topic_list)
    row = df_cms[df_cms["Topic"] == topic].iloc[0]

    # --- 5. SESSION STATE & FLOW ---
    if 'step' not in st.session_state: st.session_state.step = "pre_test"
    if 'current_topic' not in st.session_state: st.session_state.current_topic = topic

    if st.session_state.current_topic != topic:
        st.session_state.current_topic = topic
        st.session_state.step = "pre_test"
        st.rerun()

    # --- 6. STEP 1: PRE-TEST (2 QUESTIONS) ---
    if st.session_state.step == "pre_test":
        st.title(f"🔍 Pre-Assessment: {topic}")
        st.write("Establish your baseline before entering the Vault.")
        
        pre_q1 = st.radio(row["Pre_Q1"], [row["Pre_Opt1"], row["Pre_Opt2"], row["Pre_Opt3"]], index=None, key="p1")
        pre_q2 = st.radio(row["Pre_Q2"], [row["Pre_Opt1_Q2"], row["Pre_Opt2_Q2"], row["Pre_Opt3_Q2"]], index=None, key="p2")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1: class_code = st.text_input("Class Code", placeholder="e.g. IVY-HS-101")
        with col2: student_id = st.text_input("Initials", placeholder="e.g. MM")

        if st.button("ENTER THE VAULT ⚡"):
            if not class_code or not student_id or pre_q1 is None or pre_q2 is None:
                st.error("Please answer both questions and provide your ID.")
            else:
                st.session_state.update({
                    "class_code": class_code, "student_id": student_id, 
                    "pre_1": pre_q1, "pre_2": pre_q2, "step": "vault_content"
                })
                st.rerun()

    # --- 7. STEP 2: VIDEO & PULSE CHECK (2 QUESTIONS + NPS) ---
    elif st.session_state.step == "vault_content":
        st.title(f"⚡ {topic}")
        
        # Video Sanitization
        v_url = str(row["Video_URL"]).strip()
        if v_url and v_url != "nan":
            st.video(v_url)
        else:
            st.warning("Video placeholder: Content is being digitized for the Vault.")
        
        st.write("### 🧠 Pulse Check")
        post_q1 = st.radio(row["Post_Q1"], [row["Post_Opt1"], row["Post_Opt2"], row["Post_Opt3"]], index=None, key="post1")
        post_q2 = st.radio(row["Post_Q2"], [row["Post_Opt1_Q2"], row["Post_Opt2_Q2"], row["Post_Opt3_Q2"]], index=None, key="post2")
        
        st.divider()
        st.write("### 📈 Student Feedback")
        nps_score = st.select_slider("How likely are you to recommend this lesson?", options=list(range(0, 11)), value=9)

        if st.button("SUBMIT FINAL RESULTS 🚀"):
            if post_q1 is None or post_q2 is None:
                st.error("Please complete both Pulse Check questions.")
            else:
                # Comparison Logic: Check if answers changed or stayed correct
                # (Assumes Pre_A and Post_A are in your spreadsheet for grading)
                is_correct_1 = "Correct" if post_q1 == row["Post_A"] else "Incorrect"
                is_correct_2 = "Correct" if post_q2 == row["Post_A_Q2"] else "Incorrect"

                final_data = {
                    "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "Class": [st.session_state.class_code],
                    "Student": [st.session_state.student_id],
                    "Topic": [topic],
                    "Pre_1": [st.session_state.pre_1], "Post_1": [post_q1], "Result_1": [is_correct_1],
                    "Pre_2": [st.session_state.pre_2], "Post_2": [post_q2], "Result_2": [is_correct_2],
                    "NPS": [nps_score]
                }
                
                # Save to Local CSV
                csv_file = "vault_data.csv"
                new_df = pd.DataFrame(final_data)
                if not os.path.isfile(csv_file): new_df.to_csv(csv_file, index=False)
                else: new_df.to_csv(csv_file, mode='a', header=False, index=False)
                
                st.success("Mastery Logged! You've successfully cleared the Vault.")
                st.balloons()
                if st.button("Return to Selection"):
                    st.session_state.step = "pre_test"
                    st.rerun()

    # --- 8. ADMIN DASHBOARD: KNOWLEDGE LIFT ANALYTICS ---
    st.divider()
    with st.expander("🔐 Admin: Knowledge Lift Analytics"):
        if os.path.isfile("vault_data.csv"):
            df_log = pd.read_csv("vault_data.csv")
            
            # Simple Mastery Visualization
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                st.metric("Total Learners", len(df_log))
            with m_col2:
                avg_nps = df_log["NPS"].mean()
                st.metric("Avg NPS", f"{avg_nps:.1f}/10")
            with m_col3:
                lift_calc = (df_log["Result_1"] == "Correct").mean() * 100
                st.metric("Mastery Rate", f"{lift_calc:.0f}%")
            
            st.write("#### Live Mastery Stream")
            st.dataframe(df_log.tail(10))
            st.download_button("Download Data", df_log.to_csv(index=False), "vault_pilot_data.csv")
        else:
            st.info("The Vault is awaiting its first student record.")
