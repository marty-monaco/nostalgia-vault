"""
Scene planner for converting narrative pitch + source curriculum into a 90-second
storyboard manifest.
"""

from __future__ import annotations

import re
from typing import List, Optional

from .models import Scene, VideoProject


def _safe_title(value: str) -> str:
    return value.strip() or "Untitled Scene"


def _build_default_scene_blocks(topic: str, source_text: str, target_duration: int = 90) -> List[Scene]:
    """
    Create a default scene plan from a curriculum string.

    This is intentionally simple for the first implementation:
    - 5 scenes
    - each has a title, rough timing, visual prompt, voiceover, and caption
    - scene durations are normalized to the target duration
    """
    duration = float(target_duration)
    scene_durations = [0.16, 0.22, 0.24, 0.22, 0.16]
    normalized = [duration * p for p in scene_durations]
    # Force a rounded total to closely match target duration
    rounded = [round(v, 2) for v in normalized]
    total = sum(rounded)
    delta = round(duration - total, 2)
    rounded[-1] += delta

    scenes: List[Scene] = []
    start = 0.0

    for idx, dur in enumerate(rounded, start=1):
        end = start + dur
        scenes.append(
            Scene(
                scene_index=idx,
                title=f"Scene {idx}: { _safe_title(_scene_title_for_index(idx)) }",
                start_time=round(start, 2),
                end_time=round(end, 2),
                duration_seconds=round(dur, 2),
                visual_prompt=f"{topic} — cinematic still representing the concept for scene {idx}",
                voiceover=(
                    f"Scene {idx} of the story arc for {topic}. "
                    f"Use this as the narration script anchor for the generated video."
                ),
                on_screen_text=f"{topic} • Scene {idx}",
                caption=f"{topic} • Scene {idx}",
                asset_prompt=f"Create a vertical cinematic visual for {topic}, scene {idx}.",
            )
        )
        start = end

    return scenes


def _scene_title_for_index(idx: int) -> str:
    mapping = {
        1: "Hook & Setup",
        2: "Core Concept",
        3: "Conflict or Tension",
        4: "Decision & Resolution",
        5: "Takeaway",
    }
    return mapping.get(idx, f"Scene {idx}")


def _extract_first_3000_chars(text: str) -> str:
    return (text or "")[:3000]


def build_video_project_from_script(
    topic: str,
    script_text: str,
    target_duration_seconds: int = 90,
    project_id: Optional[str] = None,
) -> VideoProject:
    """
    Convert an existing narrative script into a structured video project.
    This is a strong first-step wrapper around the rest of the media stack.
    """
    project_id = project_id or f"video_{abs(hash(topic.lower().strip()))}"

    scenes = _build_default_scene_blocks(
        topic=topic,
        source_text=script_text,
        target_duration=target_duration_seconds,
    )

    # This is a lightweight pass: if the incoming script already includes
    # scene markers, we could parse them here later. For now, we keep it simple.
    project = VideoProject(
        project_id=project_id,
        topic=topic,
        source_text=_extract_first_3000_chars(script_text),
        target_duration_seconds=target_duration_seconds,
        scenes=scenes,
    )

    return project
