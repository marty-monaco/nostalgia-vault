"""
utils/production.py

ProductionEngine: wraps the Gemini API to generate an attention-gated video script
(with a strict 8-second hook) and calibrated assessment package from a blueprint.
"""
import os
import time
import logging
import streamlit as st
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONSTANTS — tunable without touching method logic
# ---------------------------------------------------------------------------
DEFAULT_MODEL       = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.4   # Balanced for formatting stability
MAX_RETRIES         = 3
RETRY_DELAY_SEC     = 2.0

SYSTEM_INSTRUCTION = (
    "You are an expert Instructional Designer, Cognitive Neuroscientist, and Media Producer. "
    "Your job is to take a narrative metaphor concept and build it out into an attention-gated "
    "90-second video script and a calibrated assessment package."
)

BLUEPRINT_PROMPT_TEMPLATE = """\\
Using the following Selected Story Blueprint:
---
{creative_report}
---

Please generate a complete production payload broken into these two specific sections:

### SECTION 1: 90-SECOND RUNNING VIDEO SCRIPT
Write out the script chronologically as a series of scenes. You must strictly follow this temporal attention-gating structure:

* **PHASE 1: THE 8-SECOND ATTENTION HOOK (0:00 - 0:08)**
  * **[VISUAL]**: A highly disruptive, cinematic, or visually shocking scene designed to capture a teenager's attention instantly. No talking heads or slow text intros.
  * **[AUDIO]**: A compelling hook line, psychological paradox, or dramatic question. CRITICAL: Absolutely no textbook definitions, jargon, or technical terms are allowed in these first 8 seconds. Establish curiosity first.

* **PHASE 2: THE METAPHOR MAPPING & EXPOSITION (0:09 - 1:30)**
  * Break this down into sequential scenes (Scene 2, Scene 3, etc.). For each scene, provide:
    * **[VISUAL]**: Clear, vivid instructions for the on-screen action, character movements, or background animation changes (perfect for an AI video generator like Kling or Runway).
    * **[AUDIO]**: The exact voiceover text spoken by the narrator. Resolve the tension from the hook by mapping the rules of the story world directly to the underlying financial/technical concepts. Keep the language highly engaging and tuned for clear voice cloning.

### SECTION 2: CALIBRATED ASSESSMENT PACKAGE
Provide exactly 4 multiple-choice questions (with options A, B, C, D, the correct answer, and a 1-sentence explanation):
* **2 Pre-Video Baseline Questions**: Testing the raw technical/financial concept directly using clear, textbook terminology.
* **2 Post-Video Conceptual Questions**: Testing true conceptual mastery *through the lens of the story or metaphor* to prove they understand how the mechanism operates.
"""


# ---------------------------------------------------------------------------
# API KEY RESOLUTION
# ---------------------------------------------------------------------------
def resolve_api_key() -> str:
    """Return the Gemini API key from the first available source.
    Priority: Streamlit secrets → environment variable → empty string.
    """
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
        
    return os.environ.get("GEMINI_API_KEY", "")


# ---------------------------------------------------------------------------
# ENGINE
# ---------------------------------------------------------------------------
class ProductionEngine:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        if not api_key:
            raise ValueError(
                "Gemini API key is required. Pass it explicitly or set "
                "GEMINI_API_KEY in Streamlit secrets or the environment."
            )
        self.model       = model
        self.temperature = temperature
        self._client     = genai.Client(api_key=api_key)

    def generate_blueprint(self, creative_report: str) -> str:
        if not creative_report or not creative_report.strip():
            raise ValueError("creative_report must not be empty.")

        prompt = self._build_prompt(creative_report)
        return self._call_api_with_retry(prompt)

    def _build_prompt(self, creative_report: str) -> str:
        return BLUEPRINT_PROMPT_TEMPLATE.format(creative_report=creative_report.strip())

    def _call_api_with_retry(self, prompt: str) -> str:
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=self.temperature,
                    ),
                )
                text = response.text
                if not text or not text.strip():
                    raise ValueError("Gemini returned an empty response.")
                return text

            except ValueError:
                raise

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if any(k in error_str for k in ("api key", "permission", "unauthorized", "invalid argument")):
                    raise RuntimeError(f"Non-retryable API error: {e}") from e

                if attempt < MAX_RETRIES:
                    wait = RETRY_DELAY_SEC * (2 ** (attempt - 1))
                    logger.warning("Gemini API attempt %d/%d failed (%s). Retrying in %.1fs…",
                                   attempt, MAX_RETRIES, e, wait)
                    time.sleep(wait)

        raise RuntimeError(
            f"Gemini API failed after {MAX_RETRIES} attempts. Last error: {last_error}"
        ) from last_error
