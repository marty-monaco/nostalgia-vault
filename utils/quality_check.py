from __future__ import annotations
from typing import List, Dict, Any

def validate_render_artifact(render_result: Dict[str, Any]) -> List[str]:
    issues: List[str] = []

    if not render_result.get("video_path"):
        issues.append("No video path produced.")
        return issues

    if render_result.get("status") == "mocked":
        issues.append("Render is using mock output; not production-ready.")

    if render_result.get("resolution") is None:
        issues.append("Missing video resolution metadata.")

    if render_result.get("duration_seconds", 0) <= 0:
        issues.append("Video duration is invalid.")

    return issues
