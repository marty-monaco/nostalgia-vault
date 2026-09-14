"""
Page 1 — Curriculum Ingestor
Supports smart auto-crawl (Methods 1 & 2), manual batch URL ingestion,
raw text normalization, and PDF textbook extraction into Session State.
"""
import streamlit as st
import pypdf
from utils.ingestion import CurriculumIngestor, IngestionError
from utils.constants import KEY_CURRICULUM_PAYLOAD

MIN_PAYLOAD_CHARS = 500
MAX_PDF_FILE_MB   = 25

st.set_page_config(page_title="The Vault - Ingest", page_icon="📥", layout="wide")


def _render_payload_preview(payload: str) -> None:
    st.divider()
    st.markdown("### 📄 Active Curriculum Payload in Memory")

    col1, col2 = st.columns(2)
    col1.metric("Characters", f"{len(payload):,}")
    col2.metric("Words (approx)", f"{len(payload.split()):,}")

    if len(payload) < MIN_PAYLOAD_CHARS:
        st.warning(
            f"⚠️ Payload is very short ({len(payload):,} chars). "
            "Metaphor generation may produce weak results — consider adding more content."
        )

    with st.expander("Preview Normalized Payload (click to expand)", expanded=False):
        st.text_area("Cached Payload:", payload, height=250, disabled=True)
        st.markdown("👉 **Next Step:** Head to the **🧠 Narrative Orchestrator** to audition story concepts.")


def _extract_pdf_text(uploaded_file, start_page: int, end_page: int) -> str:
    """Extract and combine text from a range of pages in an uploaded PDF."""
    reader = pypdf.PdfReader(uploaded_file)
    total_pages = len(reader.pages)

    start_idx = max(0, start_page - 1)
    end_idx = min(total_pages, end_page)

    extracted_parts = []
    for idx in range(start_idx, end_idx):
        page = reader.pages[idx]
        text = page.extract_text()
        if text and text.strip():
            extracted_parts.append(f"--- [Page {idx + 1}] ---\n{text.strip()}")

    return "\n\n".join(extracted_parts)


def main() -> None:
    st.title("📥 CURRICULUM INGESTOR")
    st.subheader("Aggregate & Normalize Multi-Page Textbook Chapters & PDFs")

    ingestor = CurriculumIngestor()

    tab_smart, tab_batch, tab_text, tab_pdf = st.tabs([
        "🤖 Smart Crawl (Auto-Discover)",
        "🌐 Manual Batch URLs",
        "📝 Raw Text Input",
        "📑 PDF Textbook Chapter",
    ])

    # Smart Crawl
    with tab_smart:
        st.markdown("### Smart Chapter Crawler")
        seed_url = st.text_input(
            "Paste any URL from the chapter:",
            placeholder="https://openstax.org/books/principles-microeconomics-3e/pages/18-1-voter-participation",
        )

        if st.button("🤖 Auto-Discover & Fetch Chapter", type="primary", key="btn_smart"):
            if not seed_url.strip():
                st.warning("⚠️ Please enter a URL.")
            else:
                with st.spinner("Scanning for related chapter sections…"):
                    try:
                        payload, discovered_urls = ingestor.smart_crawl(seed_url.strip())
                        st.session_state[KEY_CURRICULUM_PAYLOAD] = payload
                        st.success(f"🎉 Smart crawl complete — {len(discovered_urls)} section(s) fetched!")
                    except IngestionError as e:
                        st.error(f"❌ Smart Crawl Error: {e}")
                    except Exception as e:
                        st.error(f"❌ Unexpected Error: {e}")

    # Manual Batch
    with tab_batch:
        st.markdown("### Manual Batch URL Ingestion")
        urls_input = st.text_area(
            "URLs (one per line):",
            height=150,
            placeholder="https://openstax.org/...\nhttps://openstax.org/...",
        )
        if st.button("🚀 Fetch & Normalize Batch", type="primary", key="btn_batch"):
            valid_urls = [u.strip() for u in urls_input.splitlines() if u.strip()]
            if not valid_urls:
                st.warning("⚠️ Please enter at least one valid URL.")
            else:
                with st.spinner(f"Fetching {len(valid_urls)} page(s)…"):
                    try:
                        payload = ingestor.fetch_batch_urls(valid_urls)
                        st.session_state[KEY_CURRICULUM_PAYLOAD] = payload
                        st.success(f"🎉 {len(valid_urls)} page(s) fetched and aggregated!")
                    except IngestionError as e:
                        st.error(f"❌ Ingestion Error: {e}")

    # Raw Text
    with tab_text:
        st.markdown("### Direct Text Ingestion")
        raw_text_input = st.text_area("Paste Curriculum Text:", height=250)
        if st.button("⚙️ Process & Normalize Text", type="primary", key="btn_raw"):
            if not raw_text_input.strip():
                st.warning("⚠️ Please paste text into the box above.")
            else:
                try:
                    payload = ingestor.normalize_text(raw_text_input)
                    st.session_state[KEY_CURRICULUM_PAYLOAD] = payload
                    st.success("🎉 Text normalized and cached!")
                except IngestionError as e:
                    st.error(f"❌ Normalization Error: {e}")

    # PDF Ingestion with file size guard
    with tab_pdf:
        st.markdown("### PDF Textbook Ingestion")
        pdf_file = st.file_uploader("Choose a PDF file", type=["pdf"], key="pdf_uploader")

        if pdf_file is not None:
            file_size_mb = pdf_file.size / (1024 * 1024)
            if file_size_mb > MAX_PDF_FILE_MB:
                st.error(f"File exceeds maximum allowed size of {MAX_PDF_FILE_MB}MB.")
            else:
                try:
                    temp_reader = pypdf.PdfReader(pdf_file)
                    total_pages = len(temp_reader.pages)
                    st.info(f"📑 PDF loaded: **{pdf_file.name}** ({total_pages} pages)")

                    col_start, col_end = st.columns(2)
                    with col_start:
                        start_page = st.number_input("Start Page:", min_value=1, max_value=total_pages, value=1)
                    with col_end:
                        end_page = st.number_input("End Page:", min_value=1, max_value=total_pages, value=min(20, total_pages))

                    if st.button("📑 Extract & Normalize PDF Chapter", type="primary", key="btn_pdf"):
                        if start_page > end_page:
                            st.error("Start page cannot be greater than end page.")
                        else:
                            with st.spinner("Extracting pages…"):
                                raw_pdf = _extract_pdf_text(pdf_file, int(start_page), int(end_page))
                                if not raw_pdf.strip():
                                    st.warning("⚠️ No readable text found in those pages.")
                                else:
                                    payload = ingestor.normalize_text(raw_pdf)
                                    st.session_state[KEY_CURRICULUM_PAYLOAD] = payload
                                    st.success(f"🎉 Extracted {end_page - start_page + 1} page(s) and normalized!")
                except Exception as e:
                    st.error(f"Failed to read PDF file: {e}")

    # Payload Preview
    cached = st.session_state.get(KEY_CURRICULUM_PAYLOAD)
    if cached:
        _render_payload_preview(cached)


if __name__ == "__main__":
    main()
