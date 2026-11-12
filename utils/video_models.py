"""
utils/video_models.py

Canonical data contracts for The Vault story-to-video production pipeline.

This module defines:
- VideoProject: the complete project being produced from a pitch + curriculum
- ScriptScene: one segment of the 90-second micro-documentary
- AssessmentQuestion: one MCQ question in the export package
- RenderArtifact: final output metadata for generated audio/video/subtitles
- Parsing helpers for raw LLM output from Page 3

Why this exists:
- Prevents fragile ad-hoc parsing and session-state strings
- Standardizes timing, scene transitions, and downstream render expectations
- Makes it easy to validate a project before generating audio/visuals
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# CORE DATA MODELS
# ---------------------------------------------------------------------------

@dataclass
class ScriptScene:
    index: int
    start_time: float
    end_time: float
    title: str = ""
    visual_prompt: str = ""
    narration: str = ""
    on_screen_text: Optional[str] = None
    asset_keywords: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "title": self.title,
            "visual_prompt": self.visual_prompt,
            "narration": self.narration,
            "on_screen_text": self.on_screen_text,
            "asset_keywords": list(self.asset_keywords),
        }

    def validate(self) -> List[str]:
        issues: List[str] = []
        if self.end_time <= self.start_time:
            issues.append(f"Scene {self.index}: end_time must be greater than start_time.")
        if not self.title.strip():
            issues.append(f"Scene {self.index}: title is empty.")
        if not self.narration.strip():
            issues.append(f"Scene {self.index}: narration is empty.")
        return issues


@dataclass
class AssessmentQuestion:
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    kind: str = "post"  # "pre" or "post"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "options": list(self.options),
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "kind": self.kind,
        }

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not self.question.strip():
            issues.append("Question text is empty.")
        if len(self.options) != 4:
            issues.append(f"Question '{self.question[:60]}...' must have exactly 4 options.")
        for idx, opt in enumerate(self.options):
            if not opt.strip():
                issues.append(f"Question '{self.question[:60]}...' option {idx + 1} is empty.")
        if self.correct_answer.strip().upper() not in {"A", "B", "C", "D"}:
            issues.append(f"Question '{self.question[:60]}...' has invalid correct answer: {self.correct_answer!r}")
        return issues


@dataclass
class RenderArtifact:
    video_path: str = ""
    audio_path: str = ""
    subtitle_path: str = ""
    asset_manifest_path: str = ""
    status: str = "draft"  # queued, rendering, rendered, failed, mocked
    resolution: str = "1080x1920"
    aspect_ratio: str = "9:16"
    duration_seconds: float = 0.0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_path": self.video_path,
            "audio_path": self.audio_path,
            "subtitle_path": self.subtitle_path,
            "asset_manifest_path": self.asset_manifest_path,
            "status": self.status,
            "resolution": self.resolution,
            "aspect_ratio": self.aspect_ratio,
            "duration_seconds": self.duration_seconds,
            "notes": list(self.notes),
        }


@dataclass
class VideoProject:
    """
    Represents one story-to-video production package:
    - The selected conceptual pitch
    - The source curriculum snippet
    - A 5-scene script manifest for a ~90s micro-doc
    - 4 MCQ assessment items
    - Render metadata
    """
    topic: str
    pilot_id: str
    target_duration_sec: int = 90
    selected_pitch_title: str = ""
    selected_pitch_text: str = ""
    source_curriculum_snippet: str = ""

    scenes: List[ScriptScene] = field(default_factory=list)
    assessment_questions: List[AssessmentQuestion] = field(default_factory=list)

    status: str = "draft"
    render: Optional[RenderArtifact] = None

    # Optional metadata for tracking and debugging
    raw_llm_output: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "pilot_id": self.pilot_id,
            "target_duration_sec": self.target_duration_sec,
            "selected_pitch_title": self.selected_pitch_title,
            "selected_pitch_text": self.selected_pitch_text,
            "source_curriculum_snippet": self.source_curriculum_snippet,
            "scenes": [scene.to_dict() for scene in self.scenes],
            "assessment_questions": [q.to_dict() for q in self.assessment_questions],
            "status": self.status,
            "render": self.render.to_dict() if self.render else None,
            "raw_llm_output": self.raw_llm_output,
        }

    @property
    def total_scene_duration(self) -> float:
        return sum(scene.duration for scene in self.scenes)

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not self.topic.strip():
            issues.append("Project topic is empty.")
        if not self.pilot_id.strip():
            issues.append("Pilot ID is empty.")

        if not self.scenes:
            issues.append("No scenes defined for this project.")
        else:
            for scene in self.scenes:
                issues.extend(scene.validate())
            total = self.total_scene_duration
            if abs(total - self.target_duration_sec) > 12:
                issues.append(
                    f"Scene timing total ({total:.1f}s) is too far from target duration ({self.target_duration_sec}s)."
                )

        if len(self.assessment_questions) != 4:
            issues.append(f"Expected 4 assessment questions, found {len(self.assessment_questions)}.")

        for q in self.assessment_questions:
            issues.extend(q.validate())

        return issues

    def add_scene(self, scene: ScriptScene) -> None:
        self.scenes.append(scene)

    def add_question(self, question: AssessmentQuestion) -> None:
        self.assessment_questions.append(question)

    def get_scene_by_index(self, index: int) -> Optional[ScriptScene]:
        for scene in self.scenes:
            if scene.index == index:
                return scene
        return None


# ---------------------------------------------------------------------------
# FACTORY HELPERS
# ---------------------------------------------------------------------------

def make_default_video_project(
    topic: str,
    pilot_id: str,
    target_duration_sec: int = 90,
    selected_pitch_title: str = "",
    selected_pitch_text: str = "",
    source_curriculum_snippet: str = "",
) -> VideoProject:
    return VideoProject(
        topic=topic,
        pilot_id=pilot_id,
        target_duration_sec=target_duration_sec,
        selected_pitch_title=selected_pitch_title,
        selected_pitch_text=selected_pitch_text,
        source_curriculum_snippet=source_curriculum_snippet,
    )


# ---------------------------------------------------------------------------
# RAW LLM OUTPUT PARSERS
# ---------------------------------------------------------------------------

def _to_seconds(mmss: str) -> float:
    text = mmss.strip()
    if ":" not in text:
        raise ValueError(f"Invalid timestamp format: {text!r}")
    minutes, seconds = text.split(":", 1)
    return int(minutes) * 60 + int(seconds)


def parse_scene_blocks(raw_text: str) -> List[ScriptScene]:
    """
    Parse raw model output that looks like:

    === SCRIPT MANIFEST ===
    Scene 1 (00:00 - 00:15): Hook
    [VISUAL] ...
    [VO] ...
    ...

    This is intentionally tolerant of different formatting styles used by Gemini.
    """
    scenes: List[ScriptScene] = []
    lines = raw_text.splitlines()

    current: Optional[ScriptScene] = None

    def flush_current() -> None:
        nonlocal current
        if current is not None:
            scenes.append(current)
            current = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Scene header like "Scene 1 (00:00 - 00:15): Hook & Setup"
        match = re.match(
            r"^Scene\s+(\d+)\s*\((\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\)\s*:?(.+)?$",
            stripped,
            re.IGNORECASE,
        )
        if match:
            flush_current()
            idx = int(match.group(1))
            start = _to_seconds(match.group(2))
            end = _to_seconds(match.group(3))
            title = (match.group(4) or "").strip()
            current = ScriptScene(
                index=idx,
                start_time=start,
                end_time=end,
                title=title,
                visual_prompt="",
                narration="",
            )
            continue

        if current is None:
            continue

        if stripped.lower().startswith("[visual]"):
            current.visual_prompt = stripped[len("[visual]"):].strip()
            continue

        if stripped.lower().startswith("[vo]"):
            current.narration = stripped[len("[vo]"):].strip()
            continue

        if ":" in stripped and stripped.split(":", 1)[0].lower() in {"visual", "voiceover", "narration", "caption"}:
            label, val = stripped.split(":", 1)
            label = label.strip().lower()
            if label in {"visual"}:
                current.visual_prompt = val.strip()
            elif label in {"voiceover", "narration"}:
                current.narration = val.strip()
            elif label == "caption":
                current.on_screen_text = val.strip()
            continue

        if current.title == "":
            current.title = stripped
        elif current.visual_prompt == "":
            current.visual_prompt = stripped
        else:
            current.narration = (current.narration + " " + stripped).strip()

    flush_current()
    return scenes


def parse_mcq_block(raw_text: str) -> List[AssessmentQuestion]:
    """
    Parse a raw assessment block with format:

    Question: ...
    A) ...
    B) ...
    C) ...
    D) ...
    Correct Answer: A
    Explanation: ...

    Returns a list of AssessmentQuestion objects.
    """
    questions: List[AssessmentQuestion] = []
    lines = raw_text.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.lower().startswith("question:"):
            q_text = line[len("Question:"):].strip()
            options: List[str] = []
            correct_answer = ""
            explanation = ""
            kind = "post"

            j = i + 1
            while j < len(lines):
                candidate = lines[j].strip()
                if candidate.lower().startswith("question:"):
                    break

                if re.match(r"^[A-D]\)", candidate):
                    options.append(candidate.split(")", 1)[1].strip())
                elif candidate.lower().startswith("correct answer:"):
                    correct_answer = candidate.split(":", 1)[1].strip().upper()
                elif candidate.lower().startswith("explanation:"):
                    explanation = candidate.split(":", 1)[1].strip()
                elif candidate.lower().startswith("kind:"):
                    kind = candidate.split(":", 1)[1].strip().lower()
                j += 1

            if q_text:
                questions.append(
                    AssessmentQuestion(
                        question=q_text,
                        options=options[:4],
                        correct_answer=correct_answer.strip().upper(),
                        explanation=explanation,
                        kind=kind,
                    )
                )

            i = j
            continue

        i += 1

    return questions


def parse_project_from_llm_output(raw_output: str, topic: str, pilot_id: str, target_duration_sec: int = 90) -> VideoProject:
    """
    Full parser that turns the combined script + assessment output into a VideoProject.
    """
    project = VideoProject(
        topic=topic,
        pilot_id=pilot_id,
        target_duration_sec=target_duration_sec,
        raw_llm_output=raw_output,
    )

    markers = [
        "=== SCRIPT MANIFEST ===",
        "=== ASSESSMENT PACKAGE ===",
        "SECTION 2:",
        "CALIBRATED ASSESSMENT PACKAGE",
        "ASSESSMENT PACKAGE:",
    ]

    split_idx = None
    for marker in markers:
        idx = raw_output.lower().find(marker.lower())
        if idx != -1:
            split_idx = idx
            break

    if split_idx is None:
        script_text = raw_output.strip()
        assessment_text = ""
    else:
        script_text = raw_output[:split_idx].strip()
        assessment_text = raw_output[split_idx:].strip()

    project.scenes = parse_scene_blocks(script_text)
    project.assessment_questions = parse_mcq_block(assessment_text)

    if len(project.assessment_questions) < 4 and assessment_text == "":
        project.assessment_questions = parse_mcq_block(raw_output)

    project.status = "parsed" if project.scenes or project.assessment_questions else "draft"
    return project


def normalize_answer_letter(letter: str) -> str:
    cleaned = (letter or "").strip().upper()
    if cleaned in {"A", "B", "C", "D"}:
        return cleaned
    return cleaned[0].upper() if cleaned else ""


if __name__ == "__main__":
    sample = """
    === SCRIPT MANIFEST ===
    Scene 1 (00:00 - 00:15): Hook & Setup
    [VISUAL] A dramatic classroom shot with rising tension.
    [VO] The key idea is simple: incentives shape behavior.

    Scene 2 (00:15 - 00:35): The Core Problem
    [VISUAL] A chart comparing costs and rewards.
    [VO] When the reward changes, the decision changes too.

    === ASSESSMENT PACKAGE ===
    Question: Which statement best explains the main idea?
    A) People always act rationally.
    B) Incentives influence behavior.
    C) Prices never change.
    D) Students do not respond to rewards.
    Correct Answer: B
    Explanation: Incentives shape decisions.

    Question: What is one likely effect of a policy change?
    A) Nothing changes.
    B) People may respond differently.
    C) Incentives disappear.
    D) Everyone stops learning.
    Correct Answer: B
    Explanation: Behavioral response is common.
    """

    project = parse_project_from_llm_output(sample, topic="Sample Topic", pilot_id="P01")
    print(project)
    print(project.validate())
