"""
The Vault — Page 2: Narrative Orchestrator
Transforms ingested curriculum payloads into 3 distinct narrative metaphor
pitches using Gemini, auditions story blueprints, and routes selected concepts
to the Production Engine (Page 3).
"""

import os
import sys
import streamlit as st

# Ensure root directory is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.constants import (
    KEY_CURRICULUM_PAYLOAD,
    KEY_ORCHESTRATOR_PITCHES,
)
from utils.orchestrator import (
    UniverseOrchestrator,
    DEFAULT_DOMAIN,
    DIRECT_NARRATIVE_OPTION,
)

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="The Vault - Narrative Orchestrator",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# API KEY RESOLUTION
# -----------------------------------------------------------------------------
def _resolve_gemini_key() -> str | None:
    """Safely retrieves the Gemini API key from st.secrets or os.environ."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"].strip()
    except Exception:
        pass
    val = os.environ.get("GEMINI_API_KEY")
    return val.strip() if val else None


# -----------------------------------------------------------------------------
# PITCH DISPLAY & ROUTING HELPER
# -----------------------------------------------------------------------------
def _render_pitch_cards(pitches: list[str], topic_title: str) -> None:
    """Renders interactive audition cards and routes the selected pitch to Page 3."""
    st.markdown("### 🎭 Audition Narrative Pitches")
    st.caption("Select a metaphor blueprint below to route it directly into the Production Engine.")

    for pitch_idx, pitch_card in enumerate(pitches):
        # Extract title from markdown header (e.g., '### TITLE: [Title]')
        first_line = pitch_card.splitlines()[0] if pitch_card else f"Pitch {pitch_idx + 1}"
        clean_title = (
            first_line.replace("### TITLE:", "")
            .replace("###", "")
            .replace("**", "")
            .strip()
        )
        if not clean_title:
            clean_title = f"Pitch Concept {pitch_idx + 1}"

        with st.expander(f"📌 Pitch {pitch_idx + 1}: {clean_title}", expanded=(pitch_idx == 0)):
            st.markdown(pitch_card)

            btn_key = f"select_pitch_btn_{pitch_idx}"
            if st.button("🎬 Send to Production Engine", key=btn_key, type="primary"):
                # 1. Sync standardized session keys for Page 3 (3_🎬_Produce.py)
                st.session_state["selected_metaphor_pitch"] = pitch_card
                st.session_state["active_topic"] = topic_title or clean_title
                st.session_state["selected_pitch"] = pitch_card

                # 2. Invalidate stale cached production outputs
                st.session_state.pop("validated_module", None)
                st.session_state.pop("prod_script", None)
                st.session_state.pop("prod_mcqs", None)
                st.session_state.pop("raw_production_output", None)
                st.session_state.pop("last_generated_metaphor", None)

                st.success(
                    f"✅ '{clean_title}' locked in! Open **3_🎬_Produce** in the sidebar to generate the script."
                )


# -----------------------------------------------------------------------------
# MAIN APP INTERFACE
# -----------------------------------------------------------------------------
def main():
    st.title("🧠 NARRATIVE ORCHESTRATOR")
    st.caption("Translate Academic & Economic Models into Universal Story Metaphors")

    api_key = _resolve_gemini_key()
    raw_payload = st.session_state.get(KEY_CURRICULUM_PAYLOAD, "")

    # Sidebar Controls
    with st.sidebar:
        st.header("⚙️ Orchestrator Controls")
        cohort_id = st.text_input("Cohort / Pilot ID", value="WIRAPIDS_12")
        target_topic = st.text_input(
            "Curriculum Topic", value="Incentives vs. Goals: Price Controls"
        )
        preferred_domain = st.selectbox(
            "Steer Primary Metaphor Domain",
            [
                DEFAULT_DOMAIN,
                DIRECT_NARRATIVE_OPTION,
                "Gaming & Esports",
                "Social Media & Creator Economy",
                "Sneaker & Streetwear Culture",
                "Pop Culture & Celebrity Economy",
                "History & High-Stakes Moments",
                "Film, TV & Streaming Industry",
                "Fashion & Trend Economics",
                "Sports, Athletics & Pro Leagues",
            ],
            index=0,
        )

        st.divider()
        if st.button("🧹 Reset Orchestrator State", use_container_width=True):
            st.session_state.pop(KEY_ORCHESTRATOR_PITCHES, None)
            st.session_state.pop("selected_metaphor_pitch", None)
            st.session_state.pop("selected_pitch", None)
            st.rerun()

    # Ingested Payload Review
    with st.expander("📑 View Ingested Curriculum Payload", expanded=not bool(raw_payload)):
        curriculum_input = st.text_area(
            "Source Curriculum Text:",
            value=raw_payload,
            height=180,
            placeholder="Paste raw curriculum text or ingest via Page 1 (1_Ingest.py)...",
        )
        if curriculum_input != raw_payload:
            st.session_state[KEY_CURRICULUM_PAYLOAD] = curriculum_input
            raw_payload = curriculum_input

    # Generation Trigger
    if st.button("✨ Brainstorm Story Metaphors", type="primary", use_container_width=True):
        if not api_key:
            st.error("❌ GEMINI_API_KEY not detected in secrets or environment.")
            return

        if not raw_payload.strip():
            st.warning("⚠️ Please provide source curriculum text above or ingest via Page 1.")
            return

        with st.spinner("Orchestrating 3 narrative metaphor blueprints..."):
            try:
                orchestrator = UniverseOrchestrator(api_key=api_key)
                pitches = orchestrator.audition_metaphors(
                    raw_curriculum=raw_payload[:4000],
                    preferred_domain=preferred_domain,
                )
                st.session_state[KEY_ORCHESTRATOR_PITCHES] = pitches
            except Exception as e:
                st.error(f"❌ Orchestration Error: {e}")

    # Render Pitch Cards if present
    cached_pitches = st.session_state.get(KEY_ORCHESTRATOR_PITCHES)
    if cached_pitches:
        st.divider()
        _render_pitch_cards(cached_pitches, target_topic)


if __name__ == "__main__":
    main()
