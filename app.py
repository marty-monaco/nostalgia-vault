import streamlit as st
from streamlit_gsheets import GSheetsConnection

# This line now looks into that "Secrets" box you just filled out!
conn = st.connection("gsheets", type=GSheetsConnection)
df_cms = conn.read(ttl="10m")

# --- 1. APP CONFIG ---
st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="centered")

# --- 2. CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { background-color: #ff00ff; color: white; border-radius: 8px; font-weight: bold; }
    .privacy-box { border: 1px solid #ff00ff; padding: 15px; border-radius: 8px; font-size: 0.85em; margin-bottom: 20px; background-color: #1a1c24; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR ---
st.sidebar.title("⚡ The Vault")
# Added "Human Services (Pilot)" to the selection
topic = st.sidebar.selectbox("Select a Vault Story", 
    ["Human Services (Ch. 8)", "DNA Fingerprinting", "The Titanic", "The Space Shuttle Columbia"])

# --- 4. SESSION STATE & TOPIC MONITOR ---
if 'step' not in st.session_state:
    st.session_state.step = "pre_test"
if 'current_topic' not in st.session_state:
    st.session_state.current_topic = topic

if st.session_state.current_topic != topic:
    st.session_state.current_topic = topic
    st.session_state.step = "pre_test"
    st.rerun()

# --- 5. STEP 1: PRE-TEST & IDENTIFICATION ---
if st.session_state.step == "pre_test":
    st.title(f"🔍 Pre-Assessment: {topic}")
    
    if topic == "Human Services (Ch. 8)":
        pre_q1 = st.radio("What is the term for a client's right to make their own life choices?", ["Informed Consent", "Self-Determination", "Mandated Choice"], index=None)
        pre_q2 = st.radio("What is it called when a professional has a secondary relationship (like friend or neighbor) with a client?", ["Dual Relationship", "Case Management", "Empathy Gap"], index=None)
    
    elif topic == "DNA Fingerprinting":
        pre_q1 = st.radio("What year was DNA fingerprinting first used in a forensic case?", ["1974", "1986", "1992"], index=None)
        pre_q2 = st.radio("DNA is found in which part of the cell?", ["Ribosomes", "Nucleus", "Wall"], index=None)
    
    # ... (Add your other topics here as needed) ...

    st.divider()
    st.markdown('<div class="privacy-box"><b>Privacy Notice:</b> Please use initials or a nickname only.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        class_code = st.text_input("Class Code", placeholder="e.g. IVY-HS-101")
    with col2:
        student_id = st.text_input("Initials/Nickname", placeholder="e.g. MM")

    if st.button("ENTER THE VAULT ⚡"):
        if not class_code or not student_id or pre_q1 is None:
            st.error("Please answer the pre-test and provide your info.")
        else:
            st.session_state.class_code = class_code
            st.session_state.student_id = student_id
            st.session_state.pre_q1 = pre_q1
            st.session_state.pre_q2 = pre_q2
            st.session_state.step = "vault_content"
            st.rerun()

# --- 6. STEP 2: VIDEO & PULSE CHECK ---
elif st.session_state.step == "vault_content":
    st.title(f"⚡ {topic}")
    
    if topic == "Human Services (Ch. 8)":
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ") # Replace with Mary's Actual Video URL
        st.write("### 🧠 Ethics Pulse Check")
        q1 = st.radio("When Mary's client refuses a suggested treatment plan, which principle is she upholding by respecting that choice?", ["Dual Relationships", "Self-Determination", "Confidentiality"], index=None)
        q2 = st.radio("If a counselor agrees to buy a car from a current client, they are potentially violating which boundary?", ["Dual Relationships", "Standard of Care", "Privacy Act"], index=None)
    
    elif topic == "DNA Fingerprinting":
        st.video("https://www.youtube.com/watch?v=T_UJBPRYvcg")
        st.write("### 🧠 DNA Pulse Check")
        q1 = st.radio("Who made the discovery that DNA was as unique as a fingerprint?", ["Dr Alec Jeffries", "Dr Henry Lees", "Dr Michael Baden"], index=None)
        q2 = st.radio("True or False: DNA is now widely used for paternity?", ["True", "False"], index=None)

    # --- FINAL SUBMISSION ---
    st.divider()
    nps_score = st.select_slider("How likely are you to recommend this lesson?", options=list(range(0, 11)), value=8)

    if st.button("SUBMIT FINAL RESULTS 🚀"):
        if q1 is None:
            st.error("Please complete the Pulse Check.")
        else:
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
            pd.DataFrame(final_data).to_csv("vault_data.csv", mode='a', header=not os.path.exists("vault_data.csv"), index=False)
            st.success("Mastery Logged! You've successfully cleared the Vault.")
            st.balloons()
            if st.button("Start New Topic"):
                st.session_state.step = "pre_test"
                st.rerun()

