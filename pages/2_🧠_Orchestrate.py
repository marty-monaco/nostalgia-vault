"""
The Vault — Page 2: Narrative Orchestrator
Transforms ingested curriculum payloads into 3 distinct narrative metaphor
pitches using Gemini, auditions story blueprints, and routes selected concepts
to the Production Engine (Page 3).
"""

import os
import re
import streamlit as st
import google.generativeai as genai

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
# GEMINI API CLIENT SETUP
# -----------------------------------------------------------------------------
API_KEY = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None)

if API_KEY:
    genai.configure(api_key=API_KEY)


# -----------------------------------------------------------------------------
# PARSING & FORMATTING HELPERS
# -----------------------------------------------------------------------------
def parse_orchestrated_pitches(text: str) -> list[dict]:
    """
    Parses LLM output into individual pitch dictionaries containing title and body.
    Supports markdown headers, 'PITCH 1:', 'CONCEPT 1:', or numbered formats.
    """
    # Split on Pitch/Concept markers
    pattern = re.compile(
        r"(?:^|\n)(?:###?\s*(?:PITCH|CONCEPT)\s*\d*:?|(?:PITCH|CONCEPT)\s*\d*:?)\s*",
        re.IGNORECASE,
    )
    splits = pattern.split(text.strip())

    pitches = []
    # If regex found distinct blocks
    if len(splits) > 1:
        for idx, block in enumerate(splits[1:], start=1):
            block = block.strip()
            if not block:
                continue
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            title = lines[0].replace("**", "").replace("#", "").strip() if lines else f"Story Blueprint {idx}"
            pitches.append({
                "title": title,
                "metaphor": block,
            })

    # Fallback: Split by double newlines if no explicit headers matched
    if not pitches:
        fallback_blocks = [b.strip() for b in text.split("\n\n") if len(b.strip()) > 60]
        for idx, block in enumerate(fallback_blocks[:3], start=1):
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            title = lines[0][:40] if lines else f"Story Blueprint {idx}"
            pitches.append({
                "title": title,
                "metaphor": block,
            })

    # Final fallback if parsing produced nothing
    if not pitches:
        pitches.append({
            "title": "Selected Narrative Blueprint",
            "metaphor": text.strip(),
        })

    return pitches


def _render_pitch_cards(pitches: list, topic_title: str) -> None:
    """
    Renders interactive pitch audition cards with clean enumerate scoping to
    prevent NameError on button clicks, and syncs session state with Page 3.
    """
    st.markdown("### 🎭 Audition Narrative Pitches")
    st.caption("Select a metaphor blueprint below to route it directly into the 90-second Production Engine.")

    for pitch_idx, pitch in enumerate(pitches):
        if isinstance(pitch, dict):
            pitch_title = pitch.get("title", f"Pitch Concept {pitch_idx + 1}")
            pitch_body = pitch.get("metaphor", pitch.get("content", str(pitch)))
        else:
            pitch_title = f"Pitch Concept {pitch_idx + 1}"
            pitch_body = str(pitch)

        with st.expander(f"📌 Pitch {pitch_idx + 1}: {pitch_title}", expanded=(pitch_idx == 0)):
            st.markdown(pitch_body)

            # Properly scoped pitch_idx in widget key
            btn_key = f"select_pitch_btn_{pitch_idx}"
            if st.button("🎬 Send to Production Engine", key=btn_key, type="primary"):
                # 1. Sync standardized session keys for 3_Produce.py
                st.session_state["selected_metaphor_pitch"] = pitch_body
                st.session_state["active_topic"] = topic_title or pitch_title
                st.session_state["selected_pitch"] = pitch_body

                # 2. Invalidate stale cached production outputs
                st.session_state.pop("prod_script", None)
                st.session_state.pop("prod_mcqs", None)
                st.session_state.pop("raw_production_output", None)
                st.session_state.pop("last_generated_metaphor", None)

                st.success(f"✅ '{pitch_title}' locked in! Open **3_🎬_Produce** in the sidebar to generate the script.")


# -----------------------------------------------------------------------------
# MAIN APP INTERFACE
# -----------------------------------------------------------------------------
def main():
    st.title("🧠 NARRATIVE ORCHESTRATOR")
    st.caption("Translate Academic & Economic Models into Universal Story Metaphors")

    # Ingestion context retrieval
    raw_payload = (
        st.session_state.get("active_curriculum_payload")
        or st.session_state.get("curriculum_payload")
        or ""
    )

    with st.sidebar:
        st.header("⚙️ Orchestrator Controls")
        cohort_id = st.text_input("Cohort / Pilot ID", value="WIRAPIDS_12")
        target_topic = st.text_input("Curriculum Topic", value="Incentives vs. Goals: Price Controls")
        student_age = st.selectbox(
            "Target Demographic",
            ["High School Seniors (12th Grade)", "Introductory College", "Adult Continuing Ed"],
            index=0,
        )
        model_name = st.selectbox("Gemini Engine", ["gemini-2.5-flash", "gemini-2.5-pro"], index=0)

        st.divider()
        if st.button("🧹 Reset Orchestrator State", use_container_width=True):
            st.session_state.pop("orchestrated_pitches_raw", None)
            st.session_state.pop("parsed_pitches", None)
            st.session_state.pop("selected_metaphor_pitch", None)
            st.rerun()

    # Ingested Payload Review
    with st.expander("📑 View Ingested Curriculum Payload", expanded=not bool(raw_payload)):
        curriculum_input = st.text_area(
            "Source Curriculum Text:",
            value=raw_payload,
            height=180,
            placeholder="Paste raw curriculum text or ingest via Page 1 (1_Ingest.py)...",
        )
        # Allow updating session state from here if entered manually
        if curriculum_input != raw_payload:
            st.session_state["active_curriculum_payload"] = curriculum_input
            raw_payload = curriculum_input

    # Orchestration Generation
    if st.button("✨ Brainstorm Story Metaphors", type="primary", use_container_width=True):
        if not API_KEY:
            st.error("❌ Gemini API Key not detected. Please configure GEMINI_API_KEY in your secrets.")
            return

        if not raw_payload.strip():
            st.warning("⚠️ Please provide source curriculum text above or ingest via Page 1.")
            return

        prompt = f"""
You are the Executive Narrative Architect for 'The Vault', an educational platform delivering 90-second micro-documentaries.

CURRICULUM TOPIC: {target_topic}
TARGET COHORT: {cohort_id} ({student_age})
SOURCE CURRICULUM:
{raw_payload[:3000]}

Your task is to invent THREE distinct, compelling story metaphor pitches designed to explain these concepts to 12th graders.
Avoid dry textbook language. Root each pitch in an authentic, high-stakes real-world arena (e.g., sneaker reselling drops, battlefield medical triage, viral creator algorithms, post-war housing shortages, or underground arcade economies).

Format your output EXACTLY as follows:

PITCH 1: [Punchy Title]
- Premise: [1-2 sentences setting the narrative stage and characters]
- Metaphor Alignment: [How the real-world mechanic precisely maps to the economic principle]
- The Climax / Decision Point: [The tension or trade-off faced by the protagonist]
- Pedagogical Takeaway: [The enduring rule the student takes away]

PITCH 2: [Punchy Title]
- Premise: [1-2 sentences setting the narrative stage and characters]
- Metaphor Alignment: [How the real-world mechanic precisely maps to the economic principle]
- The Climax / Decision Point: [The tension or trade-off faced by the protagonist]
- Pedagogical Takeaway: [The enduring rule the student takes away]

PITCH 3: [Punchy Title]
- Premise: [1-2 sentences setting the narrative stage and characters]
- Metaphor Alignment: [How the real-world mechanic precisely maps to the economic principle]
- The Climax / Decision Point: [The tension or trade-off faced by the protagonist]
- Pedagogical Takeaway: [The enduring rule the student takes away]
"""
        with st.spinner("Orchestrating 3 narrative metaphor blueprints..."):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                raw_text = response.text

                st.session_state["orchestrated_pitches_raw"] = raw_text
                st.session_state["parsed_pitches"] = parse_orchestrated_pitches(raw_text)

            except Exception as e:
                st.error(f"❌ Orchestration Error: {e}")

    # Render Pitches
    if "parsed_pitches" in st.session_state and st.session_state["parsed_pitches"]:
        st.divider()
        _render_pitch_cards(st.session_state["parsed_pitches"], target_topic)


if __name__ == "__main__":
    main()
