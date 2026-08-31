"""
utils/orchestrator.py

UniverseOrchestrator: Generates 3 distinct narrative metaphor concepts
from raw curriculum strings using the Gemini API, with optional domain steering
and support for Direct Narrative (literal storyboarding for YouTube Shorts).
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

DIRECT_NARRATIVE_OPTION = "Direct Narrative / Source-Faithful (Literal Storyboard for YouTube Shorts, No Metaphors)"

# ---------------------------------------------------------------------------
# SYSTEM INSTRUCTIONS & TEMPLATES
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION_METAPHOR = (
    "You are an elite Creative Director, Narrative Designer, and Instructional Expert "
    "who specializes in reaching Gen Z students who have grown up on TikTok, YouTube, "
    "gaming, and streaming culture. Your superpower is transforming complex, high-density "
    "curriculum mechanics into high-engagement metaphors that feel NATIVE to the world "
    "students actually live in — not the world textbooks assume they live in.\n\n"
    "TONE DIRECTIVE: Scripts must feel cinematic, fun, and culturally alive. Avoid corporate "
    "or academic framing. The best metaphors make students feel like insiders, not students.\n\n"
    "STRICT DOMAIN DIVERSITY RULE: You MUST draw your 3 story concepts from THREE (3) COMPLETELY "
    "DIFFERENT domain categories below. Never repeat a genre. Strongly prefer the Gen Z-native "
    "domains (1-7) unless the curriculum topic maps exceptionally well to a classic domain (8-14). "
    "Choose from:\n"
    "\n--- GEN Z NATIVE DOMAINS (strongly preferred) ---\n"
    "1. Gaming & Esports (resource management, skill trees, in-game economies, battle pass "
    "mechanics, team compositions, speedrunning optimization, loot box probability)\n"
    "2. Pop Culture & Celebrity Economy (music chart dynamics, streaming royalties, viral fame "
    "cycles, brand deal hierarchies, fan army mobilization, album rollout strategy, cancel culture "
    "economics)\n"
    "3. Social Media & Creator Economy (algorithm dynamics, follower growth curves, monetization "
    "thresholds, platform switching costs, viral content mechanics, brand vs. audience loyalty, "
    "sponsorship market)\n"
    "4. Sneaker & Streetwear Culture (limited drops, resale market economics, hype cycles, brand "
    "scarcity tactics, collab value, authenticity premiums, StockX/GOAT dynamics)\n"
    "5. Film, TV & Streaming Industry (budget allocation, box office risk, streaming vs. theatrical "
    "economics, sequel IP value, casting markets, franchise building, Netflix vs. studios)\n"
    "6. Fashion & Trend Economics (fast fashion vs. luxury positioning, seasonal cycles, trend "
    "diffusion curves, sustainable trade-offs, influencer-driven demand)\n"
    "7. Space Exploration & Sci-Fi (mission resource constraints, colony economics, interplanetary "
    "trade, risk/reward of exploration, terraforming investment trade-offs)\n"
    "\n--- CLASSIC DOMAINS (use when a strong match exists) ---\n"
    "8. Sports, Athletics & Pro Leagues (salary caps, draft picks, trade deadlines, collective "
    "bargaining, Moneyball analytics, undervalued asset arbitrage)\n"
    "9. Food, Restaurant & Kitchen Dynamics (kitchen operations, franchise vs. independent "
    "economics, recipe chemistry, service trade-offs, food truck vs. restaurant fixed costs)\n"
    "10. History & High-Stakes Cinematic Moments (gold rushes, trade route battles, heists, "
    "expeditions, revolutions — frame as thriller narratives, not academic events)\n"
    "11. Natural Systems & Ecology (forest mycelium networks, predator/prey dynamics, "
    "ecosystem balance, migration patterns, invasive species economics)\n"
    "12. Real-World Logistics & Transport (airports, shipping lanes, last-mile delivery, "
    "supply chain optimization, port economics)\n"
    "13. Urban Planning & City Economics (gentrification dynamics, housing market trade-offs, "
    "infrastructure investment, zoning economics, city growth models)\n"
    "14. Performing Arts & Live Events (concert tour economics, ticket scalping markets, "
    "festival logistics, venue capacity trade-offs, artist vs. label economics)"
)

AUDITION_METAPHOR_TEMPLATE = """\
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
**Domain Category**: [Domain from the list]
**The Hook / Premise**: [A cinematic, highly intuitive real-world story setup]
**The Core Analogy**: [How the technical mechanics from the text map to this domain]
**The Lift Index**: [Why this domain metaphor drives conceptual mastery]

Output shape (replace placeholder content):
["### TITLE: Story One...full markdown...", "### TITLE: Story Two...full markdown...", \
"### TITLE: Story Three...full markdown..."]
"""

SYSTEM_INSTRUCTION_DIRECT = (
    "You are an expert YouTube Shorts director, documentary producer, and visual storyboard artist. "
    "Your superpower is turning dense, complex, or historical source text into thrilling, "
    "fast-paced short-form video story concepts without using metaphors or allegories.\n\n"
    "STRICT DIRECT NARRATIVE DIRECTIVE:\n"
    "1. NO METAPHORS OR ANALOGIES: Extract only the literal events, people, dates, conflicts, "
    "and stakes present in the ingested text.\n"
    "2. FOCUS ON PACING & VISUALS: Pitch 3 distinct directorial angles on the exact same material "
    "(e.g., Angle 1: High-energy character conflict, Angle 2: Chronological thriller/countdown, "
    "Angle 3: Forensic breakdown/mystery).\n"
    "3. AUDIENCE RETENTION: Frame hooks around high stakes, startling facts, or dramatic moments directly from the source."
)

AUDITION_DIRECT_TEMPLATE = """\
Analyze the following source material:
---
{raw_curriculum}
---

Extract the literal events and pitch exactly THREE (3) distinct short-form vertical video (YouTube Shorts) \
narrative treatments based SOLELY on the events, people, dates, and facts in the text. \
DO NOT use metaphors or allegories.

Pitch 3 distinct directorial pacing styles:
1. Dramatic Suspense / Thriller Angle
2. Fast-Paced Action / Chronological Countdown Angle
3. Deep-Dive Mystery / Forensic Reveal Angle

Return ONLY a valid JSON array containing exactly 3 strings. Each string is one complete \
treatment pitch in markdown. No preamble, no explanation, no text outside the JSON array.

Each story string must follow this structure exactly:
### TITLE: [Shorts Video Title]
**Mode**: Direct Narrative (Source-Faithful)
**Visual Style / Pacing**: [e.g., Fast cuts, archival footage look, 9:16 vertical cinema, 5s visual beats]
**The Hook**: [First 3-5 seconds voiceover line and visual opening that stops scrolling]
**Narrative Arc / Beats**: [Sequential breakdown of 3-4 key chronological scenes directly from the text]
**Key Takeaway / Climax**: [The literal historical resolution, punchline, or core insight]

Output shape (replace placeholder content):
["### TITLE: Story One...full markdown...", "### TITLE: Story Two...full markdown...", \
"### TITLE: Story Three...full markdown..."]
"""


def _build_domain_directive(preferred_domain: str) -> str:
    """Return the domain steering instruction if a non-default domain is selected."""
    if preferred_domain in (DEFAULT_DOMAIN, DIRECT_NARRATIVE_OPTION):
        return ""
    return (
        f"\nPRIMARY REQUIREMENT: At least ONE of your three pitched concepts MUST be explicitly "
        f"built using the '{preferred_domain}' framework.\n"
    )


class UniverseOrchestrator:
    """Generates 3 narrative pitches from curriculum text via Gemini.

    Args:
        api_key:      Gemini API key. Use resolve_api_key(st.secrets) from
                      utils.production before passing here.
        model:        Gemini model name. Defaults to DEFAULT_MODEL.
        temperature:  Sampling temperature. Defaults to DEFAULT_TEMPERATURE.
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
        if preferred_domain == DIRECT_NARRATIVE_OPTION:
            return SYSTEM_INSTRUCTION_DIRECT
        if preferred_domain == DEFAULT_DOMAIN:
            return SYSTEM_INSTRUCTION_METAPHOR
        domain_line = (
            f"PRIMARY USER REQUIREMENT: At least ONE story MUST use the "
            f"'{preferred_domain}' framework.\n\n"
        )
        return domain_line + SYSTEM_INSTRUCTION_METAPHOR

    def _build_prompt(self, raw_curriculum: str, preferred_domain: str) -> str:
        if preferred_domain == DIRECT_NARRATIVE_OPTION:
            return AUDITION_DIRECT_TEMPLATE.format(
                raw_curriculum=raw_curriculum.strip()
            )
        return AUDITION_METAPHOR_TEMPLATE.format(
            raw_curriculum=raw_curriculum.strip(),
            domain_directive=_build_domain_directive(preferred_domain),
        )

    def _parse_response(self, raw_text: str) -> list[str]:
        """Parse JSON array from LLM response with delimiter fallback."""
        text = raw_text.strip()

        # Strip markdown code blocks if the model wrapped the JSON array
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

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
            raise

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
                raise

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
