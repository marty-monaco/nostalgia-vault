from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

@dataclass
class ScriptScene:
    index: int
    start_time: float
    end_time: float
    title: str
    visual_prompt: str
    narration: str
    on_screen_text: Optional[str] = None
    asset_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AssessmentQuestion:
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    kind: str = "post"  # or "pre"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class VideoProject:
    topic: str
    pilot_id: str
    target_duration_sec: int = 90
    selected_pitch_title: str = ""
    selected_pitch_text: str = ""
    source_curriculum_snippet: str = ""
    scenes: List[ScriptScene] = field(default_factory=list)
    assessment_questions: List[AssessmentQuestion] = field(default_factory=list)
    status: str = "draft"

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
        }

    def total_scene_duration(self) -> float:
        return sum(scene.end_time - scene.start_time for scene in self.scenes)

    def validate_timing(self) -> List[str]:
        issues: List[str] = []
        if not self.scenes:
            issues.append("No scenes defined.")
            return issues

        total = self.total_scene_duration()
        if abs(total - self.target_duration_sec) > 10:
            issues.append(
                f"Scene timing total ({total:.1f}s) deviates from target ({self.target_duration_sec}s)."
            )

        for scene in self.scenes:
            if scene.end_time <= scene.start_time:
                issues.append(f"Scene {scene.index} has invalid timing.")
        return issues
