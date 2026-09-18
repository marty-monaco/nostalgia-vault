"""
utils/constants.py

Single source of truth for ALL session state keys used across The Vault CMS.

Rules:
- Every session_state key in the codebase must be defined here.
- Pages import these constants — never use raw string literals for session state.
- One typo here is caught immediately at import; one typo in a page silently
  breaks the pipeline with no error message.

Key naming convention:
  KEY_<STAGE>_<DESCRIPTION>   e.g. KEY_ORCHESTRATOR_PITCHES
  UI_<DESCRIPTION>             e.g. UI_REFINEMENT_FEEDBACK
"""

# ---------------------------------------------------------------------------
# PIPELINE STAGE PAYLOADS
# These are the primary data handoffs between pages.
# ---------------------------------------------------------------------------

# Page 1 → Page 2
KEY_CURRICULUM_PAYLOAD    = "curriculum_payload"

# Page 2 → Page 3 (the selected pitch blueprint)
KEY_ORCHESTRATOR_PITCHES  = "orchestrator_pitches"   # full PitchAuditionResponse object
KEY_ORCHESTRATOR_REPORT   = "orchestrator_report"    # legacy alias — prefer KEY_SELECTED_PITCH
KEY_SELECTED_PITCH        = "selected_metaphor_pitch" # canonical key for the chosen pitch

# Page 3 outputs
KEY_PRODUCTION_PAYLOAD    = "production_payload"      # raw LLM output string
KEY_PROD_SCRIPT           = "prod_script"             # parsed script section
KEY_PROD_MCQS             = "prod_mcqs"               # parsed assessment questions
KEY_PROD_TOPIC            = "prod_topic"              # topic string at time of production
KEY_PROD_PILOT            = "prod_pilot"              # pilot ID at time of production
KEY_RAW_PRODUCTION_OUTPUT = "raw_production_output"   # unprocessed Gemini response
KEY_LAST_GENERATED_METAPHOR = "last_generated_metaphor" # deduplication guard
KEY_VALIDATED_MODULE      = "validated_module"        # psychometrically validated output

# ---------------------------------------------------------------------------
# SHARED UI / NAVIGATION STATE
# ---------------------------------------------------------------------------

KEY_ACTIVE_TOPIC          = "active_topic"            # topic title selected by student/admin
KEY_VAULT_ARCHIVE         = "vault_archive"           # list of archived pitch strings

# ---------------------------------------------------------------------------
# CACHED RUNTIME OBJECTS
# These are expensive-to-create objects cached across reruns.
# ---------------------------------------------------------------------------

KEY_ORCHESTRATOR_INSTANCE = "orchestrator_instance"   # UniverseOrchestrator instance

# ---------------------------------------------------------------------------
# PITCH REFINEMENT STATE (Pages 2 & 5)
# ---------------------------------------------------------------------------

KEY_PITCH_VERSIONS        = "pitch_versions"          # {pitch_idx: [v0, v1, v2, ...]}
KEY_REFINEMENT_HISTORY    = "refinement_history"      # {pitch_idx: [feedback_1, ...]}

# ---------------------------------------------------------------------------
# TRANSIENT UI WIDGET STATE
# Streamlit widget keys — kept here to avoid key collisions between pages.
# ---------------------------------------------------------------------------

UI_REFINEMENT_FEEDBACK    = "refinement_feedback"
UI_CUSTOM_FEEDBACK        = "custom_feedback"
UI_TEMPLATE_FEEDBACK      = "template_feedback"

# ---------------------------------------------------------------------------
# LEGACY ALIASES
# Kept for backward compatibility during migration.
# Do not use in new code — use the canonical key above instead.
# Remove once all pages have been updated.
# ---------------------------------------------------------------------------

_LEGACY_SELECTED_PITCH    = "selected_pitch"          # replaced by KEY_SELECTED_PITCH
