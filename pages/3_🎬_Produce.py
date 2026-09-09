"""
The Vault — Page 3: Production Engine & Assessment Exporter
Generates 90-second micro-documentary scripts, voiceover scene manifests,
calibrated 4-question retrieval assessments, and exports directly to
TheVault_CMS_Core via clean CSV or copyable SQL INSERT statements.
"""

import os
import re
import pandas as pd
import streamlit as st
import google.generativeai as genai
from datetime import datetime

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
API_KEY = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None)

if API_KEY:
    genai.configure(api_key=API_KEY)


# -----------------------------------------------------------------------------
# ROBUST SPLITTING & PARSING HELPERS
# -----------------------------------------------------------------------------
def split_script_and_mcqs(text: str) -> tuple[str, str]:
    """
    Intelligently splits the LLM output into the Script and Assessment sections
    without colliding with source text section numbers (e.g., SECTION 4, SECTION 5).
    """
    # Look for unambiguous assessment boundaries
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
        # Clean leading section tags from script
        script_part = re.sub(r"^SECTION\s*1\s*:[^\n]*\n?", "", script_part, flags=re.IGNORECASE).strip()
        return script_part, mcq_part

    # Fallback if no explicit marker matched
    return text, text


def clean_question_text(q_text: str) -> str:
    """Removes leftover header lines, numbering, and prompt artifacts."""
    lines = [line.strip() for line in q_text.splitlines() if line.strip()]
    cleaned = []
    for line in lines:
        lower = line.lower()
        if lower.startswith("explanation:"):
            continue
        if "pre-video" in lower or "post-video" in lower:
            continue
        if lower.startswith("calibrated assessment") or lower.startswith("section"):
            continue
        # Strip leading "Question 1:", "Question:", "1.", etc.
        line = re.sub(r"^(?:question\s*\d*:?|\d+[\.\)]\s*)", "", line, flags=re.IGNORECASE).strip()
        cleaned.append(line)
    return " ".join(cleaned).strip()


def parse_mcq_text(text: str) -> list[dict]:
    """
    Extracts question stems, options (A-D), and declared correct answers.
    """
    pattern = re.compile(
        r"(?P<q_text>[^\n\?]+(?:\?|\:|\.))\s*"
        r"(?:[A-D]\)|\(?A\))\s*(?P<opt_a>.*?)\s*"
        r"(?:[B-D]\)|\(?B\))\s*(?P<opt_b>.*?)\s*"
        r"(?:[C-D]\)|\(?C\))\s*(?P<opt_c>.*?)\s*"
        r"(?:(?:D\)|\(?D\))\s*(?P<opt_d>.*?)\s*)?"
        r"Correct\s*Answer\s*:\s*(?P<ans>[A-D])",
        re.DOTALL | re.IGNORECASE,
    )

    matches = list(pattern.finditer(text))
    parsed = []
    for m in matches:
        q = clean_question_text(m.group("q_text"))
        a = m.group("opt_a").strip().replace("\n", " ")
        b = m.group("opt_b").strip().replace("\n", " ")
        c = m.group("opt_c").strip().replace("\n", " ")
        d = m.group("opt_d").strip().replace("\n", " ") if m.group("opt_d") else ""
        ans_letter = m.group("ans").upper()

        opt_dict = {"A": a, "B": b, "C": c, "D": d}
        correct_text = opt_dict.get(ans_letter, "")

        if q:
            parsed.append({
                "question": q,
                "options": [a, b, c, d],
                "correct_letter": ans_letter,
                "correct_text": correct_text,
            })
    return parsed


def build_cms_row(
    topic: str,
    video_url: str,
    video_len: int,
    pilot_id: str,
    parsed_questions: list[dict],
) -> dict:
    """
    Maps questions into the exact 25-column schema for TheVault_CMS_Core.
    Guarantees the correct answer is present in Opt1..Opt3.
    """
    if len(parsed_questions) < 4:
        raise ValueError(f"Expected 4 MCQs, but parsed {len(parsed_questions)}.")

    q1, q2, q3, q4 = parsed_questions[0], parsed_questions[1], parsed_questions[2], parsed_questions[3]

    def _select_3_options(q: dict) -> tuple[str, str, str]:
        correct = q["correct_text"]
        opts = [opt for opt in q["options"] if opt]
        if correct in opts[:3]:
            # Fill missing if less than 3
            while len(opts) < 3:
                opts.append("")
            return opts[0], opts[1], opts[2]
        # Swap 3rd option with correct answer if it was on D
        return (opts[0] if len(opts) > 0 else ""), (opts[1] if len(opts) > 1 else ""), correct

    pre_o1, pre_o2, pre_o3 = _select_3_options(q1)
    pre_o1_q2, pre_o2_q2, pre_o3_q2 = _select_3_options(q2)
    pst_o1, pst_o2, pst_o3 = _select_3_options(q3)
    pst_o1_q2, pst_o2_q2, pst_o3_q2 = _select_3_options(q4)

    return {
        "pilot_id": pilot_id,
        "Topic": topic,
        "Video_URL": video_url or "https://youtu.be/placeholder",
        "Video_Length_Sec": int(video_len),
        "Pre_Q1": q1["question"],
        "Pre_Opt1": pre_o1,
        "Pre_Opt2": pre_o2,
        "Pre_Opt3": pre_o3,
        "Pre_A1": q1["correct_text"],
        "Pre_Q2": q2["question"],
        "Pre_Opt1_Q2": pre_o1_q2,
        "Pre_Opt2_Q2": pre_o2_q2,
        "Pre_Opt3_Q2": pre_o3_q2,
        "Pre_A2": q2["correct_text"],
        "Post_Q1": q3["question"],
        "Post_Opt1": pst_o1,
        "Post_Opt2": pst_o2,
        "Post_Opt3": pst_o3,
        "Post_A1": q3["correct_text"],
        "Post_Q2": q4["question"],
        "Post_Opt1_Q2": pst_o1_q2,
        "Post_Opt2_Q2": pst_o2_q2,
        "Post_Opt3_Q2": pst_o3_q2,
        "Post_A2": q4["correct_text"],
        "NPS_Question": "Would you recommend The Vault to a peer?",
    }


def generate_sql_insert_statement(row: dict) -> str:
    """Generates an escaped, executable SQL INSERT statement for Supabase."""
    def esc(val):
        if val is None:
            return "NULL"
        if isinstance(val, (int, float)):
            return str(val)
        return "'" + str(val).replace("'", "''") + "'"

    cols = list(row.keys())
    quoted_cols = [f'"{col}"' if col != "pilot_id" else col for col in cols]
    vals = [esc(row[col]) for col in cols]

    return f"""insert into "TheVault_CMS_Core" (
  {', '.join(quoted_cols)}
)
values (
  {', '.join(vals)}
);"""


# -----------------------------------------------------------------------------
# MAIN APP INTERFACE
# -----------------------------------------------------------------------------
def main():
    st.title("🎬 PRODUCTION ENGINE")
    st.caption("Generate 90-Second Micro-Documentary Scripts & Calibrated Assessment Packages")

    # Ingestion session context
    curriculum_context = st.session_state.get("active_curriculum_payload", "")
    chosen_metaphor = st.session_state.get("selected_metaphor_pitch", "")

    with st.sidebar:
        st.header("⚙️ Parameters")
        target_pilot = st.text_input("Cohort / Pilot ID", value="WIRAPIDS_12")
        topic_title = st.text_input("Curriculum Topic Title", value="What is Economics? Scarcity & Trade-Offs")
        target_duration = st.slider("Target Duration (seconds)", min_value=60, max_value=120, value=85, step=5)
        grade_level = st.selectbox(
            "Cognitive Rigor Level",
            ["High School Standard (12th Grade)", "AP / Introductory College", "Undergraduate Advanced"],
            index=0,
        )
        model_name = st.selectbox("Gemini Model", ["gemini-1.5-pro", "gemini-1.5-flash"], index=0)

    # Active Context Preview
    with st.expander("📑 Active Curriculum Payload & Metaphor Context", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Source Curriculum Payload:**")
            st.text_area(
                "Payload View",
                curriculum_context or "No active payload in session state. You can paste curriculum into Page 1 (Ingest).",
                height=150,
                disabled=True,
            )
        with c2:
            st.markdown("**Selected Story Metaphor Pitch:**")
            st.text_area(
                "Metaphor View",
                chosen_metaphor or "Triage on the Battlefield: Scarcity and Alternative Uses Without Money",
                height=150,
                disabled=True,
            )

    # Trigger Generation
    if st.button("🚀 Generate Script & Calibrated Assessment", type="primary", use_container_width=True):
        if not API_KEY:
            st.error("❌ Gemini API Key not detected. Please configure GEMINI_API_KEY in your secrets or environment.")
            return

        prompt = f"""
You are the Lead Narrative Architect and Psychometrician for 'The Vault', an educational platform delivering 90-second micro-documentaries.

CURRICULUM TOPIC: {topic_title}
TARGET COHORT: {target_pilot} ({grade_level})
TARGET LENGTH: ~{target_duration} seconds (approx. 210-230 spoken words)
METAPHOR / STORY PREMISE: {chosen_metaphor or 'Relatable high-interest real world parallel'}

SOURCE CURRICULUM:
{curriculum_context[:3000]}

Generate the output with these EXACT markers:

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
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                full_output = response.text

                # Resilient splitting
                script_txt, mcq_txt = split_script_and_mcqs(full_output)
                st.session_state["prod_script"] = script_txt
                st.session_state["prod_mcqs"] = mcq_txt
                st.session_state["prod_topic"] = topic_title
                st.session_state["prod_pilot"] = target_pilot

            except Exception as e:
                st.error(f"❌ Generation Error: {e}")

    # -------------------------------------------------------------------------
    # DISPLAY & EXPORT TABS
    # -------------------------------------------------------------------------
    if "prod_script" in st.session_state and "prod_mcqs" in st.session_state:
        st.divider()
        tab_script, tab_mcq, tab_export = st.tabs([
            "📜 Script & Scene Manifest",
            "🧠 Calibrated Assessment (4 MCQs)",
            "🚀 Export to Supabase CMS",
        ])

        with tab_script:
            st.markdown("### 🎬 90-Second Cinematic Scene Manifest")
            st.markdown(st.session_state["prod_script"])

        with tab_mcq:
            st.markdown("### 📝 Active Retrieval Assessment Package")
            # Editable in case fine-tuning is desired
            edited_mcqs = st.text_area(
                "MCQ Content (Editable)",
                value=st.session_state["prod_mcqs"],
                height=350,
            )
            st.session_state["prod_mcqs"] = edited_mcqs

        with tab_export:
            st.markdown("### 🗄️ Supabase CMS Exporter (`TheVault_CMS_Core`)")
            st.caption("Auto-extracts options, verifies schema conformity, and prepares clean CSV/SQL.")

            col_u, col_l = st.columns([3, 1])
            with col_u:
                video_url_input = st.text_input(
                    "Video Watch URL:",
                    value="https://youtu.be/placeholder",
                )
            with col_l:
                vid_runtime = st.number_input(
                    "Runtime (Seconds):",
                    min_value=30,
                    max_value=300,
                    value=int(target_duration),
                )

            # Parse questions
            parsed_questions = parse_mcq_text(st.session_state["prod_mcqs"])

            if len(parsed_questions) < 4:
                st.warning(
                    f"⚠️ The parser detected **{len(parsed_questions)} of 4** questions. "
                    "Ensure all 4 questions end with a '?', list options A) through D), and declare 'Correct Answer: [Letter]'."
                )
                with st.expander("Show Diagnostic Text"):
                    st.text(st.session_state["prod_mcqs"])
            else:
                try:
                    cms_row = build_cms_row(
                        topic=st.session_state.get("prod_topic", topic_title),
                        video_url=video_url_input,
                        video_len=vid_runtime,
                        pilot_id=st.session_state.get("prod_pilot", target_pilot),
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

                except Exception as e:
                    st.error(f"❌ Schema alignment error: {e}")


if __name__ == "__main__":
    main()
