"""
utils/orchestrator.py

UniverseOrchestrator: Generates 3 distinct narrative metaphor concepts
from raw curriculum strings using the Gemini API, with optional domain steering
and support for Direct Narrative (literal storyboarding for YouTube Shorts).
"""
import time
import logging
from pydantic import BaseModel, Field
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
# PYDANTIC STRUCTURED OUTPUT CONTRACTS
# ---------------------------------------------------------------------------
class StoryPitch(BaseModel):
    title: str = Field(description="The catchy title of the story or short")
    domain_category: str = Field(description="Domain from the taxonomy or 'Direct Narrative'")
    hook: str = Field(description="The cinematic hook / first 3-5 seconds premise that stops scrolling")
    core_analogy_or_beats: str = Field(description="Mapping of technical mechanics to the domain, or 3-4 chronological story beats")
    lift_index_or_climax: str = Field(description="Why this drives conceptual mastery, or the dramatic resolution/insight")

    def to_markdown_card(self) -> str:
        return (
            f"### TITLE: {self.title}\n"
            f"**Domain Category**: {self.domain_category}\n"
            f"**The Hook / Premise**: {self.hook}\n"
            f"**The Core Analogy**: {self.core_analogy_or_beats}\n"
            f"**The Lift Index**: {self.lift_index_or_climax}"
        )

class PitchAuditionResponse(BaseModel):
    pitches: list[StoryPitch] = Field(
        min_length=3,
        max_length=3,
        description="Exactly 3 completely distinct story concepts"
    )

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
)

SYSTEM_INSTRUCTION_DIRECT = (
    "You are an expert YouTube Shorts director, documentary producer, and visual storyboard artist. "
    "Your superpower is turning dense, complex, or historical source text into thrilling, "
    "fast-paced short-form video story concepts without using metaphors or allegories.\n\n"
    "STRICT DIRECT NARRATIVE DIRECTIVE:\n"
    "1. NO METAPHORS OR ANALOGIES: Extract only the literal events, people, dates, conflicts, and stakes.\n"
    "2. FOCUS ON PACING & VISUALS: Pitch 3 distinct directorial angles on the exact same material "
    "(e.g., Angle 1: High-energy character conflict, Angle 2: Chronological countdown, Angle 3: Forensic reveal).\n"
    "3. AUDIENCE RETENTION: Frame hooks around high stakes, startling facts, or dramatic moments directly from the source."
)

AUDITION_METAPHOR_TEMPLATE = """\
Analyze the following educational material:
