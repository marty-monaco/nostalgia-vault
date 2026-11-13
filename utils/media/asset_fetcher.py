"""
Visual asset planning and retrieval boundary for The Vault.

The default mock path creates valid placeholder PNG images locally. A real
provider can be supplied later without changing the downstream scene format.
"""

from __future__ import annotations

import hashlib
import json
import struct
import zlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

AssetProvider = Callable[[Dict[str, Any], Path], Dict[str, Any]]

def fetch_visual_assets(
    storyboard_prompts: List[Dict[str, Any]],
    use_mock: bool = True,
    output_dir: str = "build/assets",
    provider: Optional[AssetProvider] = None,
) -> List[Dict[str, Any]]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for position, prompt_info in enumerate(storyboard_prompts, start=1):
        info = prompt_info if isinstance(prompt_info, dict) else {}
        scene_index = _scene_index(info, position)
        prompt = str(info.get("prompt") or info.get("visual_prompt") or "").strip()
        caption = str(info.get("caption") or info.get("on_screen_text") or info.get("title") or "").strip()
        duration = _scene_duration(info)
        keywords = info.get("asset_keywords") or []

        base = {
            "scene_index": scene_index,
            "prompt": prompt,
            "duration": duration,
            "caption": caption,
            "asset_keywords": list(keywords) if isinstance(keywords, (list, tuple)) else [],
        }

        if info.get("image_path") and Path(str(info["image_path"])).is_file():
            results.append({
                **base,
                "image_path": str(Path(str(info["image_path"])).resolve()),
                "status": "ready",
                "source": info.get("source", "local"),
                "license": info.get("license", ""),
                "attribution": info.get("attribution", ""),
            })
            continue

        if provider is not None:
            try:
                provided = provider(info, destination)
                if not isinstance(provided, dict) or not provided.get("image_path"):
                    raise ValueError("Provider must return a dictionary with an image_path.")
                image_path = Path(str(provided["image_path"]))
                if not image_path.is_file():
                    raise FileNotFoundError(f"Provider output does not exist: {image_path}")
                results.append({
                    **base,
                    **provided,
                    "scene_index": scene_index,
                    "image_path": str(image_path.resolve()),
                    "status": "ready",
                    "source": provided.get("source", "provider"),
                    "license": provided.get("license", ""),
                    "attribution": provided.get("attribution", ""),
                })
            except Exception as exc:
                results.append({
                    **base,
                    "image_path": "",
                    "status": "failed",
                    "error": str(exc),
                })
            continue

        if use_mock:
            image_path = destination / f"mock_frame_{scene_index:02d}.png"
            _write_placeholder_png(image_path, prompt or caption or f"Scene {scene_index}")
            results.append({
                **base,
                "image_path": str(image_path.resolve()),
                "status": "mocked",
                "source": "generated placeholder",
                "license": "placeholder; not a production visual",
                "attribution": "",
            })
        else:
            results.append({
                **base,
                "image_path": "",
                "status": "unavailable",
                "error": "No local image or asset provider was supplied.",
            })

    return results


def write_asset_manifest(assets: List[Dict[str, Any]], output_path: str) -> str:
    manifest_path = Path(output_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(assets, indent=2), encoding="utf-8")
    return str(manifest_path.resolve())


def _scene_index(info: Dict[str, Any], fallback: int) -> int:
    try:
        return int(info.get("scene_index", info.get("index", fallback)))
    except (TypeError, ValueError):
        return fallback


def _scene_duration(info: Dict[str, Any]) -> float:
    if info.get("duration_sec") is not None:
        value = info["duration_sec"]
    elif info.get("duration") is not None:
        value = info["duration"]
    elif info.get("start_time") is not None and info.get("end_time") is not None:
        try:
            value = float(info["end_time"]) - float(info["start_time"])
        except (TypeError, ValueError):
            value = 0
    else:
        value = 15

    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 15.0


def _write_placeholder_png(path: Path, label: str, width: int = 640, height: int = 360) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256(label.encode("utf-8")).digest()
    red = 28 + digest[0] % 80
    green = 35 + digest[1] % 80
    blue = 55 + digest[2] % 100

    row = bytes((0,)) + bytes((red, green, blue)) * width
    raw_image = row * height

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        body = chunk_type + data
        crc = zlib.crc32(body) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + body + struct.pack(">I", crc)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw_image))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)
