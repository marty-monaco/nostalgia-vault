from __future__ import annotations
import re
from typing import List, Dict, Any

from utils.video_models import VideoProject, ScriptScene

def build_scene_manifest(project: VideoProject, raw_script_text: str) -> VideoProject:
    """
    Converts a raw LLM script manifest into structured scene objects.
    This should replace the brittle regex splitting in Page 3 later.
    """
    project.scenes = []
    lines = raw_script_text.splitlines()

    current_scene = None
    for line in lines:
        if not line.strip():
            continue

        m = re.match(r"Scene\s+(\d+)\s*\((\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\)", line, re.I)
        if m:
            if current_scene:
                project.scenes.append(current_scene)

            idx = int(m.group(1))
            start = _to_seconds(m.group(2))
            end = _to_seconds(m.group(3))
            current_scene = ScriptScene(
                index=idx,
                start_time=start,
                end_time=end,
                title="",
                visual_prompt="",
                narration="",
            )
            continue

        if current_scene is None:
            continue

        if line.lower().startswith("[visual]"):
            current_scene.visual_prompt = line.split(":", 1)[1].strip() if ":" in line else ""
        elif line.lower().startswith("[vo]"):
            current_scene.narration = line.split(":", 1)[1].strip() if ":" in line else ""
        elif current_scene.title == "":
            current_scene.title = line.strip()
        else:
            current_scene.narration = (current_scene.narration + " " + line.strip()).strip()

    if current_scene:
        project.scenes.append(current_scene)

    project.status = "scene_manifest_ready"
    return project

def _to_seconds(mmss: str) -> float:
    minutes, seconds = map(int, mmss.split(":"))
    return minutes * 60 + seconds
