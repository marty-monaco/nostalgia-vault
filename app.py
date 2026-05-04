import streamlit as st
from utils.ingestor import UniversalIngestor
import os

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Curriculum Ingest | The Vault", page_icon="📥", layout="wide")

st.markdown("""
    <style>
    .ingest-container { background-color: #1f2937; padding: 20px; border-radius: 15px; border: 1px solid #4b4b4b; }
    h1 { color: #FFD700; }
    </style>
""", unsafe_allow_html=True)

# --- 2. HEADER ---
st.title("📥 CURRICULUM INGEST")
st.write("Step 1: Transform raw curriculum into a normalized knowledge base.")

# --- 3. INPUT SELECTION ---
st.divider()
col_left, col_right = st.columns([1, 2])

with col_left:
    st.write("### 🏗️ Source Type")
    source_type = st.radio(
        "What are we vaultifying today?",
        ["URL (Web Content)", "PDF Document", "Word (.docx)"],
        index=0
    )

with col_right:
    st.write("### 📂 Input Material")
    if source_type == "URL (Web Content)":
        source_input = st.text_input("Paste URL here:", placeholder="https://en.wikipedia.org/wiki/RICO_Act")
        file_upload = None
    else:
        file_upload = st.file_uploader(f"Choose a {source_type} file", type=["pdf", "docx"])
        source_input = "file_upload"

# --- 4. PROCESSING LOGIC ---
st.divider()

if st.button("PROCESS & NORMALIZE CONTENT ⚡", use_container_width=True):
    if (source_type == "URL (Web Content)" and not source_input) or (source_type != "URL (Web Content)" and not file_upload):
        st.error("Please provide a valid source before processing.")
    else:
        with st.spinner("Extracting, cleaning, and normalizing text..."):
            # Initialize our custom utility
            # If it's a URL, we pass the URL string; if it's a file, we pass the filename
            path_or_url = source_input if source_type == "URL (Web Content)" else file_upload.name
            ingestor = UniversalIngestor(path_or_url)
            
            # Execute Ingestion
            # Note: file_upload is passed for buffer reading in PDFs/Docx
            payload = ingestor.get_ingest_payload(file_upload)
            
            if "Error" in payload["raw_text"]:
                st.error(payload["raw_text"])
            else:
                # Store in Session State for the Orchestrator Page (Step 2)
                st.session_state["raw_curriculum"] = payload["raw_text"]
                st.session_state["ingest_metadata"] = payload["metadata"]
                
                # UI Feedback
                st.success(f"Successfully ingested {len(payload['raw_text'])} characters!")
                
                # Show Stats
                c1, c2, c3 = st.columns(3)
                c1.metric("Format", payload["metadata"]["type"])
                c2.metric("Approx. Vault Stories", max(1, len(payload["raw_text"]) // 2500))
                c3.metric("Data Status", "Ready for AI")

                # Content Preview
                with st.expander("👀 Review Normalized Text"):
                    st.markdown("---")
                    st.write(payload["raw_text"])
                    st.markdown("---")

# --- 5. FOOTER NAVIGATION ---
if "raw_curriculum" in st.session_state:
    st.divider()
    st.info("💡 **Next Step:** Navigate to the **🧠 Orchestrate** page in the sidebar to generate your Director JSON and Script.")
