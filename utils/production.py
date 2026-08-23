"""
utils/production.py

ProductionEngine: Wraps the Gemini API to generate an attention-gated video script
(enforcing an 8-second hook) and a calibrated assessment package dynamically mapped
to 4 distinct Bloom's Taxonomy academic rigor levels.
"""
import os
import time
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
DEFAULT_MODEL       = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.4
MAX_RETRIES         = 3
RETRY_DELAY_SEC     = 2.0

SYSTEM_INSTRUCTION = (
    "You are an expert Instructional Designer, Cognitive Neuroscientist, and Media Producer. "
    "Your job is to take a narrative metaphor concept and build it out into an attention-gated "
    "90-second video script and a calibrated assessment package precisely tuned to the target academic level."
)

BLUEPRINT_PROMPT_TEMPLATE = """\
Using the following Selected Story Blueprint:
---
{creative_report}
---

TARGET COGNITIVE RIGOR LEVEL: {academic_level}

Please generate a complete production payload broken into these two specific sections:

### SECTION 1: 90-SECOND RUNNING VIDEO SCRIPT
Write out the script chronologically using this temporal structure:

* **PHASE 1: THE 8-SECOND ATTENTION HOOK (0:00 - 0:08)**
  * **[VISUAL]**: A highly disruptive, cinematic, or visually shocking scene. No talking heads or slow text intros.
  * **[AUDIO]**: A compelling hook line, psychological paradox, or dramatic question. \
CRITICAL: No textbook definitions or jargon in these first 8 seconds. Establish curiosity first.

* **PHASE 2: THE METAPHOR MAPPING & EXPOSITION (0:09 - 1:30)**
  Sequential scenes (Scene 2, Scene 3, etc.). For each scene, provide:
  * **[VISUAL]**: Vivid instructions for on-screen action, character movements, or animation changes.
  * **[AUDIO]**: Voiceover resolving the hook by mapping the story world's rules to the technical concept.

### SECTION 2: CALIBRATED ASSESSMENT PACKAGE
Provide exactly 4 multiple-choice questions (options A, B, C, D; correct answer; 1-sentence explanation) \
STRICTLY calibrated to: **{academic_level}**.

* **2 Pre-Video Baseline Questions**: Testing the core academic concept directly.
* **2 Post-Video Conceptual Questions**: Testing metaphor mapping and application.

**RIGOR-SPECIFIC CALIBRATION:**
* **High School Standard**: Basic term definitions and simple recall. Clear right/wrong answers.
* **High School AP / Honors**: Direct structural mapping (e.g., "In the metaphor, what does X represent?"). \
Functional understanding without complex edge cases.
* **Undergraduate / University Level**: First-order consequences, equilibrium shifts, direct strategic trade-offs.
* **Advanced Research / Graduate**: High cognitive complexity — weigh competing long-term incentives, \
macroeconomic shocks, mathematical edge cases, or unintended system consequences. Distractors must be highly plausible.
"""


# ---------------------------------------------------------------------------
# API KEY RESOLUTION — single source of truth for the whole app
# ---------------------------------------------------------------------------

def resolve_api_key(secrets=None) -> str:
    """Return the Gemini API key from the first available source.

    Priority: Streamlit secrets → environment variable → empty string.

    Args:
        secrets: Pass st.secrets from the calling page. Keeping this parameter
                 explicit prevents a Streamlit import in this util file, making
                 the engine testable outside a Streamlit context.
    """
    if secrets is not None:
        try:
            return secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass
    return os.environ.get("GEMINI_API_KEY", "")


# ---------------------------------------------------------------------------
# ENGINE
# ---------------------------------------------------------------------------

class ProductionEngine:
    """Generates a video script and assessment package via the Gemini API.

    Args:
        api_key:     Gemini API key. Use resolve_api_key(st.secrets) before passing here.
        model:       Gemini model name. Defaults to DEFAULT_MODEL.
        temperature: Sampling temperature. Defaults to DEFAULT_TEMPERATURE.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        if not api_key:
            raise ValueError(
                "Gemini API key is required. Use resolve_api_key(st.secrets) "
                "from utils.production before instantiating ProductionEngine."
            )
        self.model       = model
        self.temperature = temperature
        self._client     = genai.Client(api_key=api_key)

    # -----------------------------------------------------------------------
    # PUBLIC
    # -----------------------------------------------------------------------

    def generate_blueprint(self, creative_report: str, academic_level: str) -> str:
        """Return a production payload (8-second hooked script + calibrated quiz).

        Args:
            creative_report: Story blueprint string from UniverseOrchestrator.
            academic_level:  One of the 4 rigor levels from ACADEMIC_LEVELS in Page 3.

        Raises:
            ValueError:    Empty creative_report.
            RuntimeError:  API call failed after MAX_RETRIES attempts.
        """
        if not creative_report or not creative_report.strip():
            raise ValueError("creative_report must not be empty.")
        if not academic_level or not academic_level.strip():
            raise ValueError("academic_level must not be empty.")

        prompt = BLUEPRINT_PROMPT_TEMPLATE.format(
            creative_report=creative_report.strip(),
            academic_level=academic_level,
        )
        return self._call_api_with_retry(prompt)

    # -----------------------------------------------------------------------
    # PRIVATE
    # -----------------------------------------------------------------------

    def _call_api_with_retry(self, prompt: str) -> str:
        """Call Gemini with exponential backoff on transient failures."""
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
                raise  # Non-retryable

            except Exception as e:
                last_error = e
                error_str  = str(e).lower()

                if any(k in error_str for k in ("api key", "permission", "unauthorized", "invalid argument")):
                    raise RuntimeError(f"Non-retryable API error: {e}") from e

                if attempt < MAX_RETRIES:
                    wait = RETRY_DELAY_SEC * (2 ** (attempt - 1))
                    logger.warning(
                        "Gemini attempt %d/%d failed (%s). Retrying in %.1fs…",
                        attempt, MAX_RETRIES, e, wait,
                    )
                    time.sleep(wait)

        raise RuntimeError(
            f"Gemini API failed after {MAX_RETRIES} attempts. Last error: {last_error}"
        ) from last_error
