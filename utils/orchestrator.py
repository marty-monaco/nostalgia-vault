"""
utils/orchestrator.py

UniverseOrchestrator: Generates 3 distinct narrative metaphor concepts
from raw curriculum strings using the Gemini API, with optional domain steering.
"""
import json
import time
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
DEFAULT_MODEL       = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.7   # Higher for creative narrative variety
MAX_RETRIES         = 3
RETRY_DELAY_SEC     = 2.0
DEFAULT_DOMAIN      = "Any / Multi-Domain (Default)"

SYSTEM_INSTRUCTION_BASE = (
    "You are an elite Creative Director, Narrative Designer, and Instructional Expert. "
    "Your superpower is transforming complex, high-density curriculum mechanics into "
    "associative schema-mapping metaphors that anchor dry facts to intuitive real-world systems.\n\n"
    "STRICT DOMAIN DIVERSITY RULE: You MUST draw your 3 story concepts from THREE (3) COMPLETELY "
    "DIFFERENT domain categories below. Never repeat a genre. Choose from:\n"
    "1. Sports, Athletics & Professional Leagues (NBA / NFL / MLB Collective Bargaining, Tactical Plays)\n"
    "2. Real-World Logistics & Transport (Airports, Traffic Systems, Shipping, Supply Chains)\n"
    "3. Culinary & Restaurant Dynamics (Kitchen Operations, Recipe Chemistry, Service Trade-offs)\n"
    "4. Natural Systems & Ecology (Forest Mycelium Networks, River Dynamics, Ecosystem Balances)\n"
    "5. Architecture & Construction (Load Balancing, Blueprinting, Foundations vs. Facades)\n"
    "6. History & High-Stakes Diplomacy (Trade Routes, Negotiation Paradoxes, Expeditions)\n"
    "7. Performing Arts & Music (Orchestral Conducting, Stage Management, Film Production)"
)

AUDITION_PROMPT_TEMPLATE = """\
Analyze the following educational material:
---
{raw_curriculum}
---

Based on this material, pitch exactly THREE (3) completely distinct narrative concepts \
or metaphorical worlds that can be used to build a 90-second educational story video.
{domain_directive}
Return ONLY a valid JSON array containing exactly 3 strings. Each string is one complete \
story pitch in markdown. No preamble, no explanation, no text outside the JSON array.

Each story string must follow this structure exactly:
### TITLE: [Story Title]
**Domain Category**: [Domain from the list of 7]
**The Hook / Premise**: [A cinematic, highly intuitive real-world story setup]
**The Core Analogy**: [How the technical mechanics from the text map to this domain]
**The Lift Index**: [Why this domain metaphor drives conceptual mastery]

Output shape (replace placeholder content):
["### TITLE: Story One...full markdown...", "### TITLE: Story Two...full markdown...", \
"### TITLE: Story Three...full markdown..."]
"""


def _build_domain_directive(preferred_domain: str) -> str:
    """Return the domain steering instruction if a non-default domain is selected."""
    if preferred_domain == DEFAULT_DOMAIN:
        return ""
    return (
        f"\nPRIMARY REQUIREMENT: At least ONE of your three pitched concepts MUST be explicitly "
        f"built using the '{preferred_domain}' framework.\n"
    )


class UniverseOrchestrator:
    """Generates 3 narrative metaphor pitches from curriculum text via Gemini.

    Args:
        api_key:     Gemini API key. Use resolve_api_key(st.secrets) from
                     utils.production before passing here.
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
                "from utils.production before instantiating UniverseOrchestrator."
            )
        self.model       = model
        self.temperature = temperature
        self._client     = genai.Client(api_key=api_key)

    # -----------------------------------------------------------------------
    # PUBLIC
    # -----------------------------------------------------------------------

    def audition_metaphors(
        self,
        raw_curriculum: str,
        preferred_domain: str = DEFAULT_DOMAIN,
    ) -> list[str]:
        """Return a list of exactly 3 story pitch strings.

        Args:
            raw_curriculum:   Normalized curriculum text from CurriculumIngestor.
            preferred_domain: Optional domain from DOMAIN_OPTIONS in Page 2.

        Returns:
            list[str] — exactly 3 markdown-formatted story pitch strings.

        Raises:
            ValueError:    Empty curriculum or wrong number of stories returned.
            RuntimeError:  API call failed after MAX_RETRIES attempts.
        """
        if not raw_curriculum or not raw_curriculum.strip():
            raise ValueError("raw_curriculum must not be empty.")

        system_instruction = self._build_system_instruction(preferred_domain)
        prompt             = self._build_prompt(raw_curriculum, preferred_domain)
        raw_text           = self._call_api_with_retry(prompt, system_instruction)
        return self._parse_response(raw_text)

    # -----------------------------------------------------------------------
    # PRIVATE
    # -----------------------------------------------------------------------

    def _build_system_instruction(self, preferred_domain: str) -> str:
        if preferred_domain == DEFAULT_DOMAIN:
            return SYSTEM_INSTRUCTION_BASE
        domain_line = (
            f"PRIMARY USER REQUIREMENT: At least ONE story MUST use the "
            f"'{preferred_domain}' framework.\n\n"
        )
        return domain_line + SYSTEM_INSTRUCTION_BASE

    def _build_prompt(self, raw_curriculum: str, preferred_domain: str) -> str:
        return AUDITION_PROMPT_TEMPLATE.format(
            raw_curriculum=raw_curriculum.strip(),
            domain_directive=_build_domain_directive(preferred_domain),
        )

    def _parse_response(self, raw_text: str) -> list[str]:
        """Parse JSON array from LLM response with delimiter fallback.

        Primary:  JSON array of 3 strings (new prompt format).
        Fallback: legacy '|||' delimiter split (preserves backward compatibility).
        """
        text = raw_text.strip()

        # Primary: JSON array
        try:
            stories = json.loads(text)
            if isinstance(stories, list) and all(isinstance(s, str) for s in stories):
                stories = [s.strip() for s in stories if s.strip()]
                if len(stories) != 3:
                    raise ValueError(
                        f"Expected 3 story pitches, received {len(stories)}. "
                        "Try re-running — this is usually a transient LLM formatting issue."
                    )
                return stories
        except json.JSONDecodeError:
            logger.warning("JSON parse failed — falling back to '|||' delimiter split.")
        except ValueError:
            raise  # Re-raise wrong-count error

        # Fallback: legacy delimiter
        stories = [s.strip() for s in text.split("|||") if s.strip()]
        if not stories:
            raise ValueError("Orchestrator returned no parseable story content.")
        return stories

    def _call_api_with_retry(self, prompt: str, system_instruction: str) -> str:
        """Call Gemini with exponential backoff on transient failures."""
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
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
