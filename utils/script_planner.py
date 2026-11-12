"""
utils/script_planner.py

Turn a chosen pitch and curriculum into a structured VideoProject.

This module is the bridge between:
- the selected pitch from Page 2
- the content coming from Page 1 / ingestion
- the timed, scene-based video project used by TTS / assets / render later
"""

from __future__ import annotations

import re
from typing import List, Optional

from utils.video_models import (
    AssessmentQuestion,
    ScriptScene,
    VideoProject,
    parse_project_from_llm_output,
)

# ---------------------------------------------------------------------------
# SCENE MANIFEST HELPERS
# ---------------------------------------------------------------------------

def build_video_project_from_prompt(
    topic: str,
    pilot_id: str,
    chosen_pitch: str,
    curriculum_text: str,
    raw_script_output: str,
    target_duration_sec: int = 90,
) -> VideoProject:
    """
    Build and validate a VideoProject from the raw script+assessment output.
    """
    project = parse_project_from_llm_output(
        raw_output=raw_script_output,
        topic=topic,
        pilot_id=pilot_id,
        target_duration_sec=target_duration_sec,
    )
    project.selected_pitch_title = chosen_pitch[:120] if chosen_pitch else ""
    project.selected_pitch_text = chosen_pitch or ""
    project.source_curriculum_snippet = curriculum_text[:4000] if curriculum_text else ""
    return project


def auto_fill_scene_details(project: VideoProject) -> VideoProject:
    """
    Add missing title/visual_prompt/narration data for scenes that were parsed loosely.
    """
    for scene in project.scenes:
        if not scene.title.strip():
            scene.title = f"Scene {scene.index}"
        if not scene.visual_prompt.strip():
            scene.visual_prompt = f"Educational cinematic visual for scene {scene.index}"
        if not scene.narration.strip():
            scene.narration = "Narration pending manual review."
    return project


def enforce_scene_duration(project: VideoProject, target_duration_sec: int) -> VideoProject:
    """
    Projects should be near the desired duration. This is a lightweight
    balancing utility, not a perfect render engine.
    """
    if not project.scenes:
        return project

    total = project.total_scene_duration
    if abs(total - target_duration_sec) <= 12:
        return project

    # Spread the difference proportionally
    delta = target_duration_sec - total
    if delta == 0:
        return project

    for scene in project.scenes:
        if scene.duration <= 0:
            continue
        scale = scene.duration / total
        scene.end_time += delta * scale

    return project


# ---------------------------------------------------------------------------
# SCRIPT QUALITY / REFINEMENT
# ---------------------------------------------------------------------------

def summarize_scene_plan(project: VideoProject) -> str:
    lines = [f"Topic: {project.topic}", f"Pilot ID: {project.pilot_id}"]
    for scene in project.scenes:
        lines.append(
            f"Scene {scene.index}: {scene.title} ({scene.start_time:.0f}s - {scene.end_time:.0f}s)"
        )
    return "\n".join(lines)


def ensure_question_set(project: VideoProject) -> VideoProject:
    """
    Guarantee four assessment questions. If fewer are present, pad with placeholders.
    """
    while len(project.assessment_questions) < 4:
        project.assessment_questions.append(
            AssessmentQuestion(
                question=f"Placeholder question {len(project.assessment_questions) + 1}",
                options=["Option A", "Option B", "Option C", "Option D"],
                correct_answer="A",
                explanation="Placeholder explanation.",
                kind="post",
            )
        )
    return project


def prepare_final_project(
    topic: str,
    pilot_id: str,
    chosen_pitch: str,
    curriculum_text: str,
    raw_script_output: str,
    target_duration_sec: int = 90,
) -> VideoProject:
    project = build_video_project_from_prompt(
        topic=topic,
        pilot_id=pilot_id,
        chosen_pitch=chosen_pitch,
        curriculum_text=curriculum_text,
        raw_script_output=raw_script_output,
        target_duration_sec=target_duration_sec,
    )
    project = auto_fill_scene_details(project)
    project = ensure_question_set(project)
    project = enforce_scene_duration(project, target_duration_sec)
    project.status = "ready_for_render"
    return project
