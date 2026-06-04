"""
pages/3_🎬_Produce.py

Production Engine Interface
Reads the orchestrator report from session state, references the centralized 
ProductionEngine key resolver, and renders the finished script + quiz assets.
"""
import streamlit as st
from utils.production import ProductionEngine, resolve_api_key  # Clean, unified import hook

# ---------------------------------------------------------------------------
# CONSTANTS — single source of truth for session state keys
# ---------------------------------------------------------------------------
KEY_ORCHESTRATOR_REPORT = "orchestrator_report"
KEY_PRODUCTION_PAYLOAD  = "production_payload"
KEY_PRODUCTION_RUNNING  = "production_running"

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(page_title="The Vault - Production", page_icon="🎬", layout="wide")


@st.cache_resource
def _get_engine(api_key: str) -> ProductionEngine:
    """Cache the ProductionEngine instance for the session.

    Avoids re-instantiating (and any associated network handshake) on every
    Streamlit rerun triggered by button clicks or widget interactions.
    """
    return ProductionEngine(api_key=api_key)


def _render_no_blueprint() -> None:
    st.warning(
        "⚠️ No creative blueprint found. "
        "Please run the 🧠 Orchestrator tab first to generate a metaphor report."
    )


def _render_api_key_input(auto_key: str) -> str:
    """Return the resolved API key, showing an input field only if needed."""
    if auto_key:
        st.info("🔒 Secure Production Pipeline: using authenticated Cloud Secrets key.")
        return auto_key

    return st.text_input(
        "Confirm Gemini API Key for Production:",
        type="password",
        help="To bypass this prompt, set GEMINI_API_KEY in your Streamlit Cloud Secrets.",
    )


def _render_blueprint_preview(report: str) -> None:
    with st.expander("📋 Review Foundation Blueprint"):
        st.markdown(report)


def _run_production(engine: ProductionEngine, report: str) -> None:
    """Call the engine, persist output to session state, handle errors cleanly."""
    with st.spinner("🎬 Synthesising dual-column script and calibrating quiz questions…"):
        try:
            output = engine.generate_blueprint(report)
        except ValueError as e:
            st.error(f"❌ Invalid input or API key rejected: {e}")
            return
        except TimeoutError:
            st.error("❌ Request timed out. The Gemini API did not respond in time — please retry.")
            return
        except Exception as e:
            st.error(f"❌ Unexpected production error: {e}")
            return

    if not output:
        st.error("❌ The engine returned an empty response. Check your API quota or prompt.")
        return

    st.session_state[KEY_PRODUCTION_PAYLOAD] = output


def _render_production_output(payload: str) -> None:
    st.markdown("## 🏛️ Finished Production Assets")
    st.markdown(payload)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    st.title("🎬 THE PRODUCTION ENGINE")
    st.subheader("Script Synthesis & Assessment Calibration")

    report = st.session_state.get(KEY_ORCHESTRATOR_REPORT)
    if not report:
        _render_no_blueprint()
        return

    st.success("✅ Creative Director Blueprint successfully carried over.")

    # TWEAK INTEGRATED HERE: Calls the shared central master key routing utility directly
    auto_key = resolve_api_key()
    user_key = _render_api_key_input(auto_key)

    _render_blueprint_preview(report)

    already_generated = KEY_PRODUCTION_PAYLOAD in st.session_state
    button_label = "🔄 Re-generate Script & Quizzes" if already_generated else "🎬 Generate Production Script & Quizzes"

    st.divider()

    # The button will only execute if user_key has value, maintaining validation integrity
    if st.button(button_label, type="primary", use_container_width=True, disabled=not user_key):
        if not user_key:
            st.error("❌ Cannot start production: Gemini API Key is missing.")
        else:
            engine = _get_engine(user_key)
            _run_production(engine, report)

    if already_generated:
        _render_production_output(st.session_state[KEY_PRODUCTION_PAYLOAD])


if __name__ == "__main__":
    main()
