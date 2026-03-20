import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. APP CONFIG ---
st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="wide")

# --- CUSTOM CSS FOR MOBILE NAVIGATION ---
st.markdown("""
    <style>
        /* Target the Sidebar Chevron (Arrow) */
        [data-testid="stSidebarCollapseIcon"] {
            width: 55px !important;
            height: 55px !important;
            color: #FFD700 !important; /* Gold Vault Color */
        }
        
        /* Ensure the button background doesn't clip the big icon */
        button[kind="headerNoContext"] {
            width: 70px !important;
            height: 70px !important;
            background-color: rgba(255, 215, 0, 0.1) !important;
            border-radius: 10px !important;
        }

        /* Subtle pulse to catch the student's eye */
        [data-testid="stSidebarCollapseIcon"] {
            filter: drop-shadow(0px 0px 8px rgba(255, 215, 0, 0.6));
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA LOADING (CMS) ---
@st.cache_data(ttl=60)
def load_cms_data():
    try:
        # Pulling from your Secrets (Streamlit Cloud)
        raw_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        csv_url = raw_url.replace('/edit?usp=sharing', '/export?format=csv').split('/edit')[0] + '/export?format=csv&gid=0'
        return pd.read_csv(csv_url)
    except Exception as e:
        st.error(f"CMS Connection Error: {e}")
        return None

df_cms = load_cms_data()

# --- 3. SESSION INITIALIZATION ---
if 'step' not in st.session_state:
    st.session_state.step = "pre_test"
if 'start_time' not in st.session_state:
    st.session_state.start_time = None

# --- 4. NAVIGATION ---
st.sidebar.title("⚡ THE VAULT")
nav = st.sidebar.radio("Navigation", ["Learning Portal", "Pilot Summary (Admin)"])

if df_cms is not None:
    topic_list = df_cms["Topic"].tolist()
    
    if nav == "Learning Portal":
        topic_choice = st.sidebar.selectbox("Select a Vault Story", topic_list)
        
        # Reset logic if topic changes
        if 'active_topic' not in st.session_state or st.session_state.active_topic != topic_choice:
            st.session_state.active_topic = topic_choice
            st.session_state.step = "pre_test"
            st.session_state.start_time = None
            
        current_row = df_cms[df_cms["Topic"] == st.session_state.active_topic].iloc[0]

        # --- STEP 1: PRE-TEST ---
        if st.session_state.step == "pre_test":
            st.title(f"🔍 Pre-Assessment: {st.session_state.active_topic}")
            st.write("Complete this quick check to enter the Vault.")
            
            p1 = st.radio(current_row["Pre_Q1"], [current_row["Pre_Opt1"], current_row["Pre_Opt2"], current_row["Pre_Opt3"]], index=None, key="pre1")
            p2 = st.radio(current_row["Pre_Q2"], [current_row["Pre_Opt1_Q2"], current_row["Pre_Opt2_Q2"], current_row["Pre_Opt3_Q2"]], index=None, key="pre2")
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1: class_code = st.text_input("Class Code (e.g., CRIM171)", placeholder="Enter Class ID")
            with c2: student_id = st.text_input("Student Initials / ID", placeholder="e.g., MLM")

            if st.button("ENTER THE VAULT ⚡"):
                if not class_code or not student_id or p1 is None or p2 is None:
                    st.warning("Please complete all fields and questions.")
                else:
                    st.session_state.update({
                        "class_code": class_code, "student_id": student_id,
                        "ans_pre1": p1, "ans_pre2": p2, 
                        "step": "vault_content",
                        "start_time": datetime.now() # Engagement Timer Starts
                    })
                    st.rerun()

        # --- STEP 2: VIDEO & PULSE CHECK ---
        elif st.session_state.step == "vault_content":
            st.title(f"⚡ {st.session_state.active_topic}")
            
            # HARDENED VIDEO LOGIC (Converts Shorts & Handles Errors)
            v_link = str(current_row.get("Video_URL", "")).strip()
            # Ensure standard watch format
            if "shorts/" in v_link:
                v_link = v_link.replace("shorts/", "watch?v=")
            
            final_v = v_link if v_link.startswith("http") else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            
            st.video(final_v)
            
            st.divider()
            st.write("### 🧠 Pulse Check")
            pst1 = st.radio(current_row["Post_Q1"], [current_row["Post_Opt1"], current_row["Post_Opt2"], current_row["Post_Opt3"]], index=None, key="post1")
            pst2 = st.radio(current_row["Post_Q2"], [current_row["Post_Opt1_Q2"], current_row["Post_Opt2_Q2"], current_row["Post_Opt3_Q2"]], index=None, key="post2")
            
            st.divider()
            nps = st.select_slider("Would you recommend this lesson to a peer?", options=list(range(0, 11)), value=8)

            if st.button("LOG MASTERY & FINISH 🚀"):
                if pst1 is None or pst2 is None:
                    st.error("Please finish the Pulse Check.")
                else:
                    # DUPLICATE CHECK
                    is_dup = False
                    if os.path.isfile("vault_data.csv"):
                        hist = pd.read_csv("vault_data.csv")
                        if not hist[(hist['Student']==st.session_state.student_id) & (hist['Topic']==st.session_state.active_topic)].empty:
                            is_dup = True

                    if is_dup:
                        st.warning("Mastery already logged for this story.")
                    else:
                        # CALC ENGAGEMENT (Option B)
                        duration = (datetime.now() - st.session_state.start_time).total_seconds()
                        completion_pct = min(int((duration / 90) * 100), 100) # Assume 90s target
                        is_completed = 1 if completion_pct >= 85 else 0

                        # CALC LIFT
                        s_pre = (1 if st.session_state.ans_pre1 == current_row["Pre_A1"] else 0) + (1 if st.session_state.ans_pre2 == current_row["Pre_A2"] else 0)
                        s_post = (1 if pst1 == current_row["Post_A1"] else 0) + (1 if pst2 == current_row["Post_A2"] else 0)
                        
                        # SAVE
                        res = {
                            "Timestamp": [datetime.now()], "Class": [st.session_state.class_code], 
                            "Student": [st.session_state.student_id], "Topic": [st.session_state.active_topic],
                            "Pre_Score": [s_pre], "Post_Score": [s_post], "Lift": [s_post - s_pre], 
                            "NPS": [nps], "Duration_Sec": [int(duration)], "Completed": [is_completed]
                        }
                        pd.DataFrame(res).to_csv("vault_data.csv", mode='a', header=not os.path.exists("vault_data.csv"), index=False)
                        st.success(f"Knowledge Lift achieved! Score improved by {s_post - s_pre} points.")
                        st.balloons()
            
            if st.button("← Choose Another Story"):
                st.session_state.step = "pre_test"
                st.rerun()

    # --- 5. ADMIN DASHBOARD ---
    elif nav == "Pilot Summary (Admin)":
        st.title("🔐 Pilot Summary & Impact Dashboard")
        
        if os.path.isfile("vault_data.csv"):
            df_log = pd.read_csv("vault_data.csv")
            
            # --- PILLAR METRICS ---
            avg_lift = df_log['Lift'].mean()
            pct_lift = (avg_lift / 2) * 100
            
            promoters = len(df_log[df_log['NPS'] >= 9])
            detractors = len(df_log[df_log['NPS'] <= 6])
            nps_score = int(((promoters - detractors) / len(df_log)) * 100) if len(df_log) > 0 else 0

            m1, m2, m3 = st.columns(3)
            with m1: st.metric("Total Learners", len(df_log))
            with m2: st.metric("Mastery Gain %", f"{pct_lift:.1f}%", delta=f"{avg_lift:.2f} pts")
            with m3: st.metric("Platform NPS", nps_score)

            # --- SENTIMENT GAUGE ---
            st.write("### 🌡️ Platform Sentiment Gauge")
            norm_nps = (nps_score + 100) / 200
            st.progress(norm_nps)
            st.caption(f"Score: {nps_score} (-100 to +100 Scale)")

            st.divider()

            # --- TOPIC LEADERBOARD ---
            st.subheader("🏆 Topic Performance Leaderboard")
            leaderboard = df_log.groupby('Topic').agg({
                'Student': 'count', 'Lift': 'mean', 'NPS': 'mean', 'Completed': 'mean'
            }).rename(columns={'Student': 'Learners', 'Completed': 'Completion Rate'})
            st.dataframe(leaderboard.style.highlight_max(axis=0, color='#2e7d32', subset=['Lift', 'NPS']), use_container_width=True)

            st.divider()
            st.subheader("📜 Detailed Logs")
            st.dataframe(df_log.sort_values(by="Timestamp", ascending=False), use_container_width=True)
            st.download_button("📥 Export CSV", df_log.to_csv(index=False), "vault_pilot_data.csv")
        else:
            st.info("No data yet. Complete a story to see insights.")

else:
    st.error("CMS not found. Check your Streamlit Secrets and Google Sheet link.")




