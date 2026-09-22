"""
utils/generate_and_ingest.py

Curriculum generation via Gemini and schema-validated ingestion into Supabase
(TheVault_CMS_Core).

Library module: no CLI entry point and no import-time side effects. Whoever
imports it (a Streamlit page, a notebook) decides how logging is configured.
Credentials come from utils.config; the row schema comes from utils.export_helpers.
"""
import logging

from google import genai
from google.genai import types
from supabase import create_client, Client

from utils.config import resolve_gemini_key, resolve_supabase_credentials
from utils.export_helpers import CMS_TABLE, validate_cms_row
from utils.vault_curriculum_prompts import (
    SYSTEM_PSYCHOMETRIC_INSTRUCTIONS,
    VaultModuleSchema,
    build_module_prompt,
)

logger = logging.getLogger("VaultIngestion")


def get_supabase_client() -> Client:
    url, key = resolve_supabase_credentials()
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in secrets/environment.")
    return create_client(url, key)


def get_gemini_client() -> genai.Client:
    api_key = resolve_gemini_key()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY in secrets/environment.")
    return genai.Client(api_key=api_key)


def generate_vault_module(topic: str, pilot_id: str, learning_objective: str) -> VaultModuleSchema:
    """Invokes Gemini with structured schema output and bounded thinking tokens."""
    logger.info("Generating module: '%s' for pilot '%s'...", topic, pilot_id)

    ai_client = get_gemini_client()
    prompt = build_module_prompt(topic, pilot_id, learning_objective)

    response = ai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PSYCHOMETRIC_INSTRUCTIONS,
            response_mime_type="application/json",
            response_schema=VaultModuleSchema,
            temperature=0.2,
            max_output_tokens=3000,
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
        ),
    )

    if not response.parsed:
        raise ValueError("Gemini returned an empty or unparseable schema response.")
    return response.parsed


def _verified_answer(q, label: str) -> str:
    """
    Return q.correct_answer, stripped, after checking it verbatim-matches one of
    the question's three options (the schema's own documented contract).

    Gemini's structured output enforces the schema's *shape* — three option
    strings and a correct_answer string all exist — but nothing enforces that
    correct_answer's text actually equals one of the options. Silently
    ingesting a mismatch would ship a question no option can answer correctly.
    """
    options = {q.opt1.strip(), q.opt2.strip(), q.opt3.strip()}
    answer = q.correct_answer.strip()
    if answer not in options:
        raise ValueError(
            f"{label}: correct_answer {answer!r} does not verbatim-match any of "
            f"opt1/opt2/opt3 {sorted(options)!r}. Refusing to ingest a question "
            "with no correct option."
        )
    return answer


def ingest_module_to_supabase(module: VaultModuleSchema, pilot_id: str, video_url: str = "") -> list[dict]:
    """Maps the validated schema to TheVault_CMS_Core and upserts it (returns the stored rows)."""
    clean_topic = module.topic.strip()
    clean_pilot = pilot_id.strip()
    logger.info("Persisting '%s' to %s...", clean_topic, CMS_TABLE)

    payload = {
        "pilot_id": clean_pilot,
        "Topic": clean_topic,
        "Video_URL": (video_url or "").strip(),
        "Video_Length_Sec": int(module.video_length_sec),
        "Pre_Q1": module.pre_q1.question.strip(),
        "Pre_Opt1": module.pre_q1.opt1.strip(),
        "Pre_Opt2": module.pre_q1.opt2.strip(),
        "Pre_Opt3": module.pre_q1.opt3.strip(),
        "Pre_A1": _verified_answer(module.pre_q1, "pre_q1"),
        "Pre_Q2": module.pre_q2.question.strip(),
        "Pre_Opt1_Q2": module.pre_q2.opt1.strip(),
        "Pre_Opt2_Q2": module.pre_q2.opt2.strip(),
        "Pre_Opt3_Q2": module.pre_q2.opt3.strip(),
        "Pre_A2": _verified_answer(module.pre_q2, "pre_q2"),
        "Post_Q1": module.post_q1.question.strip(),
        "Post_Opt1": module.post_q1.opt1.strip(),
        "Post_Opt2": module.post_q1.opt2.strip(),
        "Post_Opt3": module.post_q1.opt3.strip(),
        "Post_A1": _verified_answer(module.post_q1, "post_q1"),
        "Post_Q2": module.post_q2.question.strip(),
        "Post_Opt1_Q2": module.post_q2.opt1.strip(),
        "Post_Opt2_Q2": module.post_q2.opt2.strip(),
        "Post_Opt3_Q2": module.post_q2.opt3.strip(),
        "Post_A2": _verified_answer(module.post_q2, "post_q2"),
        "NPS_Question": "Would you recommend The Vault to a peer?",
    }

    # Same schema gate the Produce page uses: exact column set, cleaned values.
    payload = validate_cms_row(payload)

    supabase = get_supabase_client()
    res = supabase.table(CMS_TABLE).upsert(payload, on_conflict="pilot_id,Topic").execute()
    logger.info("Successfully upserted '%s' into Supabase.", clean_topic)
    return res.data
