"""
utils/orchestrator.py

UniverseOrchestrator: Generates 3 distinct narrative metaphor concepts
from raw curriculum strings using the Gemini API, with optional domain steering
and support for Direct Narrative (literal storyboarding for YouTube Shorts).

Extended with helper methods for pitch analysis, comparison, refinement, and metadata extraction.
"""
import time
import logging
import json
import re
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ===========================================================================
# CONSTANTS
# ===========================================================================
DEFAULT_MODEL       = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.7   # Higher for creative narrative variety
MAX_RETRIES         = 3
RETRY_DELAY_SEC     = 2.0
DEFAULT_DOMAIN      = "Any / Multi-Domain (Default)"

DIRECT_NARRATIVE_OPTION = "Direct Narrative / Source-Faithful (Literal Storyboard for YouTube Shorts, No Metaphors)"

# ===========================================================================
# PYDANTIC STRUCTURED OUTPUT CONTRACTS
# ===========================================================================
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

    def to_dict(self) -> Dict[str, str]:
        """Export pitch as structured dictionary."""
        return {
            "title": self.title,
            "domain_category": self.domain_category,
            "hook": self.hook,
            "core_analogy_or_beats": self.core_analogy_or_beats,
            "lift_index_or_climax": self.lift_index_or_climax,
        }

    def word_count(self) -> int:
        """Calculate total word count across all fields."""
        total = sum(len(field.split()) for field in self.to_dict().values())
        return total

    def engagement_score(self) -> float:
        """
        Heuristic engagement score (0.0-1.0) based on hook and title length.
        Longer, more detailed hooks tend to be more engaging.
        """
        hook_words = len(self.hook.split())
        title_words = len(self.title.split())
        # Optimal hook is 15-30 words, title 3-7 words
        hook_score = min(hook_words / 30, 1.0)
        title_score = min(title_words / 7, 1.0)
        return (hook_score + title_score) / 2

class PitchAuditionResponse(BaseModel):
    pitches: list[StoryPitch] = Field(
        min_length=3,
        max_length=3,
        description="Exactly 3 completely distinct story concepts"
    )

    def to_markdown_cards(self) -> str:
        """Export all pitches as concatenated markdown."""
        return "\n\n".join(p.to_markdown_card() for p in self.pitches)

    def to_list_dicts(self) -> List[Dict[str, str]]:
        """Export all pitches as list of dicts."""
        return [p.to_dict() for p in self.pitches]

    def domains_represented(self) -> List[str]:
        """Extract unique domains from all pitches."""
        return [p.domain_category for p in self.pitches]

    def is_direct_narrative(self) -> bool:
        """Check if all pitches are Direct Narrative mode."""
        return all("Direct Narrative" in p.domain_category for p in self.pitches)

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

REFINEMENT_TEMPLATE = (
    "You are a narrative refinement specialist. Review the following story pitch and enhance it based on the feedback provided.\n\n"
    "ORIGINAL PITCH:\n---\n{original_pitch}\n---\n\n"
    "FEEDBACK / REFINEMENT GOALS:\n{feedback}\n\n"
    "Generate a REVISED version of this pitch that incorporates the feedback while maintaining the core domain, hook, and pedagogical value."
)

# ===========================================================================
# ORCHESTRATOR CLASS
# ===========================================================================
class UniverseOrchestrator:
    """Orchestrates structured conceptual auditions from curriculum text with extended analytics and refinement tools."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        if not api_key:
            raise ValueError("An API key is required to initialize UniverseOrchestrator.")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.last_response: Optional[PitchAuditionResponse] = None

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
                    self.last_response = response.parsed
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

    # =========================================================================
    # HELPER METHODS: PITCH ANALYSIS & EXTRACTION
    # =========================================================================

    def get_last_pitches(self) -> Optional[PitchAuditionResponse]:
        """Retrieve the last generated pitch audition response."""
        return self.last_response

    def extract_pitch_by_index(self, response: PitchAuditionResponse, index: int) -> StoryPitch:
        """Extract a single pitch by index (0-2)."""
        if not 0 <= index < 3:
            raise IndexError(f"Pitch index must be 0-2, got {index}")
        return response.pitches[index]

    def rank_pitches_by_engagement(self, response: PitchAuditionResponse) -> List[Tuple[int, StoryPitch, float]]:
        """
        Rank pitches by engagement score.
        Returns: List of (index, pitch, score) tuples, sorted by score (highest first).
        """
        ranked = [
            (i, pitch, pitch.engagement_score())
            for i, pitch in enumerate(response.pitches)
        ]
        return sorted(ranked, key=lambda x: x[2], reverse=True)

    def compare_pitches(self, response: PitchAuditionResponse) -> Dict[str, Any]:
        """
        Generate a comprehensive comparison of all 3 pitches.
        Returns analytics on domains, engagement, word counts, etc.
        """
        return {
            "domains": response.domains_represented(),
            "is_direct_narrative": response.is_direct_narrative(),
            "word_counts": [p.word_count() for p in response.pitches],
            "engagement_scores": [p.engagement_score() for p in response.pitches],
            "average_engagement": sum(p.engagement_score() for p in response.pitches) / 3,
            "average_word_count": sum(p.word_count() for p in response.pitches) / 3,
            "ranked_by_engagement": self.rank_pitches_by_engagement(response),
        }

    def pitch_to_json(self, pitch: StoryPitch) -> str:
        """Export a single pitch as JSON."""
        return json.dumps(pitch.to_dict(), indent=2)

    def response_to_json(self, response: PitchAuditionResponse) -> str:
        """Export full response as JSON."""
        return json.dumps(response.to_list_dicts(), indent=2)

    # =========================================================================
    # HELPER METHODS: DOMAIN & KEYWORD EXTRACTION
    # =========================================================================

    def extract_domains_from_response(self, response: PitchAuditionResponse) -> List[str]:
        """Extract and return unique domains from response."""
        return response.domains_represented()

    def extract_keywords_from_pitch(self, pitch: StoryPitch, max_keywords: int = 5) -> List[str]:
        """
        Extract key terms from a pitch using simple keyword extraction.
        Returns top keywords from title and core analogy.
        """
        combined_text = f"{pitch.title} {pitch.core_analogy_or_beats}".lower()
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "is", "are", "was", "were", "be", "been",
            "to", "of", "in", "on", "at", "for", "from", "with", "by", "as"
        }
        # Simple word extraction
        words = re.findall(r'\b[a-z]{4,}\b', combined_text)
        unique_words = [w for w in words if w not in stop_words]
        return unique_words[:max_keywords]

    def get_narrative_mode(self, response: PitchAuditionResponse) -> str:
        """Determine if response is Direct Narrative or Metaphor mode."""
        if response.is_direct_narrative():
            return "Direct Narrative"
        return "Metaphor"

    # =========================================================================
    # HELPER METHODS: PITCH REFINEMENT & VARIATION
    # =========================================================================

    def refine_pitch(
        self,
        pitch: StoryPitch,
        feedback: str,
        temperature: float = DEFAULT_TEMPERATURE
    ) -> StoryPitch:
        """
        Refine a single pitch based on feedback.
        Args:
            pitch: The pitch to refine
            feedback: Specific feedback/goals for refinement
            temperature: Creativity temperature for refinement
        Returns:
            Refined StoryPitch object
        """
        pitch_markdown = pitch.to_markdown_card()
        prompt = REFINEMENT_TEMPLATE.format(
            original_pitch=pitch_markdown,
            feedback=feedback
        )

        config = types.GenerateContentConfig(
            system_instruction="You are a narrative refinement specialist focused on improving educational storytelling.",
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=StoryPitch
        )

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
            logger.error(f"Failed to refine pitch: {e}")
            raise

    def refine_response(
        self,
        response: PitchAuditionResponse,
        feedback_dict: Dict[int, str],
        temperature: float = DEFAULT_TEMPERATURE
    ) -> PitchAuditionResponse:
        """
        Refine multiple pitches based on per-pitch feedback.
        Args:
            response: The full audition response
            feedback_dict: Dict of {pitch_index: feedback_text}
            temperature: Creativity temperature
        Returns:
            New PitchAuditionResponse with refined pitches
        """
        refined_pitches = []
        for idx, pitch in enumerate(response.pitches):
            if idx in feedback_dict:
                refined = self.refine_pitch(pitch, feedback_dict[idx], temperature)
                refined_pitches.append(refined)
            else:
                refined_pitches.append(pitch)

        return PitchAuditionResponse(pitches=refined_pitches)

    # =========================================================================
    # HELPER METHODS: FILTERING & SELECTION
    # =========================================================================

    def filter_by_domain(
        self,
        response: PitchAuditionResponse,
        domain_keyword: str
    ) -> List[Tuple[int, StoryPitch]]:
        """
        Filter pitches that match a domain keyword.
        Returns: List of (index, pitch) tuples
        """
        matches = [
            (i, pitch)
            for i, pitch in enumerate(response.pitches)
            if domain_keyword.lower() in pitch.domain_category.lower()
        ]
        return matches

    def select_pitch_by_engagement_rank(
        self,
        response: PitchAuditionResponse,
        rank: int = 1  # 1=highest engagement, 3=lowest
    ) -> StoryPitch:
        """
        Select a pitch by engagement rank (1-3).
        Args:
            response: The audition response
            rank: Engagement rank (1=best, 2=middle, 3=lowest)
        Returns:
            The selected StoryPitch
        """
        if not 1 <= rank <= 3:
            raise ValueError("Rank must be 1-3")
        ranked = self.rank_pitches_by_engagement(response)
        return ranked[rank - 1][1]

    # =========================================================================
    # HELPER METHODS: EXPORT & SERIALIZATION
    # =========================================================================

    def export_response_to_csv_rows(self, response: PitchAuditionResponse) -> List[Dict[str, str]]:
        """
        Export response as CSV-compatible rows.
        Returns: List of dicts with flattened pitch data
        """
        rows = []
        for idx, pitch in enumerate(response.pitches):
            row = {
                "pitch_index": idx + 1,
                "title": pitch.title,
                "domain_category": pitch.domain_category,
                "hook": pitch.hook,
                "core_analogy_or_beats": pitch.core_analogy_or_beats,
                "lift_index_or_climax": pitch.lift_index_or_climax,
                "word_count": pitch.word_count(),
                "engagement_score": round(pitch.engagement_score(), 3),
            }
            rows.append(row)
        return rows

    def summarize_response(self, response: PitchAuditionResponse) -> Dict[str, Any]:
        """
        Generate a human-readable summary of the full response.
        Returns: Dict with summary statistics and analysis.
        """
        comparison = self.compare_pitches(response)
        return {
            "narrative_mode": self.get_narrative_mode(response),
            "pitch_count": len(response.pitches),
            "domains_represented": comparison["domains"],
            "average_engagement_score": round(comparison["average_engagement"], 3),
            "average_word_count": int(comparison["average_word_count"]),
            "top_pitch_by_engagement": comparison["ranked_by_engagement"][0][1].title,
            "top_pitch_score": round(comparison["ranked_by_engagement"][0][2], 3),
        }
