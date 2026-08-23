"""
Page 2 — Narrative Orchestrator
Pitches 3 distinct story concepts using the Gemini API, with optional domain steering.
"""
import streamlit as st
from utils.orchestrator import UniverseOrchestrator
from utils.production import resolve_api_key
from utils.constants import (
    KEY_CURRICULUM_PAYLOAD,
    KEY_ORCHESTRATOR_PITCHES,
    KEY_ORCHESTRATOR_REPORT,
)

DOMAIN_OPTIONS = [
    "Any / Multi-Domain (Default)",
    "Sports, Athletics & Professional Leagues (NBA / NFL / MLB)",
    "Real-World Logistics & Transport (Airports, Shipping, Supply Chains)",
    "Culinary & Restaurant Dynamics (Kitchen Ops, Recipe Trade-offs)",
    "Performing Arts & Music (Orchestral Conducting, Stage Mgmt)",
    "Architecture & Construction (Load Balancing, City Planning)",
    "History & High-Stakes Diplomacy (Trade Routes, Treaty Games)",
    "Natural Systems & Ecology (Forest Networks, River Dynamics)",
]

st.set_page_config(page_title="The Vault - Orchestrate", page_icon="🧠", layout="wide")


def _render_pitch_cards(pitches: list[str]) -> None:
    st.divider()
    st.markdown("### 🎬 Audition Pitch Cards")
    cols = st.columns(len(pitches))
    for idx, (col, pitch_text) in enumerate(zip(cols, pitches)):
        with col:
            with st.container(border=True):
                st.markdown(pitch_text)
                st.write("")
                if st.button(
                    f"👉 Select & Produce Pitch {idx + 1}",
                    key=f"select_pitch_{idx}",
                    use_container_width=True,
                    type="primary",
                ):
                    st.session_state[KEY_ORCHESTRATOR_REPORT] = pitch_text
                    st.success(
                        f"✅ Pitch {idx + 1} locked as Active Blueprint! "
                        "Navigate to the 🎬 Produce tab."
                    )


def main() -> None:
    st.title("🧠 NARRATIVE ORCHESTRATOR")
    st.subheader("Audition 3 Multi-Domain Narrative Concepts")

    raw_curriculum = st.session_state.get(KEY_CURRICULUM_PAYLOAD)
    if not raw_curriculum:
        st.warning(
            "⚠️ No curriculum payload found. Please visit the 📥 Curriculum Ingestor "
            "page first to process your text or URL."
        )
        return

    st.success("✅ Normalized curriculum detected from Ingestor.")
    st.divider()

    # Domain selector
    st.markdown("### 🎯 Preferred Metaphor Domain Focus")
    preferred_domain = st.selectbox(
        "Select a domain to guarantee at least one tailored concept, "
        "or leave on Default for full automated diversity:",
        options=DOMAIN_OPTIONS,
        index=0,
        help="Guarantees that at least one pitched story strictly uses your chosen theme.",
    )
    st.divider()

    # API key
    api_key = resolve_api_key(st.secrets)
    if not api_key:
        api_key = st.text_input("Enter Gemini API Key manually:", type="password")

    # Re-pitch guard
    existing_pitches = st.session_state.get(KEY_ORCHESTRATOR_PITCHES)
    if existing_pitches:
        st.info("💡 Pitches already generated. Re-running will replace them and clear any active blueprint.")

    if st.button(
        "🎭 Audition 3 Metaphor Concepts",
        type="primary",
        use_container_width=True,
        disabled=not api_key,
    ):
        with st.spinner(f"Pitching story concepts (Domain: {preferred_domain})…"):
            try:
                orchestrator = UniverseOrchestrator(api_key=api_key)
                # audition_metaphors returns list[str] in the refactored orchestrator
                pitches = orchestrator.audition_metaphors(
                    raw_curriculum=raw_curriculum,
                    preferred_domain=preferred_domain,
                )
                st.session_state[KEY_ORCHESTRATOR_PITCHES] = pitches
                # Clear any previously selected blueprint to avoid stale state
                st.session_state.pop(KEY_ORCHESTRATOR_REPORT, None)
                st.toast("Story Pitches Generated Successfully! 🚀")
            except ValueError as e:
                st.error(f"❌ Input Error: {e}")
            except RuntimeError as e:
                st.error(f"❌ Orchestration Error: {e}")
            except Exception as e:
                st.error(f"❌ Unexpected Error: {e}")

    pitches = st.session_state.get(KEY_ORCHESTRATOR_PITCHES, [])
    if pitches:
        _render_pitch_cards(pitches)


if __name__ == "__main__":
    main()
