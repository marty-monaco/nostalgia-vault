"""
Generate subtitle files from the narration cues and scene timing.

This format is intentionally compatible with ASS subtitles, making it easy to
pair with dynamic keyword highlighting later.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .models import NarrationCue, VideoProject


def _sec_to_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:01d}:{m:02d}:{s:05.2f}"


def generate_subtitles(project: VideoProject, output_path: str = "subtitles.ass") -> str:
    """
    Build a simple ASS subtitle file with one event per narration cue.
    This is a first-pass implementation, not a full subtitle engine.
    """
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Align, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,320,1
Style: Highlight,Arial,56,&H00FFFF00,&H000000FF,&H00000000,&H001A1A1A,-1,0,0,0,105,105,1,0,3,6,0,2,80,80,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events: List[str] = []

    for cue in project.narration_cues:
        normalized = cue.text.strip()
        if not normalized:
            continue

        # Highlight key terms using simple **term** syntax
        formatted = re.sub(r"\*\*(.*?)\*\*", r"{\\c&H00FFFF&\\fs56\\b1}\\1{\\r}", normalized)

        events.append(
            f"Dialogue: 0,{_sec_to_ass_time(cue.start_time)},{_sec_to_ass_time(cue.end_time)},"
            f"Default,,0,0,0,,{formatted}"
        )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(ass_header + "\n".join(events), encoding="utf-8")

    project.subtitles_path = str(out.resolve())
    return str(out.resolve())
