"""
Page 1 — Curriculum Ingestor
Supports multi-URL batch ingestion and raw text normalization into Session State.
"""
import streamlit as st
from utils.ingestion import CurriculumIngestor

KEY_CURRICULUM_PAYLOAD = "curriculum_payload"

st.set_page_config(page_title="The Vault - Ingest", page_icon="📥", layout="wide")

def main() -> None:
    st.title("📥 CURRICULUM INGESTOR")
    st.subheader("Aggregate & Normalize Multi-Page Textbook Chapters")

    ingestor = CurriculumIngestor()

    tab_url, tab_text = st.tabs(["🌐 Batch URL Ingestion (OpenStax / Web)", "📝 Raw Text Input"])

    # ---------------------------------------------------------------------------
    # TAB 1: BATCH URL INGESTION
    # ---------------------------------------------------------------------------
    with tab_url:
        st.markdown("### Paste Chapter URLs")
        st.caption("Enter one URL per line to aggregate multiple sub-sections into a single master payload.")
        
        urls_input = st.text_area(
            "URLs (One per line):",
            height=150,
            placeholder=(
                "https://openstax.org/books/principles-microeconomics-3e/pages/18-1-voter-participation-and-costs-of-elections\n"
                "https://openstax.org/books/principles-microeconomics-3e/pages/18-2-special-interest-politics\n"
                "https://openstax.org/books/principles-microeconomics-3e/pages/18-3-flaws-in-the-democratic-system-of-government"
            )
        )

        if st.button("🚀 Fetch & Normalize Batch Chapter", type="primary", key="btn_batch_url"):
            url_list = urls_input.split("\n")
            if not any(u.strip() for u in url_list):
                st.warning("⚠️ Please enter at least one valid URL.")
            else:
                with st.spinner(f"Fetching and aggregating {len([u for u in url_list if u.strip()])} chapter page(s)…"):
                    try:
                        payload = ingestor.fetch_batch_urls(url_list)
                        st.session_state[KEY_CURRICULUM_PAYLOAD] = payload
                        st.success("🎉 Multi-URL Chapter aggregate successfully cached in session state!")
                    except Exception as e:
                        st.error(f"❌ Batch Ingestion Error: {e}")

    # ---------------------------------------------------------------------------
    # TAB 2: RAW TEXT INPUT
    # ---------------------------------------------------------------------------
    with tab_text:
        st.markdown("### Direct Text Ingestion")
        raw_text_input = st.text_area(
            "Paste Curriculum Text:",
            height=250,
            placeholder="Paste syllabus notes, textbook content, or topic outlines here…"
        )

        if st.button("⚙️ Process & Normalize Raw Text", type="primary", key="btn_raw_text"):
            if not raw_text_input.strip():
                st.warning("⚠️ Please paste text into the box above.")
            else:
                with st.spinner("Normalizing curriculum text…"):
                    try:
                        payload = ingestor.normalize_text(raw_text_input)
                        st.session_state[KEY_CURRICULUM_PAYLOAD] = payload
                        st.success("🎉 Raw text successfully normalized and cached in session state!")
                    except Exception as e:
                        st.error(f"❌ Text Normalization Error: {e}")

    # ---------------------------------------------------------------------------
    # DISPLAY ACTIVE PAYLOAD PREVIEW
    # ---------------------------------------------------------------------------
    cached_payload = st.session_state.get(KEY_CURRICULUM_PAYLOAD)
    if cached_payload:
        st.divider()
        st.markdown("### 📄 Active Curriculum Payload in Memory")
        st.info(f"Total Character Count: {len(cached_payload):,} chars")
        with st.expander("Preview Normalized Payload (Click to expand)", expanded=False):
            st.text_area("Cached Payload Output:", cached_payload, height=250, disabled=True)
            st.markdown("👉 **Next Step:** Head over to the **🧠 Narrative Orchestrator** page to audition story concepts!")

if __name__ == "__main__":
    main()
