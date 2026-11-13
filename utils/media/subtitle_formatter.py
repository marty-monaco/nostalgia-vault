"""
Subtitle generation for The Vault.

Supports TTS-aligned cues and a sentence-timing fallback. Markdown terms
written as **term** are converted to styled ASS text.

Timestamps may be dictionaries with:
    {"start_time": 0.0, "end_time": 2.5, "text": "Narration cue"}

If end_time is omitted, the next cue's start_time (or the video duration
for the last cue) is used.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


_TERM_PATTERN = re.compile(r"\*\*(.+?)\*\*")
_SENTENCE_PATTERN = re.compile(r".+?(?:[.!?]+(?=\s|$)|$)", re.DOTALL)


def generate_styled_ass(
    script_text: str,
    duration_sec: float,
    output_path: str = "subtitles.ass",
    timestamps: Optional[Sequence[Dict[str, Any]]] = None,
    resolution: Tuple[int, int] = (1080, 1920),
) -> str:
    """
    Write an ASS subtitle file and return its path.

    Args:
        script_text: Narration text. `**term**` markup is highlighted.
        duration_sec: Final audio/video duration in seconds.
        output_path: Destination `.ass` file.
        timestamps: Optional TTS alignment cues. Each cue should have
            `start_time`, `text`, and optionally `end_time`.
        resolution: ASS play resolution, defaulting to vertical 1080x1920.

    Raises:
        ValueError: If duration or resolution is invalid.
    """
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
    """Validate and clamp provider cues, or estimate sentence-level cues."""
    if timestamps:
        prepared = []
        for cue in timestamps:
            if not isinstance(cue, dict):
                continue
            text = str(cue.get("text", "")).strip()
            if not text:
                continue
            start = _as_seconds(cue.get("start_time"), default=0.0)
            end_value = cue.get("end_time")
            end = _as_seconds(end_value, default=-1.0) if end_value is not None else -1.0
            prepared.append((start, end, text))

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


def _as_seconds(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _estimate_sentence_cues(
    script_text: str,
    duration_sec: float,
) -> List[Tuple[float, float, str]]:
    """
    Estimate sentence timings proportionally by word count.

    This is only a fallback. Use actual TTS alignment cues for production
    captions, since pauses and delivery speed vary.
    """
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
        end = (
            duration_sec
            if index == len(sentences) - 1
            else cursor + duration_sec * weight / total_weight
        )
        cues.append((cursor, end, sentence))
        cursor = end

    return cues


def _format_ass_text(text: str) -> str:
    """Escape literal ASS control characters and style `**term**` spans."""
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
    # ASS uses braces for override tags and backslashes for control sequences.
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
    """Format seconds as ASS H:MM:SS.cc."""
    total_centiseconds = max(0, round(seconds * 100))
    centiseconds = total_centiseconds % 100
    total_seconds = total_centiseconds // 100
    hours, remainder = divmod(total_seconds, 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"
