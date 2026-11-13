"""
Subtitle generation for The Vault.

Supports TTS-aligned cues and a sentence-timing fallback.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_TERM_PATTERN = re.compile(r"\*\*(.+?)\*\*")
_SENTENCE_PATTERN = re.compile(r".+?(?:[.!?]+(?=\s|$)|$)", re.DOTALL)

def generate_styled_ass(
    script_text: str,
    duration_sec: float,
    output_path: str = "subtitles.ass",
    timestamps: Optional[Sequence[Dict[str, Any]]] = None,
    resolution: Tuple[int, int] = (1080, 1920),
) -> str:
    if duration_sec <= 0:
        raise ValueError("duration_sec must be greater than zero.")
    if len(resolution) != 2 or any(int(dimension) <= 0 for dimension in resolution):
        raise ValueError("resolution must contain two positive dimensions.")

    cues = _normalise_cues(script_text, duration_sec, timestamps)
    header = _build_header(int(resolution[0]), int(resolution[1]))
    events = []

    for start, end, text in cues:
        if not text.strip() or end <= start:
            continue
        events.append(
            "Dialogue: 0,"
            f"{_sec_to_ass_time(start)},{_sec_to_ass_time(end)},"
            "Default,,0,0,0,,"
            f"{_format_ass_text(text)}"
        )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        header + "\n".join(events) + ("\n" if events else ""),
        encoding="utf-8",
    )
    return str(destination)


def _normalise_cues(
    script_text: str,
    duration_sec: float,
    timestamps: Optional[Sequence[Dict[str, Any]]],
) -> List[Tuple[float, float, str]]:
    if timestamps:
        prepared = []
        for cue in timestamps:
            if not isinstance(cue, dict):
                continue
            text = str(cue.get("text", "")).strip()
            if not text:
                continue
            start = float(cue.get("start_time", 0.0) or 0.0)
            end = cue.get("end_time")
            end_value = float(end) if end is not None else -1.0
            prepared.append((start, end_value, text))
        prepared.sort(key=lambda item: item[0])
        normalised = []
        for index, (start, end, text) in enumerate(prepared):
            if end <= start:
                if index + 1 < len(prepared):
                    end = prepared[index + 1][0]
                else:
                    end = duration_sec
            start = max(0.0, min(float(start), duration_sec))
            end = max(0.0, min(float(end), duration_sec))
            if end > start:
                normalised.append((start, end, text))
        if normalised:
            return normalised

    return _estimate_sentence_cues(script_text, duration_sec)


def _estimate_sentence_cues(
    script_text: str,
    duration_sec: float,
) -> List[Tuple[float, float, str]]:
    sentences = [
        match.group(0).strip()
        for match in _SENTENCE_PATTERN.finditer(script_text.strip())
        if match.group(0).strip()
    ]
    if not sentences:
        return []

    weights = [max(1, len(sentence.split())) for sentence in sentences]
    total_weight = sum(weights)
    cursor = 0.0
    cues = []

    for index, (sentence, weight) in enumerate(zip(sentences, weights)):
        end = duration_sec if index == len(sentences) - 1 else cursor + duration_sec * weight / total_weight
        cues.append((cursor, end, sentence))
        cursor = end

    return cues


def _format_ass_text(text: str) -> str:
    parts = []
    cursor = 0
    for match in _TERM_PATTERN.finditer(text):
        parts.append(_escape_ass_text(text[cursor:match.start()]))
        term = _escape_ass_text(match.group(1))
        parts.append(r"{\c&H00FFFF&\fs66\b1}" + term + r"{\r}")
        cursor = match.end()
    parts.append(_escape_ass_text(text[cursor:]))
    return "".join(parts).replace("\r\n", "\n").replace("\r", "\n").replace("\n", r"\N")


def _escape_ass_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def _build_header(play_res_x: int, play_res_y: int) -> str:
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,54,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,70,70,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _sec_to_ass_time(seconds: float) -> str:
    total_centiseconds = max(0, round(seconds * 100))
    centiseconds = total_centiseconds % 100
    total_seconds = total_centiseconds // 100
    hours, remainder = divmod(total_seconds, 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"
