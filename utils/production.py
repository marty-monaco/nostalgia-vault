"""
production.py

Core Story & Curriculum Production Pipeline for The Vault.
Coordinates narrative scripting, metadata synthesis, psychometrically guarded
assessment item generation, and automated publishing to TheVault_CMS_Core.
"""

import os
import sys
import logging
import argparse
from typing import Optional, Dict, Any

# Ensure project root / utils is resolvable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.vault_curriculum_prompts import VaultModuleSchema
from utils.generate_and_ingest import generate_vault_module, ingest_module_to_supabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("VaultProduction")


class VaultProductionPipeline:
    """Manages the creation, psychometric calibration, and DB synchronization of Vault modules."""

    def __init__(self, default_pilot_id: str = "WIRAPIDS_12"):
        self.default_pilot_id = default_pilot_id

    def produce_and_publish(
        self,
        topic: str,
        learning_objective: str,
        video_url: str = "",
        pilot_id: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Executes the generation pipeline:
        1. Synthesizes an 85s narrative micro-doc script.
        2. Generates pre-test items calibrated against ceiling effects.
        3. Generates post-test items strictly anchored to the narrative without domain jumps.
        4. Ingests the validated record into TheVault_CMS_Core.
        """
        target_pilot = pilot_id or self.default_pilot_id
        logger.info(f"Initiating production run for Topic: '{topic}' | Pilot: '{target_pilot}'")

        # Step 1 & 2: Generate schema-validated module via Gemini
        try:
            module_schema: VaultModuleSchema = generate_vault_module(
                topic=topic,
                pilot_id=target_pilot,
                learning_objective=learning_objective
            )
            logger.info("Successfully synthesized script and calibrated assessment items.")
        except Exception as e:
            logger.error(f"Generation failure during prompt synthesis: {e}")
            raise RuntimeError(f"Pipeline failed at generation stage: {e}") from e

        # Self-Verification / Psychometric Sanity Check
        self._audit_psychometrics(module_schema)

        if dry_run:
            logger.info("Dry run enabled. Skipping database ingestion.")
            return {
                "status": "dry_run_success",
                "module_data": module_schema.model_dump()
            }

        # Step 3: Ingest into Supabase
        try:
            db_records = ingest_module_to_supabase(
                module=module_schema,
                pilot_id=target_pilot,
                video_url=video_url
            )
            logger.info(f"Pipeline complete. Ingested into TheVault_CMS_Core for '{target_pilot}'.")
            return {
                "status": "published",
                "topic": topic,
                "pilot_id": target_pilot,
                "db_records": db_records
            }
        except Exception as e:
            logger.error(f"Database insertion failed: {e}")
            raise RuntimeError(f"Pipeline failed at Supabase ingestion: {e}") from e

    def _audit_psychometrics(self, schema: VaultModuleSchema) -> None:
        """Runs rule-based checks on generated items to prevent known regressions."""
        # Check Pre-test definitions ban
        banned_stems = ["what is ", "define ", "which best describes the definition"]
        for q_idx, q in [("Pre_Q1", schema.pre_q1), ("Pre_Q2", schema.pre_q2)]:
            stem_lower = q.question.lower()
            if any(b in stem_lower for b in banned_stems):
                logger.warning(
                    f"⚠️ Psychometric Warning [{q_idx}]: Question stem appears definitional: '{q.question}'. "
                    "May induce ceiling effect."
                )

        # Confirm answer options match declared correct keys with case-insensitive fallback
        for q_name, q in [
            ("Pre_Q1", schema.pre_q1), ("Pre_Q2", schema.pre_q2),
            ("Post_Q1", schema.post_q1), ("Post_Q2", schema.post_q2)
        ]:
            opts = [q.opt1.strip(), q.opt2.strip(), q.opt3.strip()]
            correct_norm = q.correct_answer.strip()
            if correct_norm not in opts:
                matched = next((o for o in opts if o.lower() == correct_norm.lower()), None)
                if matched:
                    q.correct_answer = matched
                else:
                    raise ValueError(
                        f"Integrity Error in {q_name}: Declared correct answer '{q.correct_answer}' "
                        f"does not match any option {opts}."
                    )


# ---------------------------------------------------------------------------
# CLI INTERFACE
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="The Vault Story Production & Ingestion Pipeline")
    parser.add_argument("--topic", type=str, required=True, help="Topic title (e.g., 'Desert of Thirst')")
    parser.add_argument("--objective", type=str, required=True, help="Core economic mechanism and misconception")
    parser.add_argument("--video_url", type=str, default="", help="YouTube watch/short URL or CDN stream link")
    parser.add_argument("--pilot", type=str, default="WIRAPIDS_12", help="Target Pilot ID")
    parser.add_argument("--dry_run", action="store_true", help="Generate and audit without saving to database")

    args = parser.parse_args()

    pipeline = VaultProductionPipeline(default_pilot_id=args.pilot)
    result = pipeline.produce_and_publish(
        topic=args.topic,
        learning_objective=args.objective,
        video_url=args.video_url,
        pilot_id=args.pilot,
        dry_run=args.dry_run
    )

    print("\n--- Production Run Summary ---")
    print(f"Status: {result['status']}")
    if args.dry_run:
        print(f"Script: {result['module_data']['video_script']}")
        print(f"Pre Q1: {result['module_data']['pre_q1']['question']}")
        print(f"Post Q1: {result['module_data']['post_q1']['question']}")
    else:
        print(f"Successfully published '{args.topic}' for pilot '{args.pilot}'.")


if __name__ == "__main__":
    main()
