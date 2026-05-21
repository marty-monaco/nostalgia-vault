import os
from google import genai
from google.genai import types

class ProductionEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API Key Missing!")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.5-flash"

    def generate_blueprint(self, creative_report):
        system_instruction = (
            "You are an expert Instructional Designer and Hollywood Scriptwriter. "
            "Your job is to take a creative metaphorical blueprint and flesh it out into a "
            "production-ready, 90-second educational video script and evaluation package."
        )

        prompt = f"""
        Using the following Creative Director Metaphor Blueprint:
        ---
        {creative_report}
        ---

        Please generate a complete, production-ready payload with the following two sections:

        ### SECTION 1: DUAL-COLUMN VIDEO SCRIPT (90 Seconds)
        Format this as a markdown table with two distinct columns: 
        * **Visual Cue / On-Screen Action**: Detailed instructions for what the viewer sees (perfect for feeding into an AI video generator like Runway or Sora).
        * **Audio / Voiceover**: The exact text to be spoken by the narrator or characters (perfect for feeding into a voice cloner like ElevenLabs).
        Make sure the progression cleanly maps the chosen metaphor to the underlying financial mechanics step-by-step.

        ### SECTION 2: CALIBRATED ASSESSMENT PACKAGE
        Provide exactly 4 multiple-choice questions (with answers and brief explanations):
        * **2 Pre-Video Baseline Questions**: Testing the raw financial concept directly using clear, high-school-appropriate terminology (to establish a baseline).
        * **2 Post-Video Conceptual Questions**: Testing the student's mastery *through the lens of the metaphor* or its application, proving they understand the core operational mechanism.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
            )
            return response.text
        except Exception as e:
            return f"Production Engine Error: {e}"