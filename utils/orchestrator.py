"""
utils/orchestrator.py

UniverseOrchestrator: Generates 3 distinct narrative metaphor concepts
from raw curriculum strings using the Gemini API, with optional domain steering
and support for Direct Narrative (literal storyboarding for YouTube Shorts)[cite: 1].
"""
import time
import logging
from typing import Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ===========================================================================
# CONSTANTS
# ===========================================================================
DEFAULT_MODEL       = "gemini-2.5-flash"[cite: 1]
DEFAULT_TEMPERATURE = 0.7   # Higher for creative narrative variety[cite: 1]
MAX_RETRIES         = 3[cite: 1]
RETRY_DELAY_SEC     = 2.0[cite: 1]
DEFAULT_DOMAIN      = "Any / Multi-Domain (Default)"[cite: 1]

DIRECT_NARRATIVE_OPTION = "Direct Narrative / Source-Faithful (Literal Storyboard for YouTube Shorts, No Metaphors)"[cite: 1]

# ===========================================================================
# PYDANTIC STRUCTURED OUTPUT CONTRACTS
# ===========================================================================
class StoryPitch(BaseModel):
    title: str = Field(description="The catchy title of the story or short")[cite: 1]
    domain_category: str = Field(description="Domain from the taxonomy or 'Direct Narrative'")[cite: 1]
    hook: str = Field(description="The cinematic hook / first 3-5 seconds premise that stops scrolling")[cite: 1]
    core_analogy_or_beats: str = Field(description="Mapping of technical mechanics to the domain, or 3-4 chronological story beats")[cite: 1]
    lift_index_or_climax: str = Field(description="Why this drives conceptual mastery, or the dramatic resolution/insight")[cite: 1]

    def to_markdown_card(self) -> str:
        return (
            f"### TITLE: {self.title}\n"
            f"**Domain Category**: {self.domain_category}\n"
            f"**The Hook / Premise**: {self.hook}\n"
            f"**The Core Analogy**: {self.core_analogy_or_beats}\n"
            f"**The Lift Index**: {self.lift_index_or_climax}"
        )[cite: 1]

class PitchAuditionResponse(BaseModel):
    pitches: list[StoryPitch] = Field(
        min_length=3,
        max_length=3,
        description="Exactly 3 completely distinct story concepts"
    )[cite: 1]

# ===========================================================================
# SYSTEM INSTRUCTIONS & TEMPLATES
# ===========================================================================
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
    "1. Gaming & Esports (resource management, skill trees, in-game economies, battle pass mechanics)\n"
    "2. Pop Culture & Celebrity Economy (music chart dynamics, streaming royalties, viral fame cycles)\n"
    "3. Social Media & Creator Economy (algorithm dynamics, follower growth curves, monetization thresholds)\n"
    "4. Sneaker & Streetwear Culture (limited drops, resale market economics, hype cycles, brand scarcity tactics)\n"
    "5. Film, TV & Streaming Industry (budget allocation, box office risk, streaming vs. theatrical economics)\n"
    "6. Fashion & Trend Economics (fast fashion vs. luxury positioning, seasonal cycles, trend diffusion)\n"
    "7. Space Exploration & Sci-Fi (mission resource constraints, colony economics, interplanetary trade)\n"
    "\n--- CLASSIC DOMAINS (use when a strong match exists) ---\n"
    "8. Sports, Athletics & Pro Leagues (salary caps, draft picks, trade deadlines, Moneyball analytics)\n"
    "9. Food, Restaurant & Kitchen Dynamics (kitchen operations, franchise vs. independent economics)\n"
    "10. History & High-Stakes Moments (gold rushes, trade route battles, heists, revolutions)\n"
    "11. Natural Systems & Ecology (forest mycelium networks, predator/prey dynamics, ecosystem balance)\n"
    "12. Real-World Logistics & Transport (airports, shipping lanes, last-mile delivery, supply chains)\n"
    "13. Urban Planning & City Economics (gentrification dynamics, housing market trade-offs, zoning)\n"
    "14. Performing Arts & Live Events (concert tour economics, ticket scalping, festival logistics)"
)[cite: 1]

SYSTEM_INSTRUCTION_DIRECT = (
    "You are an expert YouTube Shorts director, documentary producer, and visual storyboard artist. "
    "Your superpower is turning dense, complex, or historical source text into thrilling, "
    "fast-paced short-form video story concepts without using metaphors or allegories.\n\n"
    "STRICT DIRECT NARRATIVE DIRECTIVE:\n"
    "1. NO METAPHORS OR ANALOGIES: Extract only the literal events, people, dates, conflicts, and stakes.\n"
    "2. FOCUS ON PACING & VISUALS: Pitch 3 distinct directorial angles on the exact same material "
    "(e.g., Angle 1: High-energy character conflict, Angle 2: Chronological countdown, Angle 3: Forensic reveal).\n"
    "3. AUDIENCE RETENTION: Frame hooks around high stakes, startling facts, or dramatic moments directly from the source."
)[cite: 1]

AUDITION_METAPHOR_TEMPLATE = (
    "Analyze the following educational material:\n\n"
    "---\n{curriculum_text}\n---\n\n"
    "Generate exactly three (3) distinct story pitches that transform these underlying mechanics into engaging narrative metaphors.\n"
    "Domain Steering Instruction: {domain_instruction}\n"
)

AUDITION_DIRECT_TEMPLATE = (
    "Analyze the following educational source material:\n\n"
    "---\n{curriculum_text}\n---\n\n"
    "Generate exactly three (3) distinct YouTube Shorts storyboard concepts that depict these events or concepts directly and literally, without using metaphors or allegories.\n"
    "Directorial Focus: {domain_instruction}\n"
)

# ===========================================================================
# ORCHESTRATOR CLASS
# ===========================================================================
class UniverseOrchestrator:
    """Orchestrates structured conceptual auditions from curriculum text."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        if not api_key:
            raise ValueError("An API key is required to initialize UniverseOrchestrator.")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def audition_pitches(
        self,
        curriculum_text: Optional[str] = None,
        raw_curriculum: Optional[str] = None,
        domain_choice: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> PitchAuditionResponse:
        """Calls Gemini with structured outputs to return 3 distinct story concepts."""
        text = (
            curriculum_text
            or raw_curriculum
            or kwargs.get("text")
            or kwargs.get("curriculum")
            or kwargs.get("content")
        )
        if not text:
            raise ValueError("No curriculum text provided to audition.")

        domain = (
            domain_choice
            or kwargs.get("domain")
            or kwargs.get("selected_domain")
            or DEFAULT_DOMAIN
        )

        temp = (
            temperature
            if temperature is not None
            else kwargs.get("temp", DEFAULT_TEMPERATURE)
        )

        is_direct = (domain == DIRECT_NARRATIVE_OPTION)

        if is_direct:
            system_instruction = SYSTEM_INSTRUCTION_DIRECT
            domain_instruction = "Direct visual storyboards with high narrative pacing and literal fidelity."
            prompt = AUDITION_DIRECT_TEMPLATE.format(
                curriculum_text=text,
                domain_instruction=domain_instruction
            )
        else:
            system_instruction = SYSTEM_INSTRUCTION_METAPHOR
            if domain == DEFAULT_DOMAIN:
                domain_instruction = "Draw from 3 completely different domains with preference for Gen Z native categories."
            else:
                domain_instruction = f"Prioritize concepts aligned with or inspired by: {domain}."
            prompt = AUDITION_METAPHOR_TEMPLATE.format(
                curriculum_text=text,
                domain_instruction=domain_instruction
            )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temp,
            response_mime_type="application/json",
            response_schema=PitchAuditionResponse
        )

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config
                )
                if response.parsed:
                    return response.parsed
                raise ValueError("Model response did not contain structured parsed data.")
            except Exception as e:
                last_error = e
                logger.warning("Audition pitch attempt %d/%d failed: %s", attempt, MAX_RETRIES, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SEC * attempt)

        raise RuntimeError(f"Failed to generate story audition pitches after {MAX_RETRIES} attempts: {last_error}")

    def audition_metaphors(
        self,
        curriculum_text: Optional[str] = None,
        raw_curriculum: Optional[str] = None,
        domain_choice: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> PitchAuditionResponse:
        """Backward-compatible alias resolving all argument patterns."""
        return self.audition_pitches(
            curriculum_text=curriculum_text,
            raw_curriculum=raw_curriculum,
            domain_choice=domain_choice,
            temperature=temperature,
            **kwargs
        )
