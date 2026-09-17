"""
utils/export_helpers.py

Parses generated MCQ assessment text into TheVault_CMS_Core schema,
generating exportable CSV data and direct-to-SQL statements.
"""
import random
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

    parsed = []
    for match in pattern.finditer(text):
        options = [
            match.group("opt_a").strip(),
            match.group("opt_b").strip(),
            match.group("opt_c").strip(),
            match.group("opt_d").strip() if match.group("opt_d") else "",
        ]
        answer = options[ord(match.group("ans").upper()) - ord("A")]
        parsed.append({
            "question": clean_question_text(match.group("q_text")),
            "options": options,
            "correct_letter": match.group("ans").upper(),
            "correct_text": answer,
        })
    return parsed



def _shuffle_options(q: dict) -> tuple[list[str], str]:
    """Shuffle answer choices while preserving the correct answer text."""
    options = [option for option in q["options"] if option]
    correct = q["correct_text"]
    if correct not in options:
        raise ValueError("Correct answer is not present in the question options.")
    random.SystemRandom().shuffle(options)
    return options[:3], correct



def build_cms_row(topic: str, video_url: str, video_len: int, pilot_id: str, parsed_questions: list[dict]) -> dict:
    """Formats 4 parsed MCQs with independently randomized answer positions."""
    if len(parsed_questions) < 4:
        raise ValueError(f"Expected 4 MCQs, but only parsed {len(parsed_questions)}.")

    q1, q2, q3, q4 = parsed_questions[:4]
    shuffled = [_shuffle_options(question) for question in (q1, q2, q3, q4)]
    (pre_o1, pre_o2, pre_o3), pre_a1 = shuffled[0]
    (pre_o1_q2, pre_o2_q2, pre_o3_q2), pre_a2 = shuffled[1]
    (pst_o1, pst_o2, pst_o3), pst_a1 = shuffled[2]
    (pst_o1_q2, pst_o2_q2, pst_o3_q2), pst_a2 = shuffled[3]

    return {
        "Topic": topic,
        "Video_URL": video_url or "https://youtu.be/placeholder",
        "Pre_Q1": q1["question"],
        "Pre_Opt1": pre_o1,
        "Pre_Opt2": pre_o2,
        "Pre_Opt3": pre_o3,
        "Pre_A1": pre_a1,
        "Pre_Q2": q2["question"],
        "Pre_Opt1_Q2": pre_o1_q2,
        "Pre_Opt2_Q2": pre_o2_q2,
        "Pre_Opt3_Q2": pre_o3_q2,
        "Pre_A2": pre_a2,
        "Post_Q1": q3["question"],
        "Post_Opt1": pst_o1,
        "Post_Opt2": pst_o2,
        "Post_Opt3": pst_o3,
        "Post_A1": pst_a1,
        "Post_Q2": q4["question"],
        "Post_Opt1_Q2": pst_o1_q2,
        "Post_Opt2_Q2": pst_o2_q2,
        "Post_Opt3_Q2": pst_o3_q2,
        "Post_A2": pst_a2,
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

    return f"""insert into \"TheVault_CMS_Core\" (
  {', '.join(quoted_cols)}
)
values (
  {', '.join(vals)}
);"""
