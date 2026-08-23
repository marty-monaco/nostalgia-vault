"""
utils/constants.py

Single source of truth for all session state keys used across pages.
Import these instead of typing string literals — one typo here is caught
immediately; one typo in a page silently breaks the pipeline.
"""

# Pipeline stage payloads
KEY_CURRICULUM_PAYLOAD   = "curriculum_payload"
KEY_ORCHESTRATOR_PITCHES = "orchestrator_pitches"
KEY_ORCHESTRATOR_REPORT  = "orchestrator_report"
KEY_PRODUCTION_PAYLOAD   = "production_payload"

# UI state
KEY_VAULT_ARCHIVE        = "vault_archive"
