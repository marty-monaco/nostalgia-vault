"""
Page 2 — Narrative Orchestrator
Pitches 3 distinct story concepts using the Gemini API, with optional domain steering.
"""
import streamlit as st
from utils.orchestrator import UniverseOrchestrator
from utils.production import resolve_api_key

# ---------------------------------------------------------------------------
# CONSTANTS & CONFIG
# ---------------------------------------------------------------------------
KEY_CURRICULUM_PAYLOAD = "curriculum_payload"
KEY_ORCHESTRATOR_PITCHES = "orchestrator_pitches"
KEY_ORCHESTRATOR_REPORT = "orchestrator_report"

st.set_page_config(page_title="The Vault - Orchestrate", page_icon="🧠", layout="wide")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    st.title("🧠 NARRATIVE ORCHESTRATOR")
    st.subheader("Audition 3 Multi-Domain Narrative Concepts")

    # 1. Verify normalized curriculum exists in session state
    raw_curriculum = st.session_state.get(KEY_CURRICULUM_PAYLOAD)
    if not raw_curriculum:
        st.warning(
            "⚠️ No curriculum payload found in memory. Please visit the 📥 Curriculum Ingestor "
            "page first to process your text or URL."
        )
        return

    st.success("✅ Normalized Curriculum detected from Ingestor session state.")
    st.divider()

    # 2. Render Domain Selection Control
    st.markdown("### 🎯 Preferred Metaphor Domain Focus")
    preferred_domain = st.selectbox(
        "Select a specific domain to guarantee at least one tailored concept, or leave on Default for full automated diversity:",
        options=[
            "Any / Multi-Domain (Default)",
            "Sports, Athletics & Professional Leagues (NBA / NFL / MLB)",
            "Real-World Logistics & Transport (Airports, Shipping, Supply Chains)",
            "Culinary & Restaurant Dynamics (Kitchen Ops, Recipe Trade-offs)",
            "Performing Arts & Music (Orchestral Conducting, Stage Mgmt)",
            "Architecture & Construction (Load Balancing, City Planning)",
            "History & High-Stakes Diplomacy (Trade Routes, Treaty Games)",
            "Natural Systems & Ecology (Forest Networks, River Dynamics)"
        ],
        index=0, # Defaults to Any / Multi-Domain
        help="Guarantees that at least one pitched story strictly uses your chosen theme."
    )

    st.divider()

    # 3. Resolve API Key & Run Trigger
    api_key = resolve_api_key()
    if not api_key:
        api_key = st.text_input("Enter Gemini API Key manually:", type="password")

    if st.button("🎭 Audition 3 Metaphor Concepts", type="primary", use_container_width=True, disabled=not api_key):
        with st.spinner(f"Pitching story concepts (Domain Focus: {preferred_domain})…"):
            try:
                orchestrator = UniverseOrchestrator(api_key=api_key)
                pitches_raw = orchestrator.audition_metaphors(
                    raw_curriculum=raw_curriculum,
                    preferred_domain=preferred_domain
                )
                
                # Split pitches by delimiter string
                cards = [c.strip() for c in pitches_raw.split("|||") if c.strip()]
                st.session_state[KEY_ORCHESTRATOR_PITCHES] = cards
                st.toast("Story Pitches Generated Successfully! 🚀")
            except Exception as e:
                st.error(f"❌ Orchestration Error: {e}")

    # 4. Display Pitch Cards if available
    pitches = st.session_state.get(KEY_ORCHESTRATOR_PITCHES, [])
    if pitches:
        st.divider()
        st.markdown("### 🎬 Audition Pitch Cards")
        
        cols = st.columns(len(pitches))
        for idx, (col, pitch_text) in enumerate(zip(cols, pitches)):
            with col:
                st.markdown(pitch_text)
                if st.button(f"👉 Select & Produce Pitch {idx + 1}", key=f"select_pitch_{idx}", use_container_width=True):
                    st.session_state[KEY_ORCHESTRATOR_REPORT] = pitch_text
                    st.success(f"Pitch {idx + 1} locked as Active Blueprint! Navigate to the 🎬 Produce tab.")


if __name__ == "__main__":
    main()
