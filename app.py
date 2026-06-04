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
                
        except Exception as e:
            st.error(f"Critical Ingestion Failure: {e}")


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("📥 THE VAULT CONTROL DECK")
    st.subheader("Unified Curriculum Ingestion & Data Normalization Hub")
    st.write("Select your input vector below to parse, normalize, and cache your foundational educational materials.")

    st.divider()

    # Verify global credentials silently to confirm deployment readiness
    if resolve_api_key():
        st.caption("🟢 Core Engine System Validation: API Credentials Configured Securely.")
    else:
        st.caption("🟡 System Warning: No global API key found. Configuration required via Cloud Secrets before orchestration.")

    # Instantiate the clean tab layout
    tab_file, tab_url, tab_text = st.tabs(["📂 Upload Documents", "🌐 Web Link / URL", "✍️ Paste Raw Text"])

    active_payload = None
    active_file_obj = None

    with tab_file:
        file_payload, file_obj = _render_file_tab()
        if file_payload:
            active_payload = file_payload
            active_file_obj = file_obj

    with tab_url:
        url_payload = _render_url_tab()
        if url_payload and not active_payload:  # Prioritize the file tab if both are entered
            active_payload = url_payload

    with tab_text:
        text_payload = _render_text_tab()
        if text_payload and not active_payload:  # Fall back systematically
            active_payload = text_payload

    st.write("")  # Spatial structural buffer
    st.write("")

    # Unified submission trigger
    process_clicked = st.button("📥 Process and Normalize Selection", type="primary", use_container_width=True)

    st.divider()

    if process_clicked:
        if not active_payload:
            st.error("❌ Action Required: Please provide an asset input (upload a file, insert a valid URL, or paste text) before attempting normalization.")
        else:
            _execute_ingestion_pipeline(active_payload, file_object=active_file_obj)


if __name__ == "__main__":
    main()
