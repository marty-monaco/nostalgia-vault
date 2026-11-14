"""
Text-to-speech abstraction layer for The Vault.

This current version uses a mock implementation, but the interface is designed
to support providers like ElevenLabs, OpenAI TTS, or Google Cloud TTS later.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import NarrationCue, VideoProject


class TTSClient:
    def __init__(self, provider: str = "mock", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")

    def generate(self, project: VideoProject, output_dir: str = "temp_media") -> Dict[str, Any]:
        """
        Generate voiceover audio and narration cues.

        Mock mode returns a placeholder file and synthetic cue timestamps.
        """
        if self.provider == "mock" or not self.api_key:
            return self._mock_generate(project, output_dir)

        # Future live provider path:
        # from elevenlabs import generate
        # ...
        raise NotImplementedError("Live TTS provider not configured yet.")

    def _mock_generate(self, project: VideoProject, output_dir: str) -> Dict[str, Any]:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        output_path = out_dir / f"{project.project_id}_voiceover.mp3"
        output_path.write_bytes(b"MOCK_AUDIO_PAYLOAD")

        words = []
        for scene in project.scenes:
            words.extend(scene.voiceover.split())

        total_duration = float(project.target_duration_seconds)
        cue_points: List[NarrationCue] = []
        if words:
            chunk_size = max(1, len(words) // max(1, len(project.scenes)))
            for idx, scene in enumerate(project.scenes):
                chunk_words = words[idx * chunk_size : (idx + 1) * chunk_size]
                if not chunk_words:
                    chunk_words = words[-1:]
                start = scene.start_time
                end = scene.end_time
                cue_points.append(
                    NarrationCue(
                        start_time=start,
                        end_time=end,
                        text=" ".join(chunk_words),
                        speaker="narrator",
                    )
                )

        project.narration_cues = cue_points
        project.voiceover_path = str(output_path.resolve())

        return {
            "audio_path": project.voiceover_path,
            "duration_seconds": total_duration,
            "cues": cue_points,
            "status": "mocked",
        }
