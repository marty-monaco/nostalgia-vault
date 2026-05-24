import os
from google import genai
from google.genai import types

class UniverseOrchestrator:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API Key Missing!")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.5-flash"

    def audition_metaphors(self, raw_curriculum):
        system_instruction = (
            "You are an elite Creative Director, Narrative Designer, and Instructional Expert. "
            "Your superpower is transforming complex, dry curriculum mechanics into high-engagement "
            "stories and metaphors that perfectly capture the imagination of high school seniors."
        )

        prompt = f"""
        Analyze the following educational material:
        ---
        {raw_curriculum}
        ---

        Based on this material, pitch exactly THREE (3) completely distinct narrative concepts or metaphorical worlds that can be used to build a 90-second educational story video. 

        You must format your response using the exact delimiter string '|||' between the stories so the application can split them into cards. Do not include '|||' anywhere else.

        Format your entire output exactly like this:

        ### TITLE: [Story 1 Title]
        **The Hook / Premise**: [A cinematic, high-school-appropriate story setup]
        **The Core Analogy**: [Explain exactly how the technical mechanics from the text map directly to the rules/actions of this story world]
        **The Lift Index**: [Why this specific story drives conceptual mastery for a teenager]
        |||
        ### TITLE: [Story 2 Title]
        **The Hook / Premise**: [A completely different genre or scenario, e.g., sci-fi, history, retro pop-culture]
        **The Core Analogy**: [How the technical mechanics map to this second world]
        **The Lift Index**: [Pedagogical value]
        |||
        ### TITLE: [Story 3 Title]
        **The Hook / Premise**: [A third completely distinct narrative direction]
        **The Core Analogy**: [How the technical mechanics map to this third world]
        **The Lift Index**: [Pedagogical value]
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7, # Higher temperature for creative narrative variety
                )
            )
            return response.text
        except Exception as e:
            return f"Orchestrator Error contacting Gemini: {e}"
