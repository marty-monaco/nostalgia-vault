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
# ASSESSMENT EXTRACTION & SQL/CSV BUILDERS
# -----------------------------------------------------------------------------
def clean_question_text(q_text: str) -> str:
    """Removes lingering section headers, numbers, and prompt artifacts."""
    lines = [line.strip() for line in q_text.splitlines() if line.strip()]
    cleaned = []
    for line in lines:
        if line.lower().startswith("explanation:"):
            continue
        if re.search(r"^\d+\s*post-video", line, re.IGNORECASE):
            continue
        if re.search(r"^\d+\s*pre-video", line, re.IGNORECASE):
            continue
        if re.match(r"^(?:question\s*\d*:?|\d+[\.\)]\s*)", line, re.IGNORECASE):
            line = re.sub(r"^(?:question\s*\d*:?|\d+[\.\)]\s*)", "", line, flags=re.IGNORECASE).strip()
        cleaned.append(line)
    return " ".join(cleaned).strip()


def parse_mcq_text(text: str) -> list[dict]:
    """
    Robust regex parser that extracts question stems, options (A-D),
    and declared correct answers from Gemini's assessment output.
    """
    pattern = re.compile(
        r"(?P<q_text>.*?\?)\s*"
        r"A\)\s*(?P<opt_a>.*?)\s*"
        r"B\)\s*(?P<opt_b>.*?)\s*"
        r"C\)\s*(?P<opt_c>.*?)\s*"
        r"(?:D\)\s*(?P<opt_d>.*?)\s*)?"
        r"Correct Answer:\s*(?P<ans>[A-D])",
        re.DOTALL | re.IGNORECASE,
    )

    matches = list(pattern.finditer(text))
    parsed = []
    for m in matches:
        q = clean_question_text(m.group("q_text"))
        a = m.group("opt_a").strip()
        b = m.group("opt_b").strip()
        c = m.group("opt_c").strip()
        d = m.group("opt_d").strip() if m.group("opt_d") else ""
        ans_letter = m.group("ans").upper()

        opt_dict = {"A": a, "B": b, "C": c, "D": d}
        correct_text = opt_dict.get(ans_letter, "")

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
    Formats parsed questions (2 Pre, 2 Post) into the 25-column schema
    required by Supabase table `TheVault_CMS_Core`.
    """
    if len(parsed_questions) < 4:
        raise ValueError(f"Expected 4 MCQs, but parsed only {len(parsed_questions)}.")

    q1, q2, q3, q4 = parsed_questions[0], parsed_questions[1], parsed_questions[2], parsed_questions[3]

    def _select_3_options(q: dict) -> tuple[str, str, str]:
        """
        Supabase table has Opt1, Opt2, Opt3. Ensures the correct answer
        is guaranteed to be among the three options even if it was originally 'D'.
        """
        correct = q["correct_text"]
        opts = [opt for opt in q["options"] if opt]
        if correct in opts[:3]:
            return opts[0], opts[1], opts[2]
        # Swap the 3rd distractor with the correct answer
        return opts[0], opts[1], correct

    pre_o1, pre_o2, pre_o3 = _select_3_options(q1)
    pre_o1_q2, pre_o2_q2, pre_o3_q2 = _select_3_options(q2)
    pst_o1, pst_o2, pst_o3 = _select_3_options(q3)
    pst_o1_q2, pst_o2_q2, pst_o3_q2 = _select_3_options(q4)

    return {
        "Topic": topic,
        "Video_URL": video_url or "https://youtu.be/placeholder",
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
        "Video_Length_Sec": int(video_len),
        "pilot_id": pilot_id,
    }


def generate_sql_insert_statement(row: dict) -> str:
    """Constructs a production-ready SQL INSERT with escaped single quotes."""
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
# MAIN APPLICATION INTERFACE
# -----------------------------------------------------------------------------
def main():
    st.title("🎬 PRODUCTION ENGINE")
    st.caption("Generate 90-Second Micro-Documentary Scripts & Calibrated Assessment Packages")

    # Context retrieval from earlier tabs or fallback
    curriculum_context = st.session_state.get("active_curriculum_payload", "")
    chosen_metaphor = st.session_state.get("selected_metaphor_pitch", "")

    with st.sidebar:
        st.header("⚙️ Generation Parameters")
        target_pilot = st.text_input("Cohort / Pilot ID", value="WIRAPIDS_12")
        topic_title = st.text_input("Curriculum Topic Title", value="Scarcity & Trade-Offs")
        target_duration = st.slider("Target Duration (seconds)", min_value=60, max_value=120, value=85, step=5)
        grade_level = st.selectbox(
            "Cognitive Rigor Level",
            ["High School Standard (12th Grade)", "AP / Introductory College", "Undergraduate Advanced"],
            index=0,
        )
        model_name = st.selectbox("Gemini Engine", ["gemini-1.5-pro", "gemini-1.5-flash"], index=0)

    # Context Review Expander
    with st.expander("📑 View Loaded Curriculum & Metaphor Context", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Source Curriculum Payload:**")
            st.text_area("Payload", curriculum_context or "No active payload in session state. Using default context.", height=150, disabled=True)
        with c2:
            st.markdown("**Approved Story Metaphor Pitch:**")
            st.text_area("Metaphor", chosen_metaphor or "The Creator Economy: Production Time vs. Trend Velocity", height=150, disabled=True)

    # Action Trigger
    generate_btn = st.button("🚀 Generate Script & Assessment Package", type="primary", use_container_width=True)

    if generate_btn:
        if not API_KEY:
            st.error("❌ Gemini API Key not detected. Please set GEMINI_API_KEY in your environment or Streamlit secrets.")
            return

        prompt = f"""
You are the Lead Narrative Architect and Psychometrics Specialist for 'The Vault', an educational platform delivering cinematic 90-second micro-documentaries.

CURRICULUM TOPIC: {topic_title}
TARGET COHORT: {target_pilot} ({grade_level})
TARGET LENGTH: ~{target_duration} seconds (approx. 210-235 spoken words)
METAPHOR / STORY PREMISE: {chosen_metaphor or 'Relatable high-interest real world parallel'}
SOURCE MATERIAL:
{curriculum_context[:2500]}

Generate two distinct sections:

SECTION 1: 90-SECOND CINEMATIC SCRIPT & TIMED SCENE MANIFEST
Structure into 5 sequential scenes:
- Scene 1 (00:00 - 00:15): Hook & The Metaphor Setup
- Scene 2 (00:15 - 00:35): Core Concept Integration (The Textbook Rule in Action)
- Scene 3 (00:35 - 00:55): Tension / Downside Risk / The Alternative Choice
- Scene 4 (00:55 - 01:15): Resolution & The Strategic Decision
- Scene 5 (01:15 - 01:25): Synthesis & Pedagogical Takeaway
Include visual cues [VISUAL] and voiceover script [VO].

SECTION 2: CALIBRATED ASSESSMENT PACKAGE
Provide exactly 4 multiple-choice questions formatted EXACTLY as follows:

2 Pre-Video Baseline Questions:
Question: [Clear question stem testing prior baseline knowledge]?
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct Answer: [Letter]
Explanation: [1-sentence rationale]

Question: [Clear question stem testing related baseline reasoning]?
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct Answer: [Letter]
Explanation: [1-sentence rationale]

2 Post-Video Conceptual Questions:
Question: [Question testing understanding of the video's specific narrative/concept]?
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct Answer: [Letter]
Explanation: [1-sentence rationale]

Question: [Question applying the video's lesson to a practical business decision]?
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]
Correct Answer: [Letter]
Explanation: [1-sentence rationale]
"""
        with st.spinner("Generating cinematic narrative and calibrated psychometric items..."):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                full_text = response.text

                # Store in session state
                st.session_state["raw_production_output"] = full_text

                # Split script vs questions
                if "SECTION 2:" in full_text:
                    parts = full_text.split("SECTION 2:")
                    st.session_state["prod_script"] = parts[0].replace("SECTION 1:", "").strip()
                    st.session_state["prod_mcqs"] = parts[1].strip()
                else:
                    st.session_state["prod_script"] = full_text
                    st.session_state["prod_mcqs"] = full_text

            except Exception as e:
                st.error(f"❌ Generation Error: {e}")

    # -------------------------------------------------------------------------
    # DISPLAY & EXPORT AREA
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
            st.markdown(st.session_state["prod_mcqs"])

        with tab_export:
            st.markdown("### 🗄️ One-Click CMS Ingestion")
            st.caption("Automatic parsing, option extraction, and schema alignment for `TheVault_CMS_Core`.")

            c_url, c_vid_len = st.columns([3, 1])
            with c_url:
                video_url_input = st.text_input(
                    "YouTube Watch URL (Embed or Staged link):",
                    value="https://youtu.be/placeholder",
                    help="Can be updated later once video render is published.",
                )
            with c_vid_len:
                final_length = st.number_input(
                    "Video Duration (sec):",
                    min_value=30,
                    max_value=300,
                    value=int(target_duration),
                )

            # Automated Option Extraction
            parsed_questions = parse_mcq_text(st.session_state["prod_mcqs"])

            if len(parsed_questions) < 4:
                st.warning(
                    f"⚠️ Parser detected {len(parsed_questions)} of 4 questions. "
                    "Make sure your MCQs have question marks, A)-D) options, and 'Correct Answer: [Letter]'."
                )
                with st.expander("View Raw MCQ Text to Diagnose:"):
                    st.text(st.session_state["prod_mcqs"])
            else:
                try:
                    cms_row = build_cms_row(
                        topic=topic_title,
                        video_url=video_url_input,
                        video_len=final_length,
                        pilot_id=target_pilot,
                        parsed_questions=parsed_questions,
                    )
                    df_export = pd.DataFrame([cms_row])

                    st.success(f"✅ Successfully validated all 4 questions for cohort `{target_pilot}`!")

                    # Quick Preview Table
                    with st.expander("👀 Inspect Generated Schema Record", expanded=False):
                        st.dataframe(df_export, use_container_width=True)

                    btn_col1, btn_col2 = st.columns(2)

                    # Option A: CSV Download
                    with btn_col1:
                        csv_data = df_export.to_csv(index=False)
                        filename = f"TheVault_CMS_{target_pilot}_{topic_title.replace(' ', '_')}.csv"
                        st.download_button(
                            label="📥 Download Supabase CSV",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv",
                            type="primary",
                            use_container_width=True,
                        )

                    # Option B: Instant SQL Query
                    sql_query = generate_sql_insert_statement(cms_row)
                    with btn_col2:
                        show_sql = st.button("⚡ Show SQL Insert Code", use_container_width=True)

                    if show_sql:
                        st.code(sql_query, language="sql")
                        st.caption("Copy and paste this snippet directly into your Supabase SQL Editor.")

                    # Permanent copy box in expander
                    with st.expander("📋 Copyable SQL Query", expanded=False):
                        st.code(sql_query, language="sql")

                except Exception as e:
                    st.error(f"Error structuring CMS payload: {e}")


if __name__ == "__main__":
    main()
