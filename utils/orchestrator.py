"""
utils/orchestrator.py

UniverseOrchestrator: Generates 3 distinct narrative metaphor concepts 
from raw curriculum strings using the Gemini API, with optional user-selected domain steering.
"""
import os
from google import genai
from google.genai import types

class UniverseOrchestrator:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API Key Missing! Ensure GEMINI_API_KEY is configured.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.5-flash"

    def audition_metaphors(self, raw_curriculum: str, preferred_domain: str = "Any / Multi-Domain (Default)") -> str:
        """Pitches 3 distinct narrative concepts, prioritizing a preferred domain if selected."""
        
        domain_directive = ""
        if preferred_domain != "Any / Multi-Domain (Default)":
            domain_directive = (
                f"\n\nPRIMARY USER REQUIREMENT: At least ONE (1) of your pitched story concepts MUST be explicitly "
                f"built using the '{preferred_domain}' framework (e.g., NBA/NFL/MLB collective bargaining, roster scarcity, or union dynamics if sports is chosen)."
            )

        system_instruction = (
            "You are an elite Creative Director, Narrative Designer, and Instructional Expert. "
            "Your superpower is transforming complex, high-density curriculum mechanics into "
            "associative schema-mapping metaphors that anchor dry facts to intuitive real-world systems."
            f"{domain_directive}\n\n"
            "STRICT DOMAIN DIVERSITY RULE: You MUST draw your 3 story concepts from THREE (3) COMPLETELY "
            "DIFFERENT domain categories below. Never repeat a genre (e.g., do not pair two sci-fi, "
            "fantasy, or gaming tropes together). Choose from:\n"
            "1. Sports, Athletics & Professional Leagues (NBA / NFL / MLB Collective Bargaining, Tactical Plays, Pit Stops)\n"
            "2. Real-World Logistics & Transport (Airports, Traffic Systems, Shipping, Supply Chains)\n"
            "3. Culinary & Restaurant Dynamics (Kitchen Operations, Recipe Chemistry, Service Trade-offs)\n"
            "4. Natural Systems & Ecology (Forest Mycelium Networks, River Dynamics, Ecosystem Balances)\n"
            "5. Architecture & Construction (Load Balancing, Blueprinting, Foundations vs. Facades)\n"
            "6. History & High-Stakes Diplomacy (Trade Routes, Negotiation Paradoxes, Expeditions)\n"
            "7. Performing Arts & Music (Orchestral Conducting, Stage Management, Film Production)"
        )

        prompt = f"""
        Analyze the following educational material:
        ---
        {raw_curriculum}
        ---

        Based on this material, pitch exactly THREE (3) completely distinct narrative concepts or metaphorical worlds.

        You must format your response using the exact delimiter string '|||' between the stories so the application can split them into cards. Do not include '|||' anywhere else.

        Format your entire output exactly like this:

        ### TITLE: [Story 1 Title]
        **Domain Category**: [State the domain category used from the list of 7]
        **The Hook / Premise**: [A cinematic, highly intuitive real-world story setup]
        **The Core Analogy**: [Explain exactly how the technical mechanics from the text map directly to the rules/actions of this domain]
        **The Lift Index**: [Why this specific domain metaphor drives conceptual mastery]
        |||
        ### TITLE: [Story 2 Title]
        **Domain Category**: [State the domain category used from the list of 7 - MUST BE DIFFERENT FROM STORY 1]
        **The Hook / Premise**: [Setup in a completely different domain]
        **The Core Analogy**: [How the technical mechanics map to this second domain]
        **The Lift Index**: [Pedagogical value]
        |||
        ### TITLE: [Story 3 Title]
        **Domain Category**: [State the domain category used from the list of 7 - MUST BE DIFFERENT FROM STORIES 1 & 2]
        **The Hook / Premise**: [Setup in a third completely distinct domain]
        **The Core Analogy**: [How the technical mechanics map to this third domain]
        **The Lift Index**: [Pedagogical value]
        """

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
        )
        return response.text
