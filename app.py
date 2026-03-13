import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. APP CONFIG ---
st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="wide")

# --- 2. CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { 
        background-color: #ff00ff; color: white; border-radius: 8px; 
        font-weight: bold; width: 100%; border: none; padding: 12px;
    }
    .stButton>button:hover { background-color: #00ffff; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA ORCHESTRATION ---
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

# --- 4. NAVIGATION ---
st.sidebar.title("⚡ THE VAULT")
nav = st.sidebar.radio("Navigation", ["Learning Portal", "Pilot Summary (Admin)"])

if df_cms is not None:
    topic_list = df_cms["Topic"].tolist()
    
    if nav == "Learning Portal":
        topic = st.sidebar.selectbox("Select a Vault Story", topic_list)
        row = df_cms[df_cms["Topic"] == topic].iloc[0]

        if 'current_topic' not in st.session_state or st.session_state.current_topic != topic:
            st.session_state.current_topic = topic
            st.session_state.step = "pre_test"

        # STEP 1: PRE-TEST
        if st.session_state.step == "pre_test":
            st.title(f"🔍 Pre-Assessment: {topic}")
            ans_pre1 = st.radio(row["Pre_Q1"], [row["Pre_Opt1"], row["Pre_Opt2"], row["Pre_Opt3"]], index=None, key="p1")
            ans_pre2 = st.radio(row["Pre_Q2"], [row["Pre_Opt1_Q2"], row["Pre_Opt2_Q2"], row["Pre_Opt3_Q2"]], index=None, key="p2")
            
            st.divider()
            col1, col2 = st.columns(2)
            with col1: class_code = st.text_input("Class Code")
            with col2: student_id = st.text_input("Student Initials")

            if st.button("ENTER THE VAULT ⚡"):
                if not class_code or not student_id or ans_pre1 is None or ans_pre2 is None:
                    st.warning("Please complete all fields.")
                else:
                    st.session_state.update({"class_code": class_code, "student_id": student_id, 
                                            "ans_pre1": ans_pre1, "ans_pre2": ans_pre2, "step": "vault_content"})
                    st.rerun()

        # STEP 2: VIDEO & PULSE CHECK
        elif st.session_state.step == "vault_content":
            st.title(f"⚡ {topic}")
            v_url = str(row.get("Video_URL", "")).strip()
            # FIXED SYNTAX HERE
            final_video = v_url if v_url != "nan" and v_url != "" else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            st.video(final_video)
            
            st.write("### 🧠 Pulse Check")
            ans_post1 = st.radio(row["Post_Q1"], [row["Post_Opt1"], row["Post_Opt2"], row["Post_Opt3"]], index=None, key="pst1")
            ans_post2 = st.radio(row["Post_Q2"], [row["Post_Opt1_Q2"], row["Post_Opt2_Q2"], row["Post_Opt3_Q2"]], index=None, key="pst2")
            
            st.divider()
            nps_val = st.select_slider("How likely are you to recommend The Vault to a peer?", options=list(range(0, 11)), value=8)

           if st.button("LOG MASTERY & FINISH 🚀"):
                if ans_post1 is None or ans_post2 is None:
                    st.error("Please complete the Pulse Check.")
                else:
                    # --- DUPLICATE CHECK LOGIC ---
                    is_duplicate = False
                    if os.path.isfile("vault_data.csv"):
                        existing_df = pd.read_csv("vault_data.csv")
                        # Check if this student has already submitted for THIS topic in THIS class
                        duplicate_check = existing_df[
                            (existing_df['Student'] == st.session_state.student_id) & 
                            (existing_df['Topic'] == topic) &
                            (existing_df['Class'] == st.session_state.class_code)
                        ]
                        if not duplicate_check.empty:
                            is_duplicate = True

                    if is_duplicate:
                        st.warning(f"⚡ Mastery already logged! {st.session_state.student_id}, you have already completed the {topic} vault for this class.")
                    else:
                        # MASTERY TRACKER LOGIC
                        score_pre = (1 if st.session_state.ans_pre1 == row.get("Pre_A1") else 0) + (1 if st.session_state.ans_pre2 == row.get("Pre_A2") else 0)
                        score_post = (1 if ans_post1 == row.get("Post_A1") else 0) + (1 if ans_post2 == row.get("Post_A2") else 0)
                        lift = score_post - score_pre
                        
                        final_record = {
                            "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                            "Class": [st.session_state.class_code],
                            "Student": [st.session_state.student_id],
                            "Topic": [topic],
                            "Pre_Score": [score_pre],
                            "Post_Score": [score_post],
                            "Lift": [lift],
                            "NPS": [nps_val]
                        }
                        
                        pd.DataFrame(final_record).to_csv("vault_data.csv", mode='a', header=not os.path.exists("vault_data.csv"), index=False)
                        st.success(f"Mastery Logged! Knowledge Lift: {lift} pts")
                        st.balloons()
                    
                    if st.button("Start New Topic"):
                        st.session_state.step = "pre_test"
                        st.rerun()

    # --- 6. PAGE: PILOT SUMMARY ---
    elif nav == "Pilot Summary (Admin)":
        st.title("🔐 Pilot Summary & Mastery Dashboard")
        if os.path.isfile("vault_data.csv"):
            df_log = pd.read_csv("vault_data.csv")
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.metric("Learners Engaged", len(df_log))
            with m2: st.metric("Avg. Pre-Test", f"{df_log['Pre_Score'].mean():.1f}/2")
            with m3: st.metric("Avg. Knowledge Lift", f"{df_log['Lift'].mean():+.1f} pts")
            
            promoters = len(df_log[df_log['NPS'] >= 9])
            detractors = len(df_log[df_log['NPS'] <= 6])
            nps_score = ((promoters - detractors) / len(df_log)) * 100 if len(df_log) > 0 else 0
            with m4: st.metric("Platform NPS", f"{int(nps_score)}")

            st.dataframe(df_log.sort_values(by="Timestamp", ascending=False), use_container_width=True)
            st.download_button("📥 Export CSV", df_log.to_csv(index=False), "vault_pilot_data.csv")
        else:
            st.warning("No pilot data found yet.")

