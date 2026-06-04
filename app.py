"""
app.py

The Vault Control Deck
Consolidated, unified ingestion hub for raw educational materials. 
Handles document drag-and-drops, web links, and raw text clips simultaneously.
"""
import streamlit as st
from utils.ingestor import UniversalIngestor
from utils.production import resolve_api_key

# ---------------------------------------------------------------------------
# CONSTANTS — session state keys shared across pages
# ---------------------------------------------------------------------------
KEY_RAW_CURRICULUM      = "raw_curriculum"
KEY_INGEST_METADATA     = "ingest_metadata"

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(page_title="The Vault - Ingest Deck", page_icon="📥", layout="wide")


# ---------------------------------------------------------------------------
# RENDER TABS LOGIC
# ---------------------------------------------------------------------------

def _render_file_tab() -> tuple[str | None, any]:
    """Render the document drag-and-drop panel. Returns (source_payload, file_object)."""
    st.write("### Import Local Assets")
    uploaded_file = st.file_uploader(
        "Drag and drop your curriculum files here:", 
        type=["pdf", "docx"],
        help="Supports Adobe PDF (.pdf) and Microsoft Word (.docx) formats."
    )
    if uploaded_file:
        st.info(f"📎 File selected: {uploaded_file.name}")
        return uploaded_file.name, uploaded_file
    return None, None


def _render_url_tab() -> str | None:
    """Render the single-line web scraper input field. Returns source_payload."""
    st.write("### Import Web Assets")
    url_input = st.text_input(
        "Paste article or curriculum URL link here:",
        placeholder="e.g., https://en.wikipedia.org/wiki/Compound_interest"
    )
    return url_input.strip() if url_input.strip() else None


def _render_text_tab() -> str | None:
    """Render the large text canvas field. Returns source_payload."""
    st.write("### Direct Text Ingestion")
    text_input = st.text_area(
        "Paste textbook raw chapters or notes below:",
        placeholder="Type or paste high-density educational literature here...",
        height=250
    )
    return text_input.strip() if text_input.strip() else None


# ---------------------------------------------------------------------------
# CORE NORMALIZATION EXECUTION
# ---------------------------------------------------------------------------

def _execute_ingestion_pipeline(source_payload: str, file_object: any = None) -> None:
    """Instantiate the parsing utility, clean structural text gaps, and persist to state."""
    with st.spinner("⚡ Initializing normalization pipeline... Parsing text structures..."):
        try:
            ingestor = UniversalIngestor(source_payload)
            payload = ingestor.get_ingest_payload(file_object=file_object)
            
            # Catch backend file processing anomalies
            if "Error" in payload["raw_text"]:
                st.error(payload["raw_text"])
                return
                
            # Safely lock content into the shared memory array
            st.session_state[KEY_RAW_CURRICULUM] = payload["raw_text"]
            st.session_state[KEY_INGEST_METADATA] = payload["metadata"]
            
            st.success(f"🎉 Success! Extracted and normalized {len(payload['raw_text'])} characters into The Vault memory cache.")
            
            # Display a clean, un-editable production layout log view
            with st.expander("📋 Review Ingested Core Text Payload", expanded=True):
                st.text_area("Normalized Content Wrapper:", value=payload["raw_text"], height=300, disabled=True)
                
        except Exception as e
