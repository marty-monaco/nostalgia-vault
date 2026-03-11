import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. APP CONFIG ---
st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="centered")

# --- 2. LOAD DATA (Pandas Direct Method) ---
@st.cache_data(ttl=60)
def load_cms_data():
    try:
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        csv_url = raw_url.replace('/edit?usp=sharing', '/export?format=csv').split('/edit')[0] + '/export?format=csv&gid=0'
        return pd.read_csv(csv_url)
    except Exception as e:
        st.error(f"CMS Sync Error: {e}")
        return None

df_cms = load_cms_data()

if df_cms is not None:
    # --- 3. SIDEBAR SELECTION ---
    st.sidebar.title("⚡ The Vault")
    topic = st.sidebar.selectbox("Select a Vault Story", df_cms["Topic"].tolist())
    row = df_cms[df_cms["Topic"] == topic].iloc[0]

    # --- 4. SESSION STATE ---
    if 'step' not in st.session_state: st.session_state.step = "pre_test"
    if 'current_topic' not in st.session_state: st.session_state.current_topic = topic

    if st.session_state.current_topic != topic:
        st.session_state.current_topic = topic
        st.session_state.step = "pre_test"
        st.rerun()

    # --- 5. STEP 1: PRE-TEST (2 QUESTIONS) ---
    if st.session_state.step == "pre_test":
        st.title(f"🔍 Pre-Assessment: {topic}")
        
        # Q1 logic
        ans_pre1 = st.radio(row["Pre_Q1"], [row["Pre_Opt1"], row["Pre_Opt2"], row["Pre_Opt3"]], index=None, key="p1")
        # Q2 logic
        ans_pre2 = st.radio(row["Pre_Q2"], [row["Pre_Opt1_Q2"], row["Pre_Opt2_Q2"], row["Pre_Opt3_Q2"]], index=None, key="p2")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1: class_code = st.text_input("Class Code")
        with col2: student_id = st.text_input("Initials")

        if st.button("ENTER THE VAULT ⚡"):
            if not class_code or not student_id or ans_pre1 is None or ans_pre2 is None:
                st.error("Please answer both questions and provide your ID.")
            else:
                st.session_state.update({"class_code": class_code, "student_id": student_id, 
                                        "ans_pre1": ans_pre1, "ans_pre2": ans_pre2, "step": "vault_content"})
                st.rerun()

    # --- 6. STEP 2: VIDEO & PULSE CHECK ---
    elif st.session_state.step == "vault_content":
        st.title(f"⚡ {topic}")
        
        # Video Logic with RickRoll Fallback
        v_url = str(row["Video_URL"]).strip()
        final_video = v_url if v_url != "nan" and v_url != "" else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        st.video(final_video)
        
        st.write("### 🧠 Pulse Check")
        ans_post1 = st.radio(row["Post_Q1"], [row["Post_Opt1"], row["Post_Opt2"], row["Post_Opt3"]], index=None, key="pst1")
        ans_post2 = st.radio(row["Post_Q2"], [row["Post_Opt1_Q2"], row["Post_Opt2_Q2"], row["Post_Opt3_Q2"]], index=None, key="pst2")
        
        st.divider()
        # HARDCODED NPS QUESTION: Ensures consistency across all Vault Stories
        nps_q = "On a scale of 0-10, how likely are you to recommend The Vault to a peer or friend?"
        st.write(f"### 📈 Feedback")
        st.write(nps_q)
        
        # Scale 0-10
        nps_val = st.select_slider(
            "Slide to select your score:", 
            options=list(range(0, 11)), 
            value=8,
            help="0 = Not at all likely, 10 = Extremely likely"
        )

        if st.button("SUBMIT TO THE VAULT 🚀"):
            if ans_post1 is None or ans_post2 is None:
                st.error("Please complete the Pulse Check.")
            else:
                # SCORING LOGIC (Comparing against hidden "A" columns)
                score_pre = (1 if st.session_state.ans_pre1 == row["Pre_A1"] else 0) + (1 if st.session_state.ans_pre2 == row["Pre_A2"] else 0)
                score_post = (1 if ans_post1 == row["Post_A1"] else 0) + (1 if ans_post2 == row["Post_A2"] else 0)
                
                final_record = {
                    "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "Topic": [topic], "Student": [st.session_state.student_id],
                    "Pre_Score": [score_pre], "Post_Score": [score_post],
                    "Lift": [score_post - score_pre], "NPS": [nps_val]
                }
                
                # Save to CSV
                df_save = pd.DataFrame(final_record)
                df_save.to_csv("vault_data.csv", mode='a', header=not os.path.exists("vault_data.csv"), index=False)
                
                st.success(f"Mastery Logged! Knowledge Lift: {score_post - score_pre}")
                st.balloons()

