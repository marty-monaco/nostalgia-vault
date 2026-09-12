"""
generate_and_ingest.py

Executes curriculum generation via Gemini and automates schema-validated
ingestion directly into Supabase (TheVault_CMS_Core).
"""

import os
import logging
from google import genai
from google.genai import types
from supabase import create_client, Client

from vault_curriculum_prompts import (
    SYSTEM_PSYCHOMETRIC_INSTRUCTIONS,
    VaultModuleSchema,
    build_module_prompt,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VaultIngestion")

# Initialize Clients
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")  # Use service role key if bypassing RLS
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = genai.Client(api_key=GEMINI_API_KEY)


def generate_vault_module(topic: str, pilot_id: str, learning_objective: str) -> VaultModuleSchema:
    """Invokes Gemini with structured output validation."""
    logger.info(f"Generating module: '{topic}' for pilot '{pilot_id}'...")

    prompt = build_module_prompt(topic, pilot_id, learning_objective)

    response = ai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PSYCHOMETRIC_INSTRUCTIONS,
            response_mime_type="application/json",
            response_schema=VaultModuleSchema,
            temperature=0.2,  # Low temperature for precise psychometric adherence
        ),
    )

    # Automatically deserializes and validates against Pydantic schema
    return response.parsed


def ingest_module_to_supabase(module: VaultModuleSchema, pilot_id: str, video_url: str = "") -> dict:
    """
    Maps validated module schema to TheVault_CMS_Core column structure,
    preventing duplicate column assignment errors.
    """
    logger.info(f"Persisting '{module.topic}' to Supabase table 'TheVault_CMS_Core'...")

    payload = {
        "pilot_id": pilot_id,
        "Topic": module.topic,
        "Video_URL": video_url,
        "Video_Length_Sec": module.video_length_sec,
        
        # Pre-Assessment Q1
        "Pre_Q1": module.pre_q1.question,
        "Pre_Opt1": module.pre_q1.opt1,
        "Pre_Opt2": module.pre_q1.opt2,
        "Pre_Opt3": module.pre_q1.opt3,
        "Pre_A1": module.pre_q1.correct_answer,
        
        # Pre-Assessment Q2 (Enforcing _Q2 suffix)
        "Pre_Q2": module.pre_q2.question,
        "Pre_Opt1_Q2": module.pre_q2.opt1,
        "Pre_Opt2_Q2": module.pre_q2.opt2,
        "Pre_Opt3_Q2": module.pre_q2.opt3,
        "Pre_A2": module.pre_q2.correct_answer,
        
        # Post-Assessment Q1
        "Post_Q1": module.post_q1.question,
        "Post_Opt1": module.post_q1.opt1,
        "Post_Opt2": module.post_q1.opt2,
        "Post_Opt3": module.post_q1.opt3,
        "Post_A1": module.post_q1.correct_answer,
        
        # Post-Assessment Q2 (Enforcing _Q2 suffix)
        "Post_Q2": module.post_q2.question,
        "Post_Opt1_Q2": module.post_q2.opt1,
        "Post_Opt2_Q2": module.post_q2.opt2,
        "Post_Opt3_Q2": module.post_q2.opt3,
        "Post_A2": module.post_q2.correct_answer,
        
        "NPS_Question": "Would you recommend The Vault to a peer?",
    }

    # Upsert based on unique topic and pilot_id
    res = (
        supabase.table("TheVault_CMS_Core")
        .upsert(payload, on_conflict="pilot_id,Topic")
        .execute()
    )
    logger.info("Successfully ingested into TheVault_CMS_Core.")
    return res.data


if __name__ == "__main__":
    # Test Run: Generating a replacement module
    sample_topic = "Desert of Thirst: Price Controls"
    sample_pilot = "WIRAPIDS_12"
    sample_objective = (
        "Demonstrate how legally mandated price ceilings destroy supplier incentives, "
        "causing physical shortages and black markets rather than equitable distribution."
    )

    # 1. Generate with psychometric constraints
    generated_data = generate_vault_module(
        topic=sample_topic,
        pilot_id=sample_pilot,
        learning_objective=sample_objective,
    )

    # 2. Ingest into Supabase
    ingest_module_to_supabase(
        module=generated_data,
        pilot_id=sample_pilot,
        video_url="https://youtube.com/shorts/w5kCRb99CFA",
    )
