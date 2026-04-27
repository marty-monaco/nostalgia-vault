import streamlit as st
import pandas as pd
import os

# --- 1. GLOBAL CONFIG ---
st.set_page_config(
    page_title="The Nostalgia Vault | Enterprise CMS",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. THE VAULT AESTHETIC (Global CSS) ---
st.markdown("""
    <style>
    /* 80s/90s Professional Aesthetics */
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border-left: 5px solid #FFD700; }
    h1, h2, h3 { font-family: 'Courier New', Courier, monospace; color: #FFD700; text-transform: uppercase; letter-spacing: 2px; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #262730; border: 1px solid #4b4b4b; }
    .stButton>button:hover { border-color: #FFD700; color: #FFD700; }
    </style>
""", unsafe_allow_html=True)

# --- 3. DASHBOARD LOGIC ---
def get_pilot_metrics():
    """Reads the existing pilot data to show 'Hard Traction' on the landing page."""
    if os.path.exists("vault_data.csv"):
        df = pd.read_csv("vault_data.csv")
        return {
            "total_mastery": len(df),
            "avg_lift": f"+{df['Lift'].mean():.1f}",
            "nps": f"{df['NPS'].mean():.1f}/10",
            "completion": f"{(len(df[df['Status'] == 'Completed']) / len(df)) * 100:.0f}%"
        }
    return {"total_mastery": 0, "avg_lift": "0", "nps": "N/A", "completion": "0%"}

metrics = get_pilot_metrics()

# --- 4. MAIN UI ---
st.title("🏛️ THE NOSTALGIA VAULT")
st.subheader("Enterprise Content Management System (v2.0)")

st.markdown("""
Welcome to the **Content Factory**. Use the sidebar to navigate between 
Curriculum Ingestion, AI Orchestration, and Pilot Analytics.
---
""")

# --- 5. EXECUTIVE METRICS (The "McCloskey" View) ---
st.write("### 📈 Live Pilot Traction (Ivy Tech: CRIM171)")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Lessons Mastered", metrics["total_mastery"])
with c2:
    st.metric("Avg. Knowledge Lift", metrics["avg_lift"])
with c3:
    st.metric("Pilot NPS", metrics["nps"])
with c4:
    st.metric("Completion Rate", metrics["completion"])

st.divider()

# --- 6. ARCHITECTURE OVERVIEW ---
st.write("### 🏗️ Enterprise Roadmap Status")
col_a, col_b = st.columns([2, 1])

with col_a:
    st.info("**Step 1: Universal Ingestor** ✅ *Operational*")
    st.write("Supports PDF, URL, and HTML/XML parsing. Normalizes raw curriculum into 'Clean Markdown'.")
    
    st.success("**Step 2: AI Orchestrator** 🚧 *In Progress*")
    st.write("Mapping academic concepts to 80s/90s nostalgia anchors and generating Director JSON files.")
    
    st.warning("**Step 3: Automated Production** ⏳ *Planned*")
    st.write("Deterministic rendering of 90-second shorts with integrated TTS and Visual generation.")

with col_b:
    st.write("#### 🛠️ Quick Links")
    if st.button("📥 Launch Ingestor"):
        st.write("Navigate to 'Ingest' in the sidebar.")
    if st.button("📊 View Full Analytics"):
        st.write("Navigate to 'Analytics' in the sidebar.")
    if st.button("📝 Edit Master Schema"):
        st.write("Configuring Director JSON v2.1")

st.divider()
st.caption("The Nostalgia Vault | Built for Scalable Mastery | © 2026")
