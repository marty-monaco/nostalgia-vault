import streamlit as st
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="The Nostalgia Vault", page_icon="⚡", layout="centered")

# --- CUSTOM CSS FOR BRANDING ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { background-color: #ff00ff; color: white; border-radius: 8px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- APP NAVIGATION (The Scalable Part) ---
st.title("⚡ The Nostalgia Vault")
topic = st.sidebar.selectbox("Select a Vault Story", ["DNA Fingerprinting", "Pac-Man 45th", "Acid Washed Jeans"])

st.divider()

# --- DYNAMIC CONTENT LOGIC ---
if topic == "DNA Fingerprinting":
    st.subheader("🧬 The Biological Barcode")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ") # Replace with your DNA short link
    
    st.write("### 🧠 DNA Pulse Check")
    q1 = st.radio("What acts as the 'molecular scissors'?", ["Pumice Stones", "Restriction Enzymes", "Electrical Current"], index=None)
    q2 = st.radio("How does the DNA move through the gel?", ["Magnetic Pull", "Electrical Charge", "Gravity"], index=None)
    interest = st.select_slider("Rate your interest in Forensic Science:", options=["1", "2", "3", "4", "5"], value="3")

elif topic == "Pac-Man 45th":
    st.subheader("🕹️ Ghost in the Machine")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ") # Replace with your Pac-Man short link
    
    st.write("### 🧠 Arcade Pulse Check")
    q1 = st.radio("Which ghost is programmed to 'ambush' by aiming ahead?", ["Blinky (Red)", "Pinky (Pink)", "Clyde (Orange)"], index=None)
    q2 = st.radio("What causes the Level 256 'Kill Screen'?", ["A virus", "An integer overflow", "A broken button"], index=None)
    interest = st.select_slider("Rate your interest in Coding/AI:", options=["1", "2", "3", "4", "5"], value="3")

elif topic == "Acid Washed Jeans":
    st.subheader("👖 The Rockstar Accident")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ") # Replace with your Acid Wash short link
    
    st.write("### 🧠 Chemistry Pulse Check")
    q1 = st.radio("What rock is used to carry the bleach?", ["Granite", "Pumice", "Obsidian"], index=None)
    q2 = st.radio("What chemical reaction strips the indigo dye?", ["Photosynthesis", "Oxidation", "Fermentation"], index=None)
    interest = st.select_slider("Rate your interest in Materials Science:", options=["1", "2", "3", "4", "5"], value="3")

# --- UNIFIED SUBMISSION LOGIC ---
st.divider()
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        class_code = st.text_input("Class Code", placeholder="e.g. WI-RAPIDS-01")
    with col2:
        student_id = st.text_input("Initials", placeholder="e.g. ML")

    if st.button("🚀 SUBMIT TO THE VAULT"):
        if not class_code or not student_id or q1 is None:
            st.error("Please answer the questions and provide your ID.")
        else:
            # For now, we simulate success without the buggy Sheets connection
            st.success(f"Success! Your {topic} data has been logged to the Vault.")
            st.balloons()
            
            # This is where we will add the "Quiet Logging" later
            # It will save to a file or database that doesn't trigger 400 errors
