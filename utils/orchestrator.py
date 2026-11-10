"""
utils/orchestrator.py

UniverseOrchestrator: Generates 3 distinct narrative metaphor concepts
from raw curriculum strings using the Gemini API, with optional domain steering
and support for Direct Narrative (literal storyboarding for YouTube Shorts).

Extended with helper methods for pitch analysis, comparison, refinement, and metadata extraction.
Configured with api_version="v1beta" to support system_instruction and structured output schemas.

Vocabulary Scaffolding Features:
- Dual-Coding & Functional Nicknames: Mandates that complex anatomical/technical
  terms are paired with 2-to-3 word plain-English nicknames.
- Markdown Kinetic Anchors: Wraps key terms in double asterisks (**term**) so
  downstream subtitle renderers (ASS) and video compilers can create kinetic callouts.

Resilience notes:
- All Gemini structured-output calls go through _generate_structured(), which
  (a) falls back to inlining the system instruction into the prompt if the API
  rejects `system_instruction` ("Developer instruction is not enabled for api
  version v1"), and (b) does not waste retries on permanent 4xx client errors.
- 429 handling: daily-quota exhaustion fails fast with a user-presentable
  GeminiQuotaError (no pointless retries) and optionally falls over to
  fallback_models, which have their own per-model quota buckets.
- On construction, the module path and effective API version are logged so a
  stale/duplicate copy of this file or a v1 client is easy to spot.
"""
import time
import logging
import json
import random
import re
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

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

# Substring (lowercased) of the 400 error returned when system_instruction is
# sent to an API version that doesn't support it.
_SI_UNSUPPORTED_MARKER = "developer instruction is not enabled"

# 429 / quota handling.
MAX_QUOTA_WAIT_SEC = 30.0
DEFAULT_FALLBACK_MODELS: List[str] = ["gemini-2.5-flash-lite"]

# ===========================================================================
# DOMAIN TAXONOMY
# ===========================================================================
DOMAIN_TAXONOMY: List[Tuple[str, str, str]] = [
    ("Gaming & Esports", "resource management, skill trees, in-game economies, battle pass mechanics", "gen_z"),
    ("Pop Culture & Celebrity Economy", "music chart dynamics, streaming royalties, viral fame cycles", "gen_z"),
    ("Social Media & Creator Economy", "algorithm dynamics, follower growth curves, monetization thresholds", "gen_z"),
    ("Sneaker & Streetwear Culture", "limited drops, resale market economics, hype cycles, brand scarcity tactics", "gen_z"),
    ("Film, TV & Streaming Industry", "budget allocation, box office risk, streaming vs. theatrical economics", "gen_z"),
    ("Fashion & Trend Economics", "fast fashion vs. luxury positioning, seasonal cycles, trend diffusion", "gen_z"),
    ("Space Exploration & Sci-Fi", "mission resource constraints, colony economics, interplanetary trade", "gen_z"),
    ("Sports, Athletics & Pro Leagues", "salary caps, draft picks, trade deadlines, Moneyball analytics", "classic"),
    ("Food, Restaurant & Kitchen Dynamics", "kitchen operations, franchise vs. independent economics", "classic"),
    ("History & High-Stakes Moments", "gold rushes, trade route battles, heists, revolutions", "classic"),
    ("Natural Systems & Ecology", "forest mycelium networks, predator/prey dynamics, ecosystem balance", "classic"),
    ("Real-World Logistics & Transport", "airports, shipping lanes, last-mile delivery, supply chains", "classic"),
    ("Urban Planning & City Economics", "gentrification dynamics, housing market trade-offs, zoning", "classic"),
    ("Performing Arts & Live Events", "concert tour economics, ticket scalping, festival logistics", "classic"),
]
DOMAIN_NAMES: List[str] = [name for name, _, _ in DOMAIN_TAXONOMY]
_DOMAIN_DESCRIPTIONS: Dict[str, str] = {name: desc for name, desc, _ in DOMAIN_TAXONOMY}


def get_domain_choices() -> List[str]:
    """Canonical list of selectable domains."""
    return [DEFAULT_DOMAIN, DIRECT_NARRATIVE_OPTION, *DOMAIN_NAMES]

# ===========================================================================
# PYDANTIC STRUCTURED OUTPUT CONTRACTS
# ===========================================================================
class StoryPitch(BaseModel):
    title: str = Field(description="The catchy title of the story or short")
    domain_category: str = Field(description="Domain from the taxonomy or 'Direct Narrative'")
    hook: str = Field(description="The cinematic hook / first 3-5 seconds premise that stops scrolling")
    core_analogy_or_beats: str = Field(
        description="Mapping of mechanics to the domain or 3-4 chronological story beats. "
                    "Must wrap technical/anatomical keywords in double asterisks (e.g., **acetylcholine**)."
    )
    lift_index_or_climax: str = Field(description="Why this drives conceptual mastery, or the dramatic resolution/insight")

    def to_markdown_card(self) -> str:
        return (
            f"### TITLE: {self.title}\n"
            f"**Domain Category**: {self.domain_category}\n"
            f"**The Hook / Premise**: {self.hook}\n"
            f"**The Core Analogy & Scaffolding**: {self.core_analogy_or_beats}\n"
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
        """Heuristic engagement score (0.0-1.0) based on hook and title length."""
        hook_words = len(self.hook.split())
        title_words = len(self.title.split())
        hook_score = min(hook_words / 30, 1.0)
        title_score = min(title_words / 7, 1.0)
        return (hook_score + title_score) / 2


class PitchAuditionResponse(BaseModel):
    pitches: list[StoryPitch] = Field(
        min_length=3,
        max_length=3,
        description="Exactly 3 completely distinct story concepts with scaffolded vocabulary"
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
# SYSTEM INSTRUCTIONS & TEMPLATES WITH VOCABULARY SCAFFOLDING
# ===========================================================================
_CREATIVE_DIRECTOR_PREAMBLE = (
    "You are an elite Creative Director, Narrative Designer, and Instructional Expert "
    "who specializes in reaching Gen Z students who have grown up on TikTok, YouTube, "
    "gaming, and streaming culture. Your superpower is transforming complex, high-density "
    "curriculum mechanics into high-engagement metaphors that feel NATIVE to the world "
    "students actually live in — not the world textbooks assume they live in.\n\n"
    "TONE DIRECTIVE: Scripts must feel cinematic, fun, and culturally alive. Avoid corporate "
    "or academic framing. The best metaphors make students feel like insiders, not students.\n\n"
    "VOCABULARY SCAFFOLDING & DUAL-CODING RULES (MANDATORY):\n"
    "1. RULE OF TWO NAMES: Never introduce a technical, anatomical, or chemical term in isolation. "
    "Always pair it with a plain-English 2-to-3 word functional nickname (e.g., 'the chemical key—**acetylcholine**', "
    "'the power plant—**mitochondria**', 'the cellular lock—**sarcolemma**').\n"
    "2. KINETIC HIGHLIGHT SYNTAX: Wrap every primary technical keyword in double asterisks "
    "(e.g., **acetylcholine**, **action potential**, **myosin**) so the video engine can render dynamic callouts.\n"
    "3. RETENTION ECHO: Re-reference primary mechanisms with their functional nickname 15-20 seconds after introduction."
)


def _weighted_sample_without_replacement(
    items: List[Tuple[str, str, str]], weights: List[float], k: int, rng: random.Random
) -> List[Tuple[str, str, str]]:
    keyed = [(rng.random() ** (1.0 / w), item) for item, w in zip(items, weights)]
    keyed.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in keyed[:k]]


def _domain_menu(rng: random.Random, pool_size: int = 6) -> str:
    pool_size = min(pool_size, len(DOMAIN_TAXONOMY))
    weights = [2.0 if tier == "gen_z" else 1.0 for _, _, tier in DOMAIN_TAXONOMY]
    candidates = _weighted_sample_without_replacement(DOMAIN_TAXONOMY, weights, pool_size, rng)
    rng.shuffle(candidates)
    return "\n".join(f"{i}. {name} ({desc})" for i, (name, desc, _) in enumerate(candidates, start=1))


def _system_instruction_diverse(rng: random.Random) -> str:
    """Auto/multi-domain mode: 3 pitches, 3 different domains, drawn from a randomized candidate subset."""
    return (
        f"{_CREATIVE_DIRECTOR_PREAMBLE}\n\n"
        "STRICT DOMAIN DIVERSITY RULE: You MUST draw your 3 story concepts from THREE (3) COMPLETELY "
        "DIFFERENT domain categories below. Never repeat a genre. The list below is a curated subset "
        "for this run, already weighted toward Gen Z-native categories and in randomized order — treat "
        "every listed option as a fully valid choice; do not favor one just because it seems like the "
        "most literal or obvious parallel.\n\nChoose from:\n\n"
        f"{_domain_menu(rng)}"
    )


def _system_instruction_forced(domain: str) -> str:
    """Single-domain mode: all 3 pitches must come from the chosen domain."""
    description = _DOMAIN_DESCRIPTIONS.get(domain, "")
    flavor = f" ({description})" if description else ""
    return (
        f"{_CREATIVE_DIRECTOR_PREAMBLE}\n\n"
        f"STRICT SINGLE-DOMAIN RULE: The user has explicitly locked in ONE domain: "
        f"{domain}{flavor}. ALL THREE story concepts MUST be drawn from this SAME domain. "
        "Do not substitute, blend in, or drift toward a different domain for any of the three. "
        "Differentiate the three concepts through different hooks, different underlying mechanics "
        "mapped from the curriculum, and different narrative angles WITHIN this one domain."
    )

SYSTEM_INSTRUCTION_DIRECT = (
    "You are an expert YouTube Shorts director, documentary producer, and visual storyboard artist. "
    "Your superpower is turning dense, complex, or historical source text into thrilling, "
    "fast-paced short-form video story concepts without using metaphors or allegories.\n\n"
    "STRICT DIRECT NARRATIVE DIRECTIVE:\n"
    "1. NO METAPHORS OR ALLEGORIES: Extract only the literal events, anatomy, steps, and stakes.\n"
    "2. VOCABULARY SCAFFOLDING & DUAL-CODING:\n"
    "   - Every complex technical term must be preceded or followed by a functional 2-to-3 word nickname.\n"
    "   - Wrap all formal technical keywords in double asterisks (e.g., **acetylcholine**, **synapse**) for kinetic highlighting.\n"
    "3. PACING & VISUALS: Pitch 3 distinct directorial angles on the exact same material "
    "(e.g., Angle 1: High-energy bio-thriller, Angle 2: Step-by-step molecular countdown, Angle 3: Forensic diagnostic reveal).\n"
    "4. AUDIENCE RETENTION: Frame hooks around high stakes, bodily adaptations, or startling physiological facts."
)

SYSTEM_INSTRUCTION_REFINE = (
    "You are a narrative refinement specialist focused on improving educational storytelling "
    "and student retention through vocabulary scaffolding and kinetic dual-coding."
)

AUDITION_METAPHOR_TEMPLATE = (
    "Analyze the following educational material:\n\n"
    "---\n{curriculum_text}\n---\n\n"
    "Generate exactly three (3) distinct story pitches that transform these underlying mechanics into engaging narrative metaphors.\n"
    "Domain Steering Instruction: {domain_instruction}\n\n"
    "VOCABULARY SCAFFOLDING & DUAL-CODING REMINDER:\n"
    "- Pair every technical term with a 2-to-3 word functional nickname.\n"
    "- Wrap every technical keyword in double asterisks (e.g., **acetylcholine**).\n"
)

AUDITION_DIRECT_TEMPLATE = (
    "Analyze the following educational source material:\n\n"
    "---\n{curriculum_text}\n---\n\n"
    "Generate exactly three (3) distinct YouTube Shorts storyboard concepts that depict these events or concepts directly and literally, without using metaphors or allegories.\n"
    "Directorial Focus: {domain_instruction}\n\n"
    "VOCABULARY SCAFFOLDING REMINDER:\n"
    "- Pair every technical term with a functional nickname and wrap keywords in **double asterisks**.\n"
)

REFINEMENT_TEMPLATE = (
    "You are a narrative refinement specialist. Review the following story pitch and enhance it based on the feedback provided.\n\n"
    "ORIGINAL PITCH:\n---\n{original_pitch}\n---\n\n"
    "FEEDBACK / REFINEMENT GOALS:\n{feedback}\n\n"
    "Generate a REVISED version of this pitch that incorporates the feedback while maintaining the core domain, hook, "
    "vocabulary scaffolding (functional nicknames), keyword bolding (**term**), and pedagogical value."
)


# ===========================================================================
# ERROR CLASSIFICATION
# ===========================================================================
def _is_permanent_error(err: Exception) -> bool:
    if not isinstance(err, genai_errors.ClientError):
        return False
    code = getattr(err, "code", None)
    return code is not None and code != 429


def _is_system_instruction_unsupported(err: Exception) -> bool:
    return _SI_UNSUPPORTED_MARKER in str(err).lower()


def _is_quota_error(err: Exception) -> bool:
    if getattr(err, "code", None) == 429:
        return True
    return "RESOURCE_EXHAUSTED" in str(err)


def _parse_duration_seconds(text: str) -> Optional[float]:
    m = re.fullmatch(r"\s*(?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?\s*", text or "")
    if not m or not any(m.groups()):
        return None
    h, mi, sec = m.groups()
    return int(h or 0) * 3600 + int(mi or 0) * 60 + float(sec or 0)


def _format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "an unknown time"
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s" if s and m < 5 else f"{m}m"
    return f"{s}s"


def _parse_quota_error(err: Exception) -> Tuple[bool, Optional[float]]:
    daily = False
    retry_after: Optional[float] = None

    payload = getattr(err, "details", None)
    if isinstance(payload, dict):
        for d in (payload.get("error") or {}).get("details", []) or []:
            dtype = str(d.get("@type", ""))
            if dtype.endswith("QuotaFailure"):
                for v in d.get("violations", []) or []:
                    quota_id = str(v.get("quotaId", ""))
                    desc = str(v.get("description", "")).lower()
                    if "perday" in quota_id.lower() or "per day" in desc:
                        daily = True
            elif dtype.endswith("RetryInfo"):
                retry_after = _parse_duration_seconds(str(d.get("retryDelay", "")))

    text = str(err)
    if retry_after is None:
        m = re.search(r"retry in ((?:\d+h)?(?:\d+m)?[\d.]+s)", text, re.I)
        if m:
            retry_after = _parse_duration_seconds(m.group(1))
    if not daily and ("PerDay" in text or "per day" in text.lower()):
        daily = True

    return daily, retry_after


class GeminiQuotaError(RuntimeError):
    def __init__(
        self,
        model: str,
        retry_after_s: Optional[float] = None,
        daily: bool = False,
        tried_models: Optional[List[str]] = None,
    ):
        self.model = model
        self.retry_after_s = retry_after_s
        self.daily = daily
        self.tried_models = tried_models or [model]

        scope = "daily" if daily else "rate"
        tried = (
            f" (tried: {', '.join(self.tried_models)})" if len(self.tried_models) > 1 else ""
        )
        wait = f" It should free up in about {_format_duration(retry_after_s)}." if retry_after_s else ""
        super().__init__(
            f"Gemini {scope} quota exhausted for {model}{tried}.{wait} "
            "Free-tier daily quotas reset at midnight Pacific time. To keep going now, "
            "enable billing on the Google Cloud project behind your API key, or use a "
            "different model."
        )


# ===========================================================================
# ORCHESTRATOR CLASS
# ===========================================================================
class UniverseOrchestrator:
    """Orchestrates structured conceptual auditions from curriculum text with extended analytics and refinement tools."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        fallback_models: Optional[List[str]] = None,
    ):
        http_opts = types.HttpOptions(api_version="v1beta")
        if api_key:
            self._client = genai.Client(api_key=api_key, http_options=http_opts)
        else:
            try:
                self._client = genai.Client(http_options=http_opts)
            except Exception:
                self._client = None

        self.model = model
        self.fallback_models: List[str] = (
            list(DEFAULT_FALLBACK_MODELS) if fallback_models is None else list(fallback_models)
        )
        self.last_model_used: Optional[str] = None
        self.last_response: Optional[PitchAuditionResponse] = None

        try:
            _opts = getattr(getattr(self._client, "_api_client", None), "_http_options", None)
            _ver = getattr(_opts, "api_version", "unknown")
        except Exception:
            _ver = "unknown"
        logger.info(
            "UniverseOrchestrator initialised (module=%s, model=%s, api_version=%s, client=%s)",
            __file__, self.model, _ver, "ready" if self._client else "none",
        )

    @property
    def client(self) -> "genai.Client":
        """Gemini client. Raises if this instance was created without an API key."""
        if self._client is None:
            raise ValueError(
                "An API key is required for Gemini calls (generation/refinement). "
                "This UniverseOrchestrator was created without one (analytics-only mode)."
            )
        return self._client

    # =========================================================================
    # CORE: RESILIENT STRUCTURED-OUTPUT CALL
    # =========================================================================
    def _generate_structured(
        self,
        *,
        system_instruction: str,
        prompt: str,
        temperature: float,
        schema: Any,
    ):
        client = self.client

        models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
        quota_errors: List[GeminiQuotaError] = []

        for i, model_name in enumerate(models_to_try):
            try:
                result = self._call_model(
                    client,
                    model_name,
                    system_instruction=system_instruction,
                    prompt=prompt,
                    temperature=temperature,
                    schema=schema,
                )
                self.last_model_used = model_name
                if i > 0:
                    logger.warning("Request served by fallback model %s (primary %s exhausted).",
                                   model_name, self.model)
                return result

            except GeminiQuotaError as qe:
                quota_errors.append(qe)
                if i + 1 < len(models_to_try):
                    logger.warning("Quota exhausted for %s; trying fallback model %s.",
                                   model_name, models_to_try[i + 1])
                continue

            except Exception as e:
                if i == 0:
                    raise
                logger.warning("Fallback model %s unusable (%s); skipping.", model_name, e)
                continue

        retry_values = [q.retry_after_s for q in quota_errors if q.retry_after_s is not None]
        raise GeminiQuotaError(
            model=self.model,
            retry_after_s=min(retry_values) if retry_values else None,
            daily=all(q.daily for q in quota_errors),
            tried_models=models_to_try,
        )

    def _call_model(
        self,
        client: "genai.Client",
        model_name: str,
        *,
        system_instruction: str,
        prompt: str,
        temperature: float,
        schema: Any,
    ):
        use_system_instruction = True
        last_error: Optional[Exception] = None
        attempt = 1

        while attempt <= MAX_RETRIES:
            try:
                if use_system_instruction:
                    config = types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=temperature,
                        response_mime_type="application/json",
                        response_schema=schema,
                    )
                    contents = prompt
                else:
                    config = types.GenerateContentConfig(
                        temperature=temperature,
                        response_mime_type="application/json",
                        response_schema=schema,
                    )
                    contents = f"{system_instruction}\n\n---\n\n{prompt}"

                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                if response.parsed:
                    return response.parsed
                raise ValueError("Model response did not contain structured parsed data.")

            except Exception as e:
                last_error = e

                if use_system_instruction and _is_system_instruction_unsupported(e):
                    logger.warning(
                        "API rejected system_instruction (%s); retrying with the "
                        "instruction inlined into the prompt.", e
                    )
                    use_system_instruction = False
                    continue

                if _is_quota_error(e):
                    daily, retry_after = _parse_quota_error(e)
                    too_long = retry_after is not None and retry_after > MAX_QUOTA_WAIT_SEC
                    if daily or too_long or attempt >= MAX_RETRIES:
                        logger.error("Quota exhausted for %s (daily=%s, retry_after=%s).",
                                     model_name, daily, retry_after)
                        raise GeminiQuotaError(model_name, retry_after, daily) from e
                    wait = (retry_after + 1.0) if retry_after is not None else RETRY_DELAY_SEC * attempt
                    logger.warning("Rate limited on %s; waiting %.1fs (attempt %d/%d).",
                                   model_name, wait, attempt, MAX_RETRIES)
                    time.sleep(wait)
                    attempt += 1
                    continue

                if _is_permanent_error(e):
                    logger.error("Gemini request rejected (not retrying): %s", e)
                    raise RuntimeError(f"Gemini request rejected (not retrying): {e}") from e

                logger.warning("Gemini attempt %d/%d failed on %s: %s",
                               attempt, MAX_RETRIES, model_name, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SEC * attempt)
                attempt += 1

        raise RuntimeError(f"Gemini call failed after {MAX_RETRIES} attempts: {last_error}")

    # =========================================================================
    # AUDITION
    # =========================================================================
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
            domain_instruction = "Direct visual storyboards with high narrative pacing, functional nicknames, and literal fidelity."
            prompt = AUDITION_DIRECT_TEMPLATE.format(
                curriculum_text=text,
                domain_instruction=domain_instruction
            )
        elif domain and domain != DEFAULT_DOMAIN and domain in DOMAIN_NAMES:
            system_instruction = _system_instruction_forced(domain)
            domain_instruction = (
                f"All three pitches MUST be drawn from the '{domain}' domain specifically — "
                "vary the hook, story angle, and functional nicknames, not the domain."
            )
            prompt = AUDITION_METAPHOR_TEMPLATE.format(
                curriculum_text=text,
                domain_instruction=domain_instruction
            )
        else:
            system_instruction = _system_instruction_diverse(random.Random())
            if domain and domain != DEFAULT_DOMAIN:
                logger.warning(
                    "audition_pitches: domain_choice %r not in the known taxonomy; "
                    "falling back to diverse auto mode instead of forcing it.", domain
                )
                domain_instruction = (
                    f"Prioritize concepts aligned with or inspired by: {domain}, "
                    "but still draw the 3 pitches from 3 different domains overall."
                )
            else:
                domain_instruction = (
                    "Draw from 3 completely different domains with preference for "
                    "Gen Z native categories. Include functional nicknames for all technical terms."
                )
            prompt = AUDITION_METAPHOR_TEMPLATE.format(
                curriculum_text=text,
                domain_instruction=domain_instruction
            )

        result = self._generate_structured(
            system_instruction=system_instruction,
            prompt=prompt,
            temperature=temp,
            schema=PitchAuditionResponse,
        )
        self.last_response = result
        return result

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
        """Rank pitches by engagement score."""
        ranked = [
            (i, pitch, pitch.engagement_score())
            for i, pitch in enumerate(response.pitches)
        ]
        return sorted(ranked, key=lambda x: x[2], reverse=True)

    def compare_pitches(self, response: PitchAuditionResponse) -> Dict[str, Any]:
        """Generate a comprehensive comparison of all 3 pitches."""
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
        """Extract key terms from bolded markdown (**term**) or high-frequency words."""
        bolded_matches = re.findall(r'\*\*(.*?)\*\*', f"{pitch.title} {pitch.core_analogy_or_beats}")
        if bolded_matches:
            # Deduplicate while preserving order
            seen = set()
            unique_bold = [x.strip() for x in bolded_matches if not (x.strip() in seen or seen.add(x.strip()))]
            if len(unique_bold) >= max_keywords:
                return unique_bold[:max_keywords]

        combined_text = f"{pitch.title} {pitch.core_analogy_or_beats}".lower()
        stop_words = {
            "the", "a", "an", "and", "or", "is", "are", "was", "were", "be", "been",
            "to", "of", "in", "on", "at", "for", "from", "with", "by", "as"
        }
        words = re.findall(r'\b[a-z]{4,}\b', combined_text)
        unique_words = [w for w in words if w not in stop_words]
        return (bolded_matches + unique_words)[:max_keywords]

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
        """Refine a single pitch based on feedback."""
        pitch_markdown = pitch.to_markdown_card()
        prompt = REFINEMENT_TEMPLATE.format(
            original_pitch=pitch_markdown,
            feedback=feedback
        )

        try:
            return self._generate_structured(
                system_instruction=SYSTEM_INSTRUCTION_REFINE,
                prompt=prompt,
                temperature=temperature,
                schema=StoryPitch,
            )
        except Exception as e:
            logger.error("Failed to refine pitch: %s", e)
            raise

    def refine_response(
        self,
        response: PitchAuditionResponse,
        feedback_dict: Dict[int, str],
        temperature: float = DEFAULT_TEMPERATURE
    ) -> PitchAuditionResponse:
        """Refine multiple pitches based on per-pitch feedback."""
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
        """Filter pitches that match a domain keyword."""
        matches = [
            (i, pitch)
            for i, pitch in enumerate(response.pitches)
            if domain_keyword.lower() in pitch.domain_category.lower()
        ]
        return matches

    def select_pitch_by_engagement_rank(
        self,
        response: PitchAuditionResponse,
        rank: int = 1
    ) -> StoryPitch:
        """Select a pitch by engagement rank (1-3)."""
        if not 1 <= rank <= 3:
            raise ValueError("Rank must be 1-3")
        ranked = self.rank_pitches_by_engagement(response)
        return ranked[rank - 1][1]

    # =========================================================================
    # HELPER METHODS: EXPORT & SERIALIZATION
    # =========================================================================

    def export_response_to_csv_rows(self, response: PitchAuditionResponse) -> List[Dict[str, str]]:
        """Export response as CSV-compatible rows."""
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
        """Generate a human-readable summary of the full response."""
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
