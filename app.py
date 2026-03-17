import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. APP CONFIG ---
st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="wide")

# --- 2. DATA LOADING ---
@st.cache_data(ttl=60)
def load_cms_data():
    try:
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        csv_url = raw_url.replace('/edit?usp=sharing', '/export?format=csv').split('/edit')[0] + '/export?format=csv&gid=0'
        return pd.read_csv(csv_url)
    except:
        return None

df_cms = load_cms_data()

# --- 3. NAVIGATION & SESSION INITIALIZATION ---
if 'step' not in st.session_state:
    st.session_state.step = "pre_test"

st.sidebar.title("⚡ THE VAULT")
nav = st.sidebar.radio("Navigation", ["Learning Portal", "Pilot Summary (Admin)"])

if df_cms is not None:
    topic_list = df_cms["Topic"].tolist()
    
    if nav == "Learning Portal":
        # SIDEBAR SELECTION
        topic_choice = st.sidebar.selectbox("Select a Vault Story", topic_list)
        
        # Reset if they switch topics mid-stream
        if 'active_topic' not in st.session_state or st.session_state.active_topic != topic_choice:
            st.session_state.active_topic = topic_choice
            st.session_state.step = "pre_test"
            
        # PULL THE ROW ONCE PER RERUN
        current_row = df_cms[df_cms["Topic"] == st.session_state.active_topic].iloc[0]

        # --- STEP 1: PRE-TEST ---
        if st.session_state.step == "pre_test":
            st.title(f"🔍 Pre-Assessment: {st.session_state.active_topic}")
            
            p1 = st.radio(current_row["Pre_Q1"], [current_row["Pre_Opt1"], current_row["Pre_Opt2"], current_row["Pre_Opt3"]], index=None)
            p2 = st.radio(current_row["Pre_Q2"], [current_row["Pre_Opt1_Q2"], current_row["Pre_Opt2_Q2"], current_row["Pre_Opt3_Q2"]], index=None)
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1: class_code = st.text_input("Class Code")
            with c2: student_id = st.text_input("Student Initials")

            if st.button("ENTER THE VAULT ⚡"):
                if not class_code or not student_id or p1 is None or p2 is None:
                    st.warning("Please complete all fields.")
                else:
                    st.session_state.update({
                        "class_code": class_code, "student_id": student_id,
                        "ans_pre1": p1, "ans_pre2": p2, "step": "vault_content"
                    })
                    st.rerun()

        # --- STEP 2: VIDEO & PULSE CHECK ---
        elif st.session_state.step == "vault_content":
            st.title(f"⚡ {st.session_state.active_topic}")
            
            # VIDEO LOGIC
            v_link = str(current_row.get("Video_URL", "")).strip()
            final_v = v_link if v_link.startswith("http") else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            st.video(final_v)
            
            st.divider()
            st.write("### 🧠 Pulse Check")
            
            # THE QUESTIONS (Re-referenced from current_row)
            pst1 = st.radio(current_row["Post_Q1"], [current_row["Post_Opt1"], current_row["Post_Opt2"], current_row["Post_Opt3"]], index=None)
            pst2 = st.radio(current_row["Post_Q2"], [current_row["Post_Opt1_Q2"], current_row["Post_Opt2_Q2"], current_row["Post_Opt3_Q2"]], index=None)
            
            st.divider()
            nps = st.select_slider("Would you recommend The Vault?", options=list(range(0, 11)), value=8)

            if st.button("LOG MASTERY & FINISH 🚀"):
                if pst1 is None or pst2 is None:
                    st.error("Please answer the Pulse Check.")
                else:
                    # DUPLICATE CHECK
                    is_dup = False
                    if os.path.isfile("vault_data.csv"):
                        hist = pd.read_csv("vault_data.csv")
                        if not hist[(hist['Student']==st.session_state.student_id) & (hist['Topic']==st.session_state.active_topic)].empty:
                            is_dup = True

                    if is_dup:
                        st.warning("Mastery already logged for this topic.")
                    else:
                        # CALCULATE SCORES
                        s_pre = (1 if st.session_state.ans_pre1 == current_row["Pre_A1"] else 0) + (1 if st.session_state.ans_pre2 == current_row["Pre_A2"] else 0)
                        s_post = (1 if pst1 == current_row["Post_A1"] else 0) + (1 if pst2 == current_row["Post_A2"] else 0)
                        
                        # SAVE
                        res = {"Timestamp": [datetime.now()], "Class": [st.session_state.class_code], 
                               "Student": [st.session_state.student_id], "Topic": [st.session_state.active_topic],
                               "Pre_Score": [s_pre], "Post_Score": [s_post], "Lift": [s_post - s_pre], "NPS": [nps]}
                        pd.DataFrame(res).to_csv("vault_data.csv", mode='a', header=not os.path.exists("vault_data.csv"), index=False)
                        st.success(f"Mastery Logged! Lift: {s_post - s_pre}")
                        st.balloons()

            if st.button("Return to Start"):
                st.session_state.step = "pre_test"
                st.rerun()

    # --- 4. ADMIN DASHBOARD ---
    elif nav == "Pilot Summary (Admin)":
        st.title("🔐 Pilot Summary Dashboard")
        if os.path.isfile("vault_data.csv"):
            df_log = pd.read_csv("vault_data.csv")
            st.metric("Avg. Knowledge Lift", f"{df_log['Lift'].mean():+.2f} pts")
            st.dataframe(df_log, use_container_width=True)
        else:
            st.info("No data yet.")





