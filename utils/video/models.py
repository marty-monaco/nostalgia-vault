"""
Typed models for the video production pipeline.

These are the canonical objects used across planning, asset generation, TTS,
subtitles, render, and validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class AssetSource(str, Enum):
    MOCK = "mock"
    STOCK = "stock"
    GENERATED = "generated"
    UPLOADED = "uploaded"


class RenderStatus(str, Enum):
    PENDING = "pending"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    MOCKED = "mocked"


class VideoJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class NarrationCue:
    start_time: float
    end_time: float
    text: str
    speaker: str = "narrator"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Scene:
    scene_index: int
    title: str
    start_time: float
    end_time: float
    duration_seconds: float
    visual_prompt: str
    voiceover: str
    on_screen_text: str = ""
    caption: str = ""
    asset_prompt: str = ""
    reference_image: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AssetSpec:
    scene_index: int
    asset_type: str
    source: AssetSource
    prompt: str
    local_path: Optional[str] = None
    caption: str = ""
    status: str = "planned"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VideoProject:
    project_id: str
    topic: str
    source_text: str
    target_duration_seconds: int = 90
    aspect_ratio: str = "9:16"
    resolution: str = "1080x1920"
    scenes: List[Scene] = field(default_factory=list)
    narration_cues: List[NarrationCue] = field(default_factory=list)
    asset_specs: List[AssetSpec] = field(default_factory=list)
    voiceover_path: Optional[str] = None
    subtitles_path: Optional[str] = None
    render_path: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())

    def total_scene_duration(self) -> float:
        return sum(scene.duration_seconds for scene in self.scenes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "topic": self.topic,
            "source_text": self.source_text,
            "target_duration_seconds": self.target_duration_seconds,
            "aspect_ratio": self.aspect_ratio,
            "resolution": self.resolution,
            "scenes": [scene.to_dict() for scene in self.scenes],
            "narration_cues": [cue.to_dict() for cue in self.narration_cues],
            "asset_specs": [asset.to_dict() for asset in self.asset_specs],
            "voiceover_path": self.voiceover_path,
            "subtitles_path": self.subtitles_path,
            "render_path": self.render_path,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class RenderResult:
    render_path: Optional[str]
    status: RenderStatus
    duration_seconds: float
    resolution: str
    aspect_ratio: str
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "render_path": self.render_path,
            "status": self.status.value,
            "duration_seconds": self.duration_seconds,
            "resolution": self.resolution,
            "aspect_ratio": self.aspect_ratio,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass
class QualityReport:
    project_id: str
    passed: bool
    checks: Dict[str, bool]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "passed": self.passed,
            "checks": self.checks,
            "warnings": self.warnings,
            "errors": self.errors,
        }


@dataclass
class VideoJobStatus:
    job_id: str
    project_id: str
    status: VideoJobStatus
    progress_pct: int = 0
    message: str = ""
    artifact_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "progress_pct": self.progress_pct,
            "message": self.message,
            "artifact_path": self.artifact_path,
        }
