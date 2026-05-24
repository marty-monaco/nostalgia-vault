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
            "You are an expert Instructional Designer and Media Producer. Your job is to take a "
            "narrative metaphor concept and build it out into a 90-second video script and assessment package."
        )

        prompt = f"""
        Using the following Selected Story Blueprint:
        ---
        {creative_report}
        ---

        Please generate a complete production payload broken into these two specific sections:

        ### SECTION 1: 90-SECOND RUNNING VIDEO SCRIPT
        Write out the script chronologically as a series of scenes (Scene 1, Scene 2, Scene 3, etc.). For each scene, provide:
        * **[VISUAL]**: Clear, vivid instructions for the on-screen action, animations, or scenery (perfect for an AI video generator).
        * **[AUDIO]**: The exact voiceover text to be spoken by the narrator (clear, high-school-appropriate language perfect for voice cloning).

        Ensure the story progression tracks perfectly to the underlying financial rules from the source text.

        ### SECTION 2: CALIBRATED ASSESSMENT PACKAGE
        Provide exactly 4 multiple-choice questions (with options A, B, C, D, the correct answer, and a 1-sentence explanation):
        * **2 Pre-Video Baseline Questions**: Testing the raw financial concept directly using clear, textbook terminology.
        * **2 Post-Video Conceptual Questions**: Testing mastery *through the lens of the story or metaphor* to prove they understand the operational mechanism.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4, # Balanced for formatting stability
                )
            )
            return response.text
        except Exception as e:
            return f"Production Engine Error: {e}"
