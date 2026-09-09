"""
utils/export_helpers.py

Parses generated MCQ assessment text into TheVault_CMS_Core schema,
generating exportable CSV data and direct-to-SQL statements.
"""
import re
import pandas as pd


def clean_question_text(q_text: str) -> str:
    """Removes leftover prompt headers or explanations from question stems."""
    lines = [line.strip() for line in q_text.splitlines() if line.strip()]
    cleaned = []
    for line in lines:
        if line.lower().startswith("explanation:"):
            continue
        if re.search(r"^\d+\s*post-video", line, re.IGNORECASE):
            continue
        if re.search(r"^\d+\s*pre-video", line, re.IGNORECASE):
            continue
        if re.match(r"^(?:question\s*\d+:?|\d+[\.\)]\s*)", line, re.IGNORECASE):
            line = re.sub(r"^(?:question\s*\d+:?|\d+[\.\)]\s*)", "", line, flags=re.IGNORECASE).strip()
        cleaned.append(line)
    return " ".join(cleaned).strip()


def parse_mcq_text(text: str) -> list[dict]:
    """Extracts questions, A-D options, and correct answers from raw LLM output."""
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


def build_cms_row(topic: str, video_url: str, video_len: int, pilot_id: str, parsed_questions: list[dict]) -> dict:
    """Formats 4 parsed questions (2 Pre, 2 Post) into the 25-column CMS schema."""
    if len(parsed_questions) < 4:
        raise ValueError(f"Expected 4 MCQs, but only parsed {len(parsed_questions)}.")

    q1, q2, q3, q4 = parsed_questions[0], parsed_questions[1], parsed_questions[2], parsed_questions[3]

    def _select_3_options(q: dict) -> tuple[str, str, str]:
        """Supabase CMS schema uses Opt1, Opt2, Opt3. Ensures correct answer is present."""
        correct = q["correct_text"]
        opts = [opt for opt in q["options"] if opt]
        if correct in opts[:3]:
            return opts[0], opts[1], opts[2]
        # Swap third distractor with the correct answer if it fell on Option D
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
    """Generates an escaped SQL INSERT query matching TheVault_CMS_Core."""
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
