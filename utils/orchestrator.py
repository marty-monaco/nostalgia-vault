import os
from google import genai
from google.genai import types

class UniverseOrchestrator:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API Key Missing! Please provide a Gemini API Key.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.5-flash"

    def audition_metaphors(self, raw_curriculum):
        system_instruction = (
            "You are the Lead Educational Architect of The Vault platform. "
            "Your goal is to maximize student 'Knowledge Lift' and conceptual mastery. "
            "You transform dry, complex academic text into high-impact narrative stories. "
            "You do not default to one specific era or theme; you analyze the core mechanics "
            "of a lesson and find the absolute best cultural anchor or metaphor that makes it click."
        )

        prompt = f"""
        Analyze the following raw educational curriculum text:
        ---
        {raw_curriculum}
        ---

        Please provide a structured 'Creative Director Report' covering the following exactly:
        1. CORE CONCEPT DECOMPOSITION: Break down the text into its top 2-3 essential atomic learning concepts.
        2. METAPHOR AUDITION: Propose 3 wildly distinct cultural, historical, or pop-culture narrative anchors (e.g., 90s hip-hop culture, 80s spy thrillers, video game mechanics, sci-fi concepts) that share structural logic with the lesson.
        3. CONCEPTUAL LIFT RANKING: Evaluate all 3 anchors. Explain which one provides the strongest, most intuitive mental bridge for a high school student and why.
        4. THE WINNING BLUEPRINT: Choose the #1 anchor and draft a high-level summary of how a 90-second educational script would map out using this metaphor.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )
            )
            return response.text
        except Exception as e:
            return f"Orchestrator Error contacting Gemini: {e}"