"""
utils/export_helpers.py

Single source of truth for turning generated MCQ text into a TheVault_CMS_Core
row and into export formats. 3_Produce.py imports from here; do not re-define
these functions inside a page.

Export paths
------------
* generate_sql_insert_statement(row)  Copy/paste or .sql download for the Supabase
                                      SQL editor. A text statement cannot be
                                      parameterized, so every identifier is checked
                                      against CMS_COLUMNS and every value is
                                      validated and escaped in one place.
* build_parameterized_insert(row)     (sql, params) for a real database driver
                                      (psycopg etc.). Values never touch the SQL text.
* validate_cms_row(row)               Checked dict for supabase-py:
                                      client.table(CMS_TABLE).insert(validate_cms_row(row))
"""
from __future__ import annotations

import math
import numbers
import random
import re

CMS_TABLE = "TheVault_CMS_Core"

# Exact TheVault_CMS_Core schema, in export order. This is also the whitelist
# of identifiers allowed to appear in generated SQL.
CMS_COLUMNS: tuple[str, ...] = (
    "pilot_id", "Topic", "Video_URL", "Video_Length_Sec",
    "Pre_Q1", "Pre_Opt1", "Pre_Opt2", "Pre_Opt3", "Pre_A1",
    "Pre_Q2", "Pre_Opt1_Q2", "Pre_Opt2_Q2", "Pre_Opt3_Q2", "Pre_A2",
    "Post_Q1", "Post_Opt1", "Post_Opt2", "Post_Opt3", "Post_A1",
    "Post_Q2", "Post_Opt1_Q2", "Post_Opt2_Q2", "Post_Opt3_Q2", "Post_A2",
    "NPS_Question",
)

_RNG = random.SystemRandom()


# ---------------------------------------------------------------------------
# PARSING (moved verbatim from 3_Produce.py, which had the live versions)
# ---------------------------------------------------------------------------
def clean_question_text(q_text: str) -> str:
    """Strips section labels, explanations, and question numbering."""
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
        line = re.sub(r"^(?:question\s*\d*:?|\d+[\.\)]\s*)", "", line, flags=re.IGNORECASE).strip()
        cleaned.append(line)
    return " ".join(cleaned).strip()


def parse_mcq_text(text: str) -> list[dict]:
    """Extracts question stems, options A-D, and declared correct answers."""
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


# ---------------------------------------------------------------------------
# ROW BUILDING
# ---------------------------------------------------------------------------
def _select_options(q: dict, randomize: bool, rng: random.Random) -> tuple[str, str, str]:
    """
    Pick the 3 options stored for a question. The correct answer is always
    among them; otherwise raise so a broken row is never exported silently.

    randomize=False keeps the LLM's order (D-answers slot into position 3).
    randomize=True keeps the correct answer + 2 random distractors and shuffles
    all three, which removes the LLM's positional bias toward certain letters.
    """
    correct = q["correct_text"]
    options = [opt for opt in q["options"] if opt]
    stem = q["question"][:60]

    if not correct or correct not in options:
        raise ValueError(
            f"Question '{stem}...' declares 'Correct Answer: {q['correct_letter']}' "
            "but that option is empty or missing."
        )

    if randomize:
        distractors = [opt for opt in options if opt != correct]
        if len(distractors) < 2:
            raise ValueError(f"Question '{stem}...' needs at least 2 distinct wrong options.")
        chosen = rng.sample(distractors, 2) + [correct]
        rng.shuffle(chosen)
        return chosen[0], chosen[1], chosen[2]

    if len(options) < 3:
        raise ValueError(f"Question '{stem}...' has fewer than 3 options.")
    if correct in options[:3]:
        return options[0], options[1], options[2]
    return options[0], options[1], correct


def build_cms_row(
    topic: str,
    video_url: str,
    video_len: int,
    pilot_id: str,
    parsed_questions: list[dict],
    randomize_positions: bool = False,
    rng: random.Random | None = None,
) -> dict:
    """
    Structure 4 parsed questions (2 Pre, 2 Post) into the 25-column
    TheVault_CMS_Core row. Keys are returned in CMS_COLUMNS order.
    """
    if len(parsed_questions) < 4:
        raise ValueError(f"Expected 4 MCQs, but parsed {len(parsed_questions)}.")

    rng = rng or _RNG
    q1, q2, q3, q4 = parsed_questions[:4]
    o1, o2, o3, o4 = (_select_options(q, randomize_positions, rng) for q in (q1, q2, q3, q4))

    row = {
        "pilot_id": pilot_id,
        "Topic": topic,
        "Video_URL": video_url or "https://youtu.be/placeholder",
        "Video_Length_Sec": int(video_len),
        "Pre_Q1": q1["question"],
        "Pre_Opt1": o1[0], "Pre_Opt2": o1[1], "Pre_Opt3": o1[2],
        "Pre_A1": q1["correct_text"],
        "Pre_Q2": q2["question"],
        "Pre_Opt1_Q2": o2[0], "Pre_Opt2_Q2": o2[1], "Pre_Opt3_Q2": o2[2],
        "Pre_A2": q2["correct_text"],
        "Post_Q1": q3["question"],
        "Post_Opt1": o3[0], "Post_Opt2": o3[1], "Post_Opt3": o3[2],
        "Post_A1": q3["correct_text"],
        "Post_Q2": q4["question"],
        "Post_Opt1_Q2": o4[0], "Post_Opt2_Q2": o4[1], "Post_Opt3_Q2": o4[2],
        "Post_A2": q4["correct_text"],
        "NPS_Question": "Would you recommend The Vault to a peer?",
    }
    assert tuple(row) == CMS_COLUMNS, "build_cms_row is out of sync with CMS_COLUMNS"
    return row


# ---------------------------------------------------------------------------
# VALIDATION + SQL
# ---------------------------------------------------------------------------
def _clean_value(col: str, val):
    """Normalise one cell: keep None/bool/int/finite float, stringify the rest."""
    if val is None or isinstance(val, bool):
        return val
    if isinstance(val, numbers.Integral):
        return int(val)
    if isinstance(val, numbers.Real):
        if not math.isfinite(float(val)):
            raise ValueError(f"Column '{col}' holds a non-finite number ({val}).")
        return float(val)
    return str(val).replace("\x00", "")  # Postgres cannot store NUL characters


def validate_cms_row(row: dict) -> dict:
    """
    Return a cleaned copy of row in CMS_COLUMNS order. Raises ValueError on any
    missing or unknown column, so nothing outside the schema can reach SQL.
    """
    unknown = sorted(set(row) - set(CMS_COLUMNS))
    missing = [c for c in CMS_COLUMNS if c not in row]
    if unknown or missing:
        raise ValueError(f"Row does not match {CMS_TABLE}: unknown={unknown}, missing={missing}")
    return {col: _clean_value(col, row[col]) for col in CMS_COLUMNS}


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _sql_literal(val) -> str:
    """
    Render a validated value as a Postgres literal. Backslash-containing strings
    use E'...' with backslashes doubled, so the result is identical whether or
    not standard_conforming_strings is on.
    """
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, numbers.Integral):
        return str(int(val))
    if isinstance(val, numbers.Real):
        if not math.isfinite(float(val)):
            raise ValueError("Non-finite numbers cannot be written as SQL literals.")
        return repr(float(val))
    text = str(val).replace("\x00", "")
    escaped = text.replace("'", "''")
    if "\\" in text:
        return "E'" + escaped.replace("\\", "\\\\") + "'"
    return "'" + escaped + "'"


def generate_sql_insert_statement(row: dict) -> str:
    """Build a copyable INSERT for the Supabase SQL editor (all values escaped)."""
    clean = validate_cms_row(row)
    cols = ", ".join(_quote_ident(c) for c in CMS_COLUMNS)
    vals = ", ".join(_sql_literal(clean[c]) for c in CMS_COLUMNS)
    return f"insert into {_quote_ident(CMS_TABLE)} (\n  {cols}\n)\nvalues (\n  {vals}\n);"


def build_parameterized_insert(row: dict, placeholder: str = "%s") -> tuple[str, list]:
    """
    Return (sql, params) for a real driver. Values are bound by the driver and
    never appear in the SQL text. Use placeholder="?" for sqlite, "%s" for psycopg.
    """
    clean = validate_cms_row(row)
    cols = ", ".join(_quote_ident(c) for c in CMS_COLUMNS)
    marks = ", ".join([placeholder] * len(CMS_COLUMNS))
    sql = f"insert into {_quote_ident(CMS_TABLE)} ({cols}) values ({marks})"
    return sql, [clean[c] for c in CMS_COLUMNS]
