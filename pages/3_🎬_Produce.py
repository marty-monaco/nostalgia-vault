"""
Page 3 — Production Engine
Takes an active story blueprint from Session State, allows academic level targeting,
and generates the finalized 8-second hooked script and calibrated assessment package.
"""
import streamlit as st
from utils.production import ProductionEngine, resolve_api_key

# ---------------------------------------------------------------------------
# CONSTANTS & CONFIG
# ---------------------------------------------------------------------------
KEY_ORCHESTRATOR_REPORT = "orchestrator_report"
KEY_PRODUCTION_PAYLOAD  = "production_payload"

st.set_page_config(page_title="The Vault - Produce", page_icon="🎬", layout="wide")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    st.title("🎬 THE PRODUCTION ENGINE")
    st.subheader("Script Synthesis & Calibrated Assessment Package")

    # 1. Verify an active concept blueprint exists in session state
    active_blueprint = st.session_state.get(KEY_ORCHESTRATOR_REPORT)
    if not active_blueprint:
        st.warning(
            "⚠️ No story concept selected. Please visit the 🧠 Narrative Orchestrator "
            "page first and select 'Produce Story' on a pitch card."
        )
        return

    st.success("✅ Active Story Blueprint detected from Orchestrator session state.")
    st.divider()

    # 2. Render Active Blueprint Preview Card
    with st.expander("📖 Active Story Blueprint (Click to expand)", expanded=True):
        st.markdown(active_blueprint)

    st.divider()

    # 3. Render Academic Rigor Control Selector
    st.markdown("### 🎓 Target Academic Rigor Level")
    academic_level = st.selectbox(
        "Select the target cognitive complexity for the generated assessment questions:",
        options=[
            "High School Standard",
            "High School AP / Honors",
            "Undergraduate / University Level",
            "Advanced Research / Graduate"
        ],
        index=2,  # Defaults to Undergraduate for high-rigor testing
        help="Adjusts the cognitive depth (Bloom's Taxonomy) of the pre and post-video questions."
    )

    st.divider()

    # 4. Resolve API Key & Run Trigger
    api_key = resolve_api_key()
    if not api_key:
        api_key = st.text_input("Enter Gemini API Key manually:", type="password")

    if st.button("🚀 Generate Production Script & Quizzes", type="primary", use_container_width=True, disabled=not api_key):
        with st.spinner(f"Synthesizing 8-second hook and {academic_level}-level assessment package…"):
            try:
                engine = ProductionEngine(api_key=api_key)
                payload = engine.generate_blueprint(
                    creative_report=active_blueprint,
                    academic_level=academic_level
                )
                st.session_state[KEY_PRODUCTION_PAYLOAD] = payload
                st.toast("Production Payload Generated Successfully! 🎉")
            except Exception as e:
                st.error(f"❌ Production Engine Error: {e}")

    # 5. Display Production Output if cached
    production_payload = st.session_state.get(KEY_PRODUCTION_PAYLOAD)
    if production_payload:
        st.divider()
        st.markdown("### 📄 Production Payload Output")
        st.markdown(production_payload)


if __name__ == "__main__":
    main()
