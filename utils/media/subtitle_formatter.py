"""
utils/media/subtitle_formatter.py
Generates styled ASS subtitles highlighting bolded **keywords** in The Vault brand colors.
"""

from pathlib import Path
import re


def generate_styled_ass(script_text: str, duration_sec: float, output_path: str = "subtitles.ass") -> str:
    """
    Creates an ASS subtitle file that renders regular dialogue in white
    and bolded **terms** in highlighted cyan/gold kinetic boxes.
    """
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,54,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,320,1
Style: TermHighlight,Arial Black,64,&H00FFFF00,&H000000FF,&H00000000,&H001A1A1A,-1,0,0,0,105,105,1,0,3,6,0,2,80,80,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Regex to match **word**
    term_pattern = re.compile(r"\*\*(.*?)\*\*")

    # Format text: transform **word** into styled ASS override tags
    # \c&H00FFFF& (Cyan text), \fs62 (larger font size), followed by reset
    formatted_text = term_pattern.sub(r"{\\c&H00FFFF&\\fs66\\b1}\1{\\r}", script_text)

    # Clean display text for simple sentence pacing
    clean_lines = formatted_text.split(". ")
    time_per_line = duration_sec / max(1, len(clean_lines))

    events = []
    for i, line in enumerate(clean_lines):
        if not line.strip():
            continue
        start_t = _sec_to_ass_time(i * time_per_line)
        end_t = _sec_to_ass_time((i + 1) * time_per_line)
        events.append(f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{line.strip()}")

    ass_content = ass_header + "\n".join(events)
    Path(output_path).write_text(ass_content, encoding="utf-8")
    return output_path


def _sec_to_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:01d}:{m:02d}:{s:05.2f}"
