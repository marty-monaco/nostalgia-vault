"""
utils/production.py

ProductionEngine: Wraps the Gemini API to generate an attention-gated video script
(enforcing an 8-second hook) and a calibrated assessment package scaled to specific academic rigor levels.
"""
import os
import time
import logging
import streamlit as st
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

DEFAULT_MODEL       = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.4
MAX_RETRIES         = 3
RETRY_DELAY_SEC     = 2.0

SYSTEM_INSTRUCTION = (
    "You are an expert Instructional Designer, Cognitive Neuroscientist, and Media Producer. "
    "Your job is to take a narrative metaphor concept and build it out into an attention-gated "
    "90-second video script and a calibrated assessment package scaled to the target academic level."
)

BLUEPRINT_PROMPT_TEMPLATE = """\
Using the following Selected Story Blueprint:
---
{creative_report}
---

TARGET AUDIENCE ACADEMIC LEVEL: {academic_level}

Please generate a complete production payload broken into these two specific sections:

### SECTION 1: 90-SECOND RUNNING VIDEO SCRIPT
Write out the script chronologically as a series of scenes. You must strictly follow this temporal attention-gating structure:

* **PHASE 1: THE 8-SECOND ATTENTION HOOK (0:00 - 0:08)**
  * **[VISUAL]**: A highly disruptive, cinematic, or visually shocking scene designed to capture immediate attention. No talking heads or slow text intros.
  * **[AUDIO]**: A compelling hook line, psychological paradox, or dramatic question. CRITICAL: Absolutely no textbook definitions or jargon allowed in these first 8 seconds. Establish curiosity first.

* **PHASE 2: THE METAPHOR MAPPING & EXPOSITION (0:09 - 1:30)**
  * Break this down into sequential scenes (Scene 2, Scene 3, etc.). For each scene, provide:
    * **[VISUAL]**: Clear, vivid instructions for on-screen action, character movements, or background animation changes (optimized for AI video generation).
    * **[AUDIO]**: The exact voiceover text spoken by the narrator. Resolve the tension from the hook by mapping the rules of the story world directly to the underlying technical concepts.

### SECTION 2: CALIBRATED ASSESSMENT PACKAGE
Provide exactly 4 multiple-choice questions (with options A, B, C, D, the correct answer, and a 1-sentence explanation) calibrated specifically for an **{academic_level}** cognitive level:

* **2 Pre-Video Baseline Questions**: Testing the raw concept directly using academic terminology appropriate for {academic_level}.
* **2 Post-Video Conceptual Questions**: High-rigor application questions.
  * If Target Level is "Undergraduate / University Level" or "Advanced Research / Graduate": Apply Bloom's Taxonomy (Analysis & Evaluation). Force the user to weigh competing trade-offs, evaluate mathematical edge cases, or analyze unintended policy consequences through the metaphor.
  * If Target Level is "High School Standard" or "High School AP / Honors": Focus on core conceptual comprehension and direct structural analogy mapping.
"""


def resolve_api_key() -> str:
    """Return the Gemini API key from Streamlit secrets or environment variables."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
        
    return os.environ.get("GEMINI_API_KEY", "")


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

    def generate_blueprint(self, creative_report: str, academic_level: str = "High School Standard") -> str:
        if not creative_report or not creative_report.strip():
            raise ValueError("creative_report must not be empty.")

        prompt = self._build_prompt(creative_report, academic_level)
        return self._call_api_with_retry(prompt)

    def _build_prompt(self, creative_report: str, academic_level: str) -> str:
        return BLUEPRINT_PROMPT_TEMPLATE.format(
            creative_report=creative_report.strip(),
            academic_level=academic_level
        )

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
