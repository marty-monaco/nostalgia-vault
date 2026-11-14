"""
Video production toolkit for The Vault.
This package contains the structured scene, narration, asset, subtitle, and render pipeline
used to turn a story pitch + script into a 90-second social-video artifact.
"""

from .models import (
    AssetSpec,
    NarrationCue,
    RenderResult,
    Scene,
    VideoProject,
    QualityReport,
    VideoJobStatus,
)
from .script_planner import build_video_project_from_script
from .orchestrator import VideoProductionOrchestrator

__all__ = [
    "AssetSpec",
    "NarrationCue",
    "RenderResult",
    "Scene",
    "VideoProject",
    "QualityReport",
    "VideoJobStatus",
    "build_video_project_from_script",
    "VideoProductionOrchestrator",
]
