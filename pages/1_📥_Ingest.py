"""
Page 1 — Curriculum Ingestor
Supports multi-URL batch ingestion and raw text normalization into Session State.
"""
import streamlit as st
from utils.ingestion import CurriculumIngestor, IngestionError
from utils.constants import KEY_CURRICULUM_PAYLOAD

MIN_PAYLOAD_CHARS = 500

st.set_page_config(page_title="The Vault - Ingest", page_icon="📥", layout="wide")


def _render_payload_preview(payload: str) -> None:
    """Show character count, quality warning if too short, and expandable preview."""
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
        st.markdown("👉 **Next Step:** Head to the **🧠 Narrative Orchestrator** page to audition story concepts.")


def main() -> None:
    st.title("📥 CURRICULUM INGESTOR")
    st.subheader("Aggregate & Normalize Multi-Page Textbook Chapters")

    ingestor = CurriculumIngestor()
    tab_url, tab_text = st.tabs(["🌐 Batch URL Ingestion (OpenStax / Web)", "📝 Raw Text Input"])

    # -----------------------------------------------------------------------
    # TAB 1: BATCH URL INGESTION
    # -----------------------------------------------------------------------
    with tab_url:
        st.markdown("### Paste Chapter URLs")
        st.caption("Enter one URL per line to aggregate multiple sub-sections into a single master payload.")

        urls_input = st.text_area(
            "URLs (one per line):",
            height=150,
            placeholder=(
                "https://openstax.org/books/principles-microeconomics-3e/pages/18-1-voter-participation\n"
                "https://openstax.org/books/principles-microeconomics-3e/pages/18-2-special-interest-politics\n"
                "https://openstax.org/books/principles-microeconomics-3e/pages/18-3-flaws-in-democratic-system"
            ),
        )

        if st.button("🚀 Fetch & Normalize Batch Chapter", type="primary", key="btn_batch_url"):
            valid_urls = [u.strip() for u in urls_input.splitlines() if u.strip()]
            if not valid_urls:
                st.warning("⚠️ Please enter at least one valid URL.")
            else:
                with st.spinner(f"Fetching and aggregating {len(valid_urls)} chapter page(s)…"):
                    try:
                        payload = ingestor.fetch_batch_urls(valid_urls)
                        st.session_state[KEY_CURRICULUM_PAYLOAD] = payload
                        st.success(f"🎉 {len(valid_urls)} page(s) aggregated and cached successfully!")
                    except IngestionError as e:
                        st.error(f"❌ Ingestion Error: {e}")
                    except Exception as e:
                        st.error(f"❌ Unexpected Error: {e}")

    # -----------------------------------------------------------------------
    # TAB 2: RAW TEXT INPUT
    # -----------------------------------------------------------------------
    with tab_text:
        st.markdown("### Direct Text Ingestion")

        raw_text_input = st.text_area(
            "Paste Curriculum Text:",
            height=250,
            placeholder="Paste syllabus notes, textbook content, or topic outlines here…",
        )

        if st.button("⚙️ Process & Normalize Raw Text", type="primary", key="btn_raw_text"):
            if not raw_text_input.strip():
                st.warning("⚠️ Please paste text into the box above.")
            else:
                with st.spinner("Normalizing curriculum text…"):
                    try:
                        payload = ingestor.normalize_text(raw_text_input)
                        st.session_state[KEY_CURRICULUM_PAYLOAD] = payload
                        st.success("🎉 Text normalized and cached successfully!")
                    except IngestionError as e:
                        st.error(f"❌ Normalization Error: {e}")
                    except Exception as e:
                        st.error(f"❌ Unexpected Error: {e}")

    # -----------------------------------------------------------------------
    # PAYLOAD PREVIEW
    # -----------------------------------------------------------------------
    cached_payload = st.session_state.get(KEY_CURRICULUM_PAYLOAD)
    if cached_payload:
        _render_payload_preview(cached_payload)


if __name__ == "__main__":
    main()
