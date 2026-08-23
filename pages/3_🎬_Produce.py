"""
Page 3 — Production Engine
Takes the active story blueprint from Session State, allows academic level
targeting, and generates the 8-second hooked script and assessment package.
"""
import streamlit as st
from utils.production import ProductionEngine, resolve_api_key
from utils.constants import KEY_ORCHESTRATOR_REPORT, KEY_PRODUCTION_PAYLOAD

ACADEMIC_LEVELS = [
    "High School Standard",
    "High School AP / Honors",
    "Undergraduate / University Level",
    "Advanced Research / Graduate",
]

st.set_page_config(page_title="The Vault - Produce", page_icon="🎬", layout="wide")


def _render_production_output(payload: str) -> None:
    """Render the production payload in structured collapsible sections."""
    st.divider()
    st.markdown("### 📄 Production Payload Output")

    # Split into the two known sections for structured rendering
    if "### SECTION 2" in payload:
        script_part, quiz_part = payload.split("### SECTION 2", 1)
        with st.expander("🎬 SECTION 1 — Video Script", expanded=True):
            st.markdown(script_part.replace("### SECTION 1", "").strip())
        with st.expander("📝 SECTION 2 — Assessment Package", expanded=True):
            st.markdown("### SECTION 2" + quiz_part)
    else:
        st.markdown(payload)

    # Copyable raw output for export
    with st.expander("📋 Raw Output (copy for export)", expanded=False):
        st.text_area("Full payload:", payload, height=400, disabled=True)


def main() -> None:
    st.title("🎬 THE PRODUCTION ENGINE")
    st.subheader("Script Synthesis & Calibrated Assessment Package")

    active_blueprint = st.session_state.get(KEY_ORCHESTRATOR_REPORT)
    if not active_blueprint:
        st.warning(
            "⚠️ No story concept selected. Please visit the 🧠 Narrative Orchestrator "
            "page and select 'Produce Story' on a pitch card."
        )
        return

    st.success("✅ Active Story Blueprint detected from Orchestrator.")
    st.divider()

    with st.expander("📖 Active Story Blueprint (click to expand)", expanded=True):
        st.markdown(active_blueprint)

    st.divider()

    # Academic rigor selector
    st.markdown("### 🎓 Target Academic Rigor Level")
    academic_level = st.selectbox(
        "Select the target cognitive complexity for the generated assessment questions:",
        options=ACADEMIC_LEVELS,
        index=2,  # Defaults to Undergraduate
        help="Adjusts cognitive depth (Bloom's Taxonomy) of pre and post-video questions.",
    )
    st.divider()

    # API key
    api_key = resolve_api_key(st.secrets)
    if not api_key:
        api_key = st.text_input("Enter Gemini API Key manually:", type="password")

    # Re-generation guard
    existing_payload = st.session_state.get(KEY_PRODUCTION_PAYLOAD)
    if existing_payload:
        st.info("💡 A production payload already exists. Re-running will replace it.")

    button_label = "🔄 Re-generate Script & Quizzes" if existing_payload else "🚀 Generate Production Script & Quizzes"

    if st.button(button_label, type="primary", use_container_width=True, disabled=not api_key):
        with st.spinner(f"Synthesizing 8-second hook and {academic_level}-level assessment…"):
            try:
                engine = ProductionEngine(api_key=api_key)
                payload = engine.generate_blueprint(
                    creative_report=active_blueprint,
                    academic_level=academic_level,
                )
                st.session_state[KEY_PRODUCTION_PAYLOAD] = payload
                st.toast("Production Payload Generated Successfully! 🎉")
            except ValueError as e:
                st.error(f"❌ Input Error: {e}")
            except RuntimeError as e:
                st.error(f"❌ Production Engine Error: {e}")
            except Exception as e:
                st.error(f"❌ Unexpected Error: {e}")

    production_payload = st.session_state.get(KEY_PRODUCTION_PAYLOAD)
    if production_payload:
        _render_production_output(production_payload)


if __name__ == "__main__":
    main()
