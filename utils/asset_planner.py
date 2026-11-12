from __future__ import annotations
from typing import List, Dict, Any

def plan_scene_assets(scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output = []
    for scene in scenes:
        output.append({
            "scene_index": scene.get("index", 0),
            "prompt": scene.get("visual_prompt") or "cinematic educational explainer, clean visuals",
            "duration_sec": max(1.0, float(scene.get("end_time", 0)) - float(scene.get("start_time", 0))),
            "caption": scene.get("on_screen_text") or scene.get("title") or "Explainer visual",
            "asset_keywords": scene.get("asset_keywords", []),
            "status": "planned",
        })
    return output
