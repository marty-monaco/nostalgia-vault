"""
Utils/generate_and_ingest.py

Executes curriculum generation via Gemini and automates schema-validated
ingestion directly into Supabase (TheVault_CMS_Core).
"""
import os
import sys
import logging
from google import genai
from google.genai import types
from supabase import create_client, Client

from utils.vault_curriculum_prompts import (
    SYSTEM_PSYCHOMETRIC_INSTRUCTIONS,
    VaultModuleSchema,
    build_module_prompt,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VaultIngestion")


def _resolve_secret(key_name: str, nested_section: str = None) -> str | None:
    """Safely retrieves credentials from st.secrets or os.environ."""
    try:
        import streamlit as st
        if nested_section and nested_section in st.secrets:
            val = st.secrets[nested_section].get(key_name)
            if val:
                return str(val).strip()
        val = st.secrets.get(key_name)
        if val:
            return str(val).strip()
    except Exception:
        pass
    val = os.environ.get(key_name)
    return str(val).strip() if val else None


def get_supabase_client() -> Client:
    url = _resolve_secret("SUPABASE_URL", "supabase")
    key = _resolve_secret("SUPABASE_KEY", "supabase")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in secrets/environment.")
    return create_client(url, key)


def get_gemini_client() -> genai.Client:
    api_key = _resolve_secret("GEMINI_API_KEY")
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


def ingest_module_to_supabase(module: VaultModuleSchema, pilot_id: str, video_url: str = "") -> dict:
    """Maps validated schema to TheVault_CMS_Core column structure."""
    clean_topic = module.topic.strip()
    clean_pilot = pilot_id.strip()
    logger.info("Persisting '%s' to TheVault_CMS_Core...", clean_topic)

    payload = {
        "pilot_id": clean_pilot,
        "Topic": clean_topic,
        "Video_URL": (video_url or "").strip(),
        "Video_Length_Sec": int(module.video_length_sec),
        "Pre_Q1": module.pre_q1.question.strip(),
        "Pre_Opt1": module.pre_q1.opt1.strip(),
        "Pre_Opt2": module.pre_q1.opt2.strip(),
        "Pre_Opt3": module.pre_q1.opt3.strip(),
        "Pre_A1": module.pre_q1.correct_answer.strip(),
        "Pre_Q2": module.pre_q2.question.strip(),
        "Pre_Opt1_Q2": module.pre_q2.opt1.strip(),
        "Pre_Opt2_Q2": module.pre_q2.opt2.strip(),
        "Pre_Opt3_Q2": module.pre_q2.opt3.strip(),
        "Pre_A2": module.pre_q2.correct_answer.strip(),
        "Post_Q1": module.post_q1.question.strip(),
        "Post_Opt1": module.post_q1.opt1.strip(),
        "Post_Opt2": module.post_q1.opt2.strip(),
        "Post_Opt3": module.post_q1.opt3.strip(),
        "Post_A1": module.post_q1.correct_answer.strip(),
        "Post_Q2": module.post_q2.question.strip(),
        "Post_Opt1_Q2": module.post_q2.opt1.strip(),
        "Post_Opt2_Q2": module.post_q2.opt2.strip(),
        "Post_Opt3_Q2": module.post_q2.opt3.strip(),
        "Post_A2": module.post_q2.correct_answer.strip(),
        "NPS_Question": "Would you recommend The Vault to a peer?",
    }

    supabase = get_supabase_client()
    res = supabase.table("TheVault_CMS_Core").upsert(payload, on_conflict="pilot_id,Topic").execute()
    logger.info("Successfully upserted '%s' into Supabase.", clean_topic)
    return res.data
