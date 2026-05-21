import streamlit as st
from utils.ingestor import UniversalIngestor

st.set_page_config(page_title="The Vault - Ingest Deck", page_icon="📥", layout="wide")

st.title("📥 THE VAULT CONTROL DECK")
st.subheader("Unified Curriculum Ingestion & Data Normalization Hub")
st.write("Select your input vector below to parse, normalize, and cache your foundational educational materials.")

st.divider()

# Create 3 distinct horizontal tabs for clean user interaction
tab_file, tab_url, tab_text = st.tabs(["📂 Upload Documents", "🌐 Web Link / URL", "✍️ Paste Raw Text"])

source_payload = None
file_object = None

# TAB 1: File Uploader Logic
with tab_file:
    st.write("### Import Local Assets")
    uploaded_file = st.file_uploader(
        "Drag and drop your curriculum files here:", 
        type=["pdf", "docx"],
        help="Supports Adobe PDF (.pdf) and Microsoft Word (.docx) formats."
    )
    if uploaded_file:
        file_object = uploaded_file
        source_payload = uploaded_file.name
        st.info(f"📎 File selected: {uploaded_file.name}")

# TAB 2: URL Logic
with tab_url:
    st.write("### Import Web Assets")
    url_input = st.text_input(
        "Paste article or curriculum URL link here:",
        placeholder="e.g., https://en.wikipedia.org/wiki/Compound_interest"
    )
    if url_input.strip():
        source_payload = url_input.strip()

# TAB 3: Raw Text Logic
with tab_text:
    st.write("### Direct Text Ingestion")
    text_input = st.text_area(
        "Paste textbook raw chapters or notes below:",
        placeholder="Type or paste high-density educational literature here...",
        height=250
    )
    if text_input.strip():
        source_payload = text_input.strip()

st.write("") # Quick vertical spacing layout element
st.write("")

# Single consolidated process button wrapped in a safe form layout
process_button = st.button("📥 Process and Normalize Selection", type="primary", use_container_width=True)

st.divider()

if process_button:
    if not source_payload:
        st.error("❌ Action Required: Please provide an asset input (upload a file, insert a valid URL, or paste text) before attempting normalization.")
    else:
        with st.spinner("⚡ Initializing normalization pipeline... Parsing text structures..."):
            try:
                # Instantiate the ingestor class using the active input stream
                ingestor = UniversalIngestor(source_payload)
                payload = ingestor.get_ingest_payload(file_object=file_object)
                
                # Check for backend errors
                if "Error" in payload["raw_text"]:
                    st.error(payload["raw_text"])
                else:
                    # Global cross-page state assignment
                    st.session_state["raw_curriculum"] = payload["raw_text"]
                    st.session_state["ingest_metadata"] = payload["metadata"]
                    
                    st.success(f"🎉 Success! Extracted and normalized {len(payload['raw_text'])} characters into The Vault memory cache.")
                    
                    # Display a beautiful read-only preview block of what the AI stored
                    with st.expander("📋 Review Ingested Core Text Payload", expanded=True):
                        st.text_area("Normalized Content Wrapper:", value=payload["raw_text"], height=300, disabled=True)
                        
            except Exception as e:
                st.error(f"Critical Ingestion Failure: {e}")
