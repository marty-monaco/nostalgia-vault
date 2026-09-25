"""
The Vault — Page 3: Production Engine & Assessment Exporter
Generates 90-second micro-documentary scripts, timed scene manifests,
calibrated 4-question retrieval assessments, and exports directly to
TheVault_CMS_Core via clean CSV or copyable SQL INSERT statements.
"""

import re
import pandas as pd
import streamlit as st
from google import genai

from utils.config import resolve_gemini_key
from utils.drafts import delete_draft, format_draft_age, load_draft, save_draft
from utils.export_helpers import (
    build_cms_row,
    generate_sql_insert_statement,
    parse_mcq_text,
)
from utils.constants import (
    KEY_ACTIVE_TOPIC,
    KEY_CURRICULUM_PAYLOAD,
    KEY_LAST_GENERATED_METAPHOR,
    KEY_PROD_MCQS,
    KEY_PROD_PILOT,
    KEY_PROD_SCRIPT,
    KEY_PROD_TOPIC,
    KEY_RAW_PRODUCTION_OUTPUT,
    KEY_SELECTED_PITCH,
)

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="The Vault - Production Engine",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# GEMINI API CLIENT SETUP
# -----------------------------------------------------------------------------
API_KEY = resolve_gemini_key()

# -----------------------------------------------------------------------------
# PIPELINE INPUTS (session state -> plain values; nothing runs at import time)
# -----------------------------------------------------------------------------
DEFAULT_TOPIC = "Incentives vs. Goals: The Rent Control Paradox"


def _pitch_to_text(pitch) -> str:
    """
    Convert whatever Orchestrate stored under KEY_SELECTED_PITCH into text.

    Orchestrate stores a StoryPitch object. Interpolating that directly into a
    prompt or widget yields its repr (title='...' hook='...'), not a readable
    pitch, so render the markdown card instead. Plain strings pass through.
    """
    if pitch is None:
        return ""
    if hasattr(pitch, "to_markdown_card"):
        return pitch.to_markdown_card()
    return str(pitch).strip()


def _clear_production_outputs() -> None:
    """Drop every generated artifact so stale output can never be exported."""
    for key in (KEY_PROD_SCRIPT, KEY_PROD_MCQS, KEY_RAW_PRODUCTION_OUTPUT):
        st.session_state.pop(key, None)


def _load_pipeline_inputs() -> tuple[str, str, str]:
    """
    Read the Page 1 / Page 2 handoffs and return (curriculum, pitch_text, topic).

    If the selected pitch differs from the one the current outputs were generated
    from, the outputs are stale and are cleared. Called once at the top of main().
    """
    curriculum = st.session_state.get(KEY_CURRICULUM_PAYLOAD) or ""
    pitch_text = _pitch_to_text(st.session_state.get(KEY_SELECTED_PITCH))
    topic = st.session_state.get(KEY_ACTIVE_TOPIC) or DEFAULT_TOPIC

    if pitch_text and st.session_state.get(KEY_LAST_GENERATED_METAPHOR) != pitch_text:
        _clear_production_outputs()
        st.session_state[KEY_LAST_GENERATED_METAPHOR] = pitch_text

    return curriculum, pitch_text, topic


# -----------------------------------------------------------------------------
# ROBUST SPLITTING & ASSESSMENT PARSING HELPERS
# -----------------------------------------------------------------------------
def split_script_and_mcqs(text: str) -> tuple[str, str]:
    """
    Splits LLM output into Script and Assessment sections without colliding
    with source curriculum headings (like SECTION 4 or SECTION 5).
    """
    markers = [
        r"===+\s*ASSESSMENT",
        r"SECTION\s*2\s*:\s*CALIBRATED",
        r"CALIBRATED\s*ASSESSMENT\s*PACKAGE",
        r"ASSESSMENT\s*PACKAGE\s*:",
        r"2\s*Pre-Video\s*Baseline\s*Questions",
        r"Pre-Video\s*Baseline\s*Questions",
    ]
    pattern = re.compile("|".join(markers), re.IGNORECASE)
    match = pattern.search(text)

    if match:
        split_idx = match.start()
        script_part = text[:split_idx].strip()
        mcq_part = text[split_idx:].strip()
        script_part = re.sub(r"^SECTION\s*1\s*:[^\n]*\n?", "", script_part, flags=re.IGNORECASE).strip()
        return script_part, mcq_part

    return text, text


# -----------------------------------------------------------------------------
# MAIN APP INTERFACE
# -----------------------------------------------------------------------------
def main():
    st.title("🎬 PRODUCTION ENGINE")
    st.caption("Generate 90-Second Micro-Documentary Scripts & Calibrated Assessment Packages")

    curriculum_context, chosen_metaphor, default_topic = _load_pipeline_inputs()

    with st.sidebar:
        st.header("⚙️ Production Controls")
        target_pilot = st.text_input("Cohort / Pilot ID", value="WIRAPIDS_12")
        topic_title = st.text_input("Curriculum Topic Title", value=default_topic)
        target_duration = st.slider("Target Duration (sec)", min_value=60, max_value=120, value=85, step=5)
        grade_level = st.selectbox(
            "Cognitive Rigor Level",
            ["High School Standard (12th Grade)", "AP / Introductory College", "Undergraduate Advanced"],
            index=0,
        )
        model_name = st.selectbox("Gemini Model", ["gemini-2.5-flash", "gemini-2.5-pro"], index=0)

        st.divider()
        if st.button("🧹 Flush Production Memory", use_container_width=True):
            _clear_production_outputs()
            st.session_state.pop(KEY_LAST_GENERATED_METAPHOR, None)
            st.rerun()

    # ---------------------------------------------------------------------
    # RESUME A SAVED DRAFT
    # Only offered when this session has no script yet, so a fresh
    # "Generate" click is never silently overwritten by an old draft.
    # ---------------------------------------------------------------------
    if not st.session_state.get(KEY_PROD_SCRIPT):
        draft = load_draft(target_pilot, topic_title)
        if draft and draft.get("prod_script"):
            st.info(f"📂 Found a saved script for **{target_pilot} / {topic_title}** from {format_draft_age(draft)}.")
            if st.button("↩️ Resume This Draft", use_container_width=True):
                st.session_state[KEY_PROD_SCRIPT] = draft["prod_script"]
                st.session_state[KEY_PROD_MCQS] = draft.get("prod_mcqs", "")
                st.session_state[KEY_PROD_TOPIC] = topic_title
                st.session_state[KEY_PROD_PILOT] = target_pilot
                st.success("✅ Draft restored.")
                st.rerun()

    # Context Review Expander
    with st.expander("📑 Active Ingested Payload & Metaphor Pitch", expanded=not bool(st.session_state.get(KEY_PROD_SCRIPT))):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Source Curriculum Payload:**")
            st.text_area(
                "Payload View",
                curriculum_context or "No payload found. Load text via Page 1 (Ingest).",
                height=130,
                disabled=True,
            )
        with c2:
            st.markdown("**Selected Story Metaphor Pitch:**")
            st.text_area(
                "Metaphor View",
                chosen_metaphor or "No metaphor selected. Choose one in Page 2 (Orchestrate).",
                height=130,
                disabled=True,
            )

    # Generation Button
    if st.button("🚀 Generate Script & Calibrated Assessment", type="primary", use_container_width=True):
        if not API_KEY:
            st.error("❌ Gemini API Key not detected. Please configure GEMINI_API_KEY in your secrets.")
            return

        prompt = f"""
You are the Lead Narrative Architect and Psychometrician for 'The Vault', an educational platform delivering 90-second micro-documentaries.

CURRICULUM TOPIC: {topic_title}
TARGET COHORT: {target_pilot} ({grade_level})
TARGET LENGTH: ~{target_duration} seconds (approx. 210-230 spoken words)
METAPHOR / STORY PREMISE: {chosen_metaphor or 'Relatable high-interest real world parallel'}

SOURCE CURRICULUM:
{curriculum_context[:3000]}

Generate the output with these EXACT section markers:

=== SCRIPT MANIFEST ===
Structure into 5 sequential timed scenes with visual cues [VISUAL] and voiceover script [VO]:
- Scene 1 (00:00 - 00:15): The Hook & Setup
- Scene 2 (00:15 - 00:35): The Core Concept in Action
- Scene 3 (00:35 - 00:55): Tension & Alternative Choice
- Scene 4 (00:55 - 01:15): Strategic Decision & Resolution
- Scene 5 (01:15 - 01:25): Synthesis & Takeaway

=== ASSESSMENT PACKAGE ===
Provide exactly 4 multiple-choice questions (2 Pre-Video baseline, 2 Post-Video conceptual) formatted EXACTLY as follows:

2 Pre-Video Baseline Questions:
Question: [Clear question stem testing prior baseline knowledge]?
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct Answer: [A, B, C, or D]
Explanation: [Rationale]

Question: [Second question stem testing foundational concept]?
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct Answer: [A, B, C, or D]
Explanation: [Rationale]

2 Post-Video Conceptual Questions:
Question: [Question testing understanding of the video's narrative/concept]?
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct Answer: [A, B, C, or D]
Explanation: [Rationale]

Question: [Question testing practical real-world application of the lesson]?
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct Answer: [A, B, C, or D]
Explanation: [Rationale]
"""
        with st.spinner("Generating 90s narrative manifest and 4 psychometric MCQs..."):
            try:
                client = genai.Client(api_key=API_KEY)
                response = client.models.generate_content(model=model_name, contents=prompt)
                full_output = response.text
                if not full_output:
                    raise ValueError(
                        "Gemini returned no text (the response may have been blocked or truncated)."
                    )

                script_txt, mcq_txt = split_script_and_mcqs(full_output)
                st.session_state[KEY_PROD_SCRIPT] = script_txt
                st.session_state[KEY_PROD_MCQS] = mcq_txt
                st.session_state[KEY_RAW_PRODUCTION_OUTPUT] = full_output
                st.session_state[KEY_PROD_TOPIC] = topic_title
                st.session_state[KEY_PROD_PILOT] = target_pilot
                st.session_state[KEY_LAST_GENERATED_METAPHOR] = chosen_metaphor

                save_draft(target_pilot, topic_title, prod_script=script_txt, prod_mcqs=mcq_txt)

            except Exception as e:
                st.error(f"❌ Generation Error: {e}")

    # -------------------------------------------------------------------------
    # DISPLAY & EXPORT AREA
    # -------------------------------------------------------------------------
    if KEY_PROD_SCRIPT in st.session_state and KEY_PROD_MCQS in st.session_state:
        st.divider()
        tab_script, tab_mcq, tab_export = st.tabs([
            "📜 Script & Scene Manifest",
            "🧠 Calibrated Assessment (4 MCQs)",
            "🚀 Export to Supabase CMS",
        ])

        with tab_script:
            st.markdown("### 🎬 90-Second Cinematic Scene Manifest")
            st.markdown(st.session_state[KEY_PROD_SCRIPT])

        with tab_mcq:
            st.markdown("### 📝 Active Retrieval Assessment Package")
            edited_mcqs = st.text_area(
                "MCQ Content (Editable)",
                value=st.session_state[KEY_PROD_MCQS],
                height=350,
            )
            st.session_state[KEY_PROD_MCQS] = edited_mcqs

        with tab_export:
            st.markdown("### 🗄️ Supabase CMS Exporter (`TheVault_CMS_Core`)")
            st.caption("Auto-extracts options, verifies schema conformity, and prepares clean CSV/SQL.")

            col_u, col_l = st.columns([3, 1])
            with col_u:
                video_url_input = st.text_input(
                    "Video Watch URL:",
                    value="",
                    placeholder="https://youtu.be/... (leave blank if not uploaded yet)",
                )
            with col_l:
                vid_runtime = st.number_input(
                    "Runtime (Seconds):",
                    min_value=30,
                    max_value=300,
                    value=int(target_duration),
                )
            if not video_url_input:
                st.caption("ℹ️ No URL yet — a placeholder will be written; update the CMS row once the video is live.")

            parsed_questions = parse_mcq_text(st.session_state[KEY_PROD_MCQS])

            if len(parsed_questions) < 4:
                st.warning(
                    f"⚠️ The parser detected **{len(parsed_questions)} of 4** questions. "
                    "Ensure all 4 questions end with a '?', list options A) through D), and state 'Correct Answer: [Letter]'."
                )
                with st.expander("Show Diagnostic Text"):
                    st.caption("Parsed MCQ text (as edited above):")
                    st.text(st.session_state[KEY_PROD_MCQS])
                    raw = st.session_state.get(KEY_RAW_PRODUCTION_OUTPUT)
                    if raw:
                        st.caption("Full raw Gemini output for this generation, before script/assessment splitting:")
                        st.text(raw)
            else:
                try:
                    cms_row = build_cms_row(
                        topic=st.session_state.get(KEY_PROD_TOPIC, topic_title),
                        video_url=video_url_input,
                        video_len=vid_runtime,
                        pilot_id=st.session_state.get(KEY_PROD_PILOT, target_pilot),
                        parsed_questions=parsed_questions,
                    )
                    df_export = pd.DataFrame([cms_row])

                    st.success(f"✅ Verified all 4 questions for cohort `{cms_row['pilot_id']}`!")

                    with st.expander("👀 Inspect Formatted Database Row", expanded=False):
                        st.dataframe(df_export, use_container_width=True)

                    btn_c1, btn_c2 = st.columns(2)
                    with btn_c1:
                        csv_data = df_export.to_csv(index=False)
                        filename = f"TheVault_CMS_{cms_row['pilot_id']}_{cms_row['Topic'][:20].replace(' ', '_')}.csv"
                        st.download_button(
                            label="📥 Download Clean CSV for Supabase",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv",
                            type="primary",
                            use_container_width=True,
                        )

                    sql_statement = generate_sql_insert_statement(cms_row)
                    with btn_c2:
                        st.download_button(
                            label="💾 Download SQL File (.sql)",
                            data=sql_statement,
                            file_name=f"insert_{cms_row['pilot_id']}.sql",
                            mime="text/plain",
                            use_container_width=True,
                        )

                    st.markdown("#### ⚡ Copy & Run SQL Directly in Supabase:")
                    st.code(sql_statement, language="sql")

                    st.divider()
                    st.caption(
                        "Once this row has actually been inserted into Supabase, mark the draft done "
                        "so it stops appearing as a resumable draft."
                    )
                    if st.button(
                        "✅ Mark as Shipped (clear saved draft)",
                        use_container_width=True,
                        key="mark_shipped",
                    ):
                        pilot_for_delete = st.session_state.get(KEY_PROD_PILOT, target_pilot)
                        topic_for_delete = st.session_state.get(KEY_PROD_TOPIC, topic_title)
                        if delete_draft(pilot_for_delete, topic_for_delete):
                            st.success(f"🗑️ Draft cleared for `{pilot_for_delete} / {topic_for_delete}`.")
                        else:
                            st.warning("Could not clear the draft (it may already be gone, or the DB is unreachable).")

                except Exception as e:
                    st.error(f"❌ Schema alignment error: {e}")


if __name__ == "__main__":
    main()
