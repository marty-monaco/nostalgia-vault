"""
utils/production.py

ProductionEngine: wraps the Gemini API to generate a 90-second video script
and calibrated assessment package from a narrative metaphor blueprint.
"""
import os
import time
import logging
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
    "You are an expert Instructional Designer and Media Producer. "
    "Your job is to take a narrative metaphor concept and build it out into "
    "a 90-second video script and assessment package."
)

BLUEPRINT_PROMPT_TEMPLATE = """\
Using the following Selected Story Blueprint:
---
{creative_report}
---

Please generate a complete production payload broken into these two specific sections:

### SECTION 1: 90-SECOND RUNNING VIDEO SCRIPT
Write out the script chronologically as a series of scenes (Scene 1, Scene 2, Scene 3, etc.).
For each scene, provide:
* **[VISUAL]**: Clear, vivid instructions for the on-screen action, animations, or scenery \
(perfect for an AI video generator).
* **[AUDIO]**: The exact voiceover text to be spoken by the narrator \
(clear, high-school-appropriate language perfect for voice cloning).

Ensure the story progression tracks perfectly to the underlying financial rules from the source text.

### SECTION 2: CALIBRATED ASSESSMENT PACKAGE
Provide exactly 4 multiple-choice questions \
(with options A, B, C, D, the correct answer, and a 1-sentence explanation):
* **2 Pre-Video Baseline Questions**: Testing the raw financial concept directly \
using clear, textbook terminology.
* **2 Post-Video Conceptual Questions**: Testing mastery *through the lens of the story \
or metaphor* to prove they understand the operational mechanism.
"""


# ---------------------------------------------------------------------------
# API KEY RESOLUTION — single source of truth for the whole app
# ---------------------------------------------------------------------------
def resolve_api_key(streamlit_secrets=None) -> str:
    """Return the Gemini API key from the first available source.

    Priority: Streamlit secrets → environment variable → empty string.
    Pass `st.secrets` as `streamlit_secrets` when calling from a Streamlit page.
    Keeping this here (rather than in each page) means one change covers the app.
    """
    if streamlit_secrets is not None:
        try:
            return streamlit_secrets["GEMINI_API_KEY"]
        except (KeyError, Exception):
            pass
    return os.environ.get("GEMINI_API_KEY", "")


# ---------------------------------------------------------------------------
# ENGINE
# ---------------------------------------------------------------------------
class ProductionEngine:
    """Generates a video script and assessment package via the Gemini API.

    Args:
        api_key:     Gemini API key. Raises ValueError immediately if absent.
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
                "Gemini API key is required. Pass it explicitly or set "
                "GEMINI_API_KEY in Streamlit secrets or the environment."
            )
        self.model       = model
        self.temperature = temperature
        self._client     = genai.Client(api_key=api_key)

    # -----------------------------------------------------------------------
    # PUBLIC
    # -----------------------------------------------------------------------
    def generate_blueprint(self, creative_report: str) -> str:
        """Return a production payload (script + quiz) for the given report.

        Raises:
            ValueError:    Empty or whitespace-only creative_report.
            RuntimeError:  API call failed after MAX_RETRIES attempts.
        """
        if not creative_report or not creative_report.strip():
            raise ValueError("creative_report must not be empty.")

        prompt = self._build_prompt(creative_report)
        return self._call_api_with_retry(prompt)

    # -----------------------------------------------------------------------
    # PRIVATE
    # -----------------------------------------------------------------------
    def _build_prompt(self, creative_report: str) -> str:
        """Render the prompt template — testable without an API call."""
        return BLUEPRINT_PROMPT_TEMPLATE.format(creative_report=creative_report.strip())

    def _call_api_with_retry(self, prompt: str) -> str:
        """Call the Gemini API with exponential backoff on transient failures.

        Raises RuntimeError after MAX_RETRIES exhausted.
        Raises immediately on non-retryable errors (auth, invalid argument).
        """
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
                raise  # Non-retryable — bad input or empty response

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Non-retryable: auth / permission failures
                if any(k in error_str for k in ("api key", "permission", "unauthorized", "invalid argument")):
                    raise RuntimeError(f"Non-retryable API error: {e}") from e

                if attempt < MAX_RETRIES:
                    wait = RETRY_DELAY_SEC * (2 ** (attempt - 1))  # 2s, 4s, 8s
                    logger.warning("Gemini API attempt %d/%d failed (%s). Retrying in %.1fs…",
                                   attempt, MAX_RETRIES, e, wait)
                    time.sleep(wait)

        raise RuntimeError(
            f"Gemini API failed after {MAX_RETRIES} attempts. Last error: {last_error}"
        ) from last_error
