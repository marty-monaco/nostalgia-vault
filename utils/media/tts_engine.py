import os
from pathlib import Path
from elevenlabs.client import ElevenLabs

def generate_voiceover(
    script_text: str, 
    output_path: str = "temp_voiceover.mp3",
    voice_id: str = "JBFqnCBsd6RMkjVDRZzb",
    model_id: str = "eleven_turbo_v2_5"
) -> dict:
    """
    Synthesizes speech from an 85-second script using ElevenLabs.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY environment variable is missing.")

    client = ElevenLabs(api_key=api_key)
    
    # Generate the stream
    audio_stream = client.text_to_speech.convert(
        text=script_text,
        voice_id=voice_id,
        model_id=model_id,
        output_format="mp3_44100_128",
    )

    output_file = Path(output_path)
    with open(output_file, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)

    return {
        "audio_path": str(output_file.resolve()),
        "status": "completed"
    }
  
