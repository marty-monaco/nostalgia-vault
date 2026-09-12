"""
vault_curriculum_prompts.py

Centralized prompt templates, psychometric design constraints,
and Pydantic schemas for The Vault curriculum generation engine.
"""

from pydantic import BaseModel, Field


class AssessmentQuestion(BaseModel):
    question: str = Field(description="The question stem.")
    opt1: str = Field(description="Option A")
    opt2: str = Field(description="Option B")
    opt3: str = Field(description="Option C")
    correct_answer: str = Field(description="Verbatim text matching exactly one of opt1, opt2, or opt3.")


class VaultModuleSchema(BaseModel):
    topic: str = Field(description="Clean, impactful topic title.")
    video_length_sec: int = Field(default=85, description="Length of script in seconds.")
    video_script: str = Field(description="Engaging 85-second narrative micro-documentary script.")
    
    # Pre-Assessment (Diagnostic baseline)
    pre_q1: AssessmentQuestion
    pre_q2: AssessmentQuestion
    
    # Post-Assessment (Active retrieval & retention)
    post_q1: AssessmentQuestion
    post_q2: AssessmentQuestion


SYSTEM_PSYCHOMETRIC_INSTRUCTIONS = """
You are the Lead Psychometrician and Instructional Designer for "The Vault", an AI-powered educational platform.
The Vault uses high-stakes narrative micro-documentaries to teach counter-intuitive concepts in economics, business, and finance.

Your objective is to generate curriculum modules that achieve a STATISTICALLY POSITIVE LIFT (+0.35 to +0.55 delta between pre-test and post-test).

STRICT PSYCHOMETRIC LAWS:

1. PRE-ASSESSMENT (Baseline Diagnostic - Target 40%-60% Pass Rate):
   - STRICT BAN: NEVER ask dictionary definitions, obvious vocabulary, or colloquialisms (e.g., DO NOT ask "What is scarcity?" or "What is a trade-off?").
   - CEILING EFFECT PREVENTION: High school seniors easily guess definition questions, creating a 100% baseline where positive lift is mathematically impossible.
   - REQUIREMENT: Probe the intuitive fallacy or naive common-sense assumption that the video will dismantle. Test *why* intuition fails in this scenario.

2. POST-ASSESSMENT (Active Retrieval - Target 80%-95% Pass Rate):
   - NARRATIVE ANCHOR: All post-test questions MUST stay strictly within the world, characters, narrative, and direct events of the video script.
   - STRICT BAN ON DOMAIN JUMPS: Never switch domains (e.g., if the video is about water scarcity in a desert, NEVER ask about rent control or apartment maintenance in the post-test).
   - DIRECT CAUSALITY: Questions must test the specific economic mechanisms dramatized in the story.

3. DISTRACTOR HYGIENE:
   - Distractors must represent the specific intuitive misconception that the lesson corrects.
   - BANNED: Do not use realistic industry buzzwords or alternative valid concepts (e.g., do not use "algorithmic incentives" as a distractor if the answer is "trade-offs").
   - Ensure the correct answer precisely matches one of the three options word-for-word.
"""

def build_module_prompt(topic: str, pilot_id: str, learning_objective: str) -> str:
    """Builds the operational user prompt for module generation."""
    return f"""
Generate a complete curriculum module for The Vault.

Cohort / Pilot ID: {pilot_id}
Topic: {topic}
Core Learning Objective: {learning_objective}

Ensure the script tells a dramatic, narrative-driven 85-second story.
Calibrate the pre-test to challenge baseline intuition and calibrate the post-test to evaluate retention of the story's core economic mechanism without shifting domains.
"""
