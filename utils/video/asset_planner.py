"""
Generate visual briefs and asset specs for each scene.

This is intentionally a planning layer that converts scenes into asset requests
for stock libraries, AI image generation, or uploaded media.
"""

from __future__ import annotations

from typing import List

from .models import AssetSpec, AssetSource, Scene, VideoProject


def plan_visual_assets(project: VideoProject) -> List[AssetSpec]:
    """
    Take each scene and convert it into a structured asset request.
    """
    assets: List[AssetSpec] = []

    for scene in project.scenes:
        asset = AssetSpec(
            scene_index=scene.scene_index,
            asset_type="background_visual",
            source=AssetSource.MOCK,
            prompt=scene.asset_prompt or scene.visual_prompt,
            caption=scene.caption or scene.on_screen_text,
            status="planned",
        )
        assets.append(asset)

    project.asset_specs = assets
    return assets


def build_scene_asset_library(project: VideoProject) -> List[AssetSpec]:
    """
    A compatibility wrapper for later providers.
    """
    return plan_visual_assets(project)
