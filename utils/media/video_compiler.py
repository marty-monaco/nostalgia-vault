import subprocess
from pathlib import Path

def compile_micro_doc(
    audio_path: str,
    scenes: list[dict],
    output_path: str = "output_microdoc.mp4"
) -> str:
    """
    Compiles an 85-second vertical (1080x1920) micro-doc using FFmpeg.
    
    scenes: List of dicts, each containing:
      - 'image_path': str
      - 'duration': float (seconds)
      - 'caption': str
    """
    # Create an FFmpeg concat file for the video track
    concat_file = Path("concat_manifest.txt")
    with open(concat_file, "w") as f:
        for scene in scenes:
            f.write(f"file '{scene['image_path']}'\n")
            f.write(f"duration {scene['duration']}\n")
        # Ensure the last image registers its full duration
        if scenes:
            f.write(f"file '{scenes[-1]['image_path']}'\n")

    # FFmpeg command:
    # 1. Ingest image sequence from manifest.
    # 2. Scale and crop to 1080x1920 (9:16 vertical).
    # 3. Ingest ElevenLabs voiceover MP3.
    # 4. Render out web-optimized H.264 / AAC.
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", audio_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed: {result.stderr.decode('utf-8')}")

    if concat_file.exists():
        concat_file.unlink()

    return str(Path(output_path).resolve())
