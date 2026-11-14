"""
Validation layer for the video production pipeline.

Checks for basic integrity before declaring a video render valid.
"""

from __future__ import annotations

from typing import Dict, List

from .models import QualityReport, VideoProject


def validate_video_project(project: VideoProject) -> QualityReport:
    checks: Dict[str, bool] = {}
    warnings: List[str] = []
    errors: List[str] = []

    checks["has_scenes"] = bool(project.scenes)
    checks["total_duration_matches_target"] = abs(project.total_scene_duration() - project.target_duration_seconds) < 10.0
    checks["voiceover_exists"] = bool(project.voiceover_path)
    checks["subtitles_exist"] = bool(project.subtitles_path)
    checks["assets_planned"] = bool(project.asset_specs)

    if not checks["has_scenes"]:
        errors.append("Project has no scenes.")
    if not checks["total_duration_matches_target"]:
        warnings.append("Scene total duration is not close to the target runtime.")
    if not checks["voiceover_exists"]:
        warnings.append("No voiceover file created yet.")
    if not checks["subtitles_exist"]:
        warnings.append("No subtitle file created yet.")
    if not checks["assets_planned"]:
        warnings.append("No visual asset planning metadata was generated.")

    report = QualityReport(
        project_id=project.project_id,
        passed=not errors and all(checks.values()),
        checks=checks,
        warnings=warnings,
        errors=errors,
    )

    return report
