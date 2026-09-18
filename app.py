"""
The Vault CMS — Main Entry Point
Configures session state defaults, loads application branding, 
and imports normalized utilities.
"""
import streamlit as st

# Update import to match the renamed utils/ingestion.py module and CurriculumIngestor class
from utils.ingestion import CurriculumIngestor

# Page Configuration
st.set_page_config(
    page_title="The Vault CMS",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State Keys
SESSION_KEYS = [
    "curriculum_payload",
    "orchestrator_pitches",
    "orchestrator_report",
    "production_payload"
]

for key in SESSION_KEYS:
    if key not in st.session_state:
        st.session_state[key] = None

# Landing Page UI
st.title("🏛️ THE VAULT CMS")
st.subheader("Educational Story Architecture & Production Pipeline")

st.markdown("""
Welcome to **The Vault CMS**. This platform transforms high-density academic curricula 
into attention-gated 90-second video scripts and calibrated assessment packages.

### 🚀 Workflow Navigation
Use the sidebar on the left to move through the production pipeline:

1. **📥 1_Ingest**: Input single/batch textbook URLs (OpenStax) or raw curriculum text.
2. **🧠 2_Orchestrate**: Audition 3 multi-domain narrative story concepts with custom domain steering.
3. **🎬 3_Produce**: Generate the final 8-second hooked script and academic rigor-targeted quiz package.
""")

st.divider()

# System Status Widget
if st.session_state.get("curriculum_payload"):
    st.success("✅ Active Curriculum Payload loaded in memory.")
else:
    st.info("ℹ️ No active payload detected. Start by visiting the **📥 Ingest** page.")
