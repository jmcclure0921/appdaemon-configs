"""Sample still frames from a recorded video for vision processing.

Uses ffmpeg (a near-universal dependency) via subprocess so we don't pull a
heavy decoding library into the core service. Each returned frame carries the
millisecond offset into the recording, which `mapping.py` uses to look up the
walking-path position where it was filmed.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Frame:
    t_ms: int
    jpeg: bytes


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def sample_frames(video: bytes, *, fps: float = 1.0, max_frames: int = 120) -> list[Frame]:
    """Extract up to `max_frames` JPEG frames at `fps` frames per second.

    Raises RuntimeError if ffmpeg is unavailable so the caller can surface a
    clear failure rather than silently producing no detections.
    """
    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg is required for video frame sampling but was not found on PATH"
        )
    if not video:
        return []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "input.mp4"
        src.write_bytes(video)
        # %05d → frame number; -vf fps=N samples evenly across the clip.
        pattern = tmp_path / "frame_%05d.jpg"
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", str(src),
            "-vf", f"fps={fps}",
            "-frames:v", str(max_frames),
            "-q:v", "3",
            str(pattern),
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        frames: list[Frame] = []
        for i, path in enumerate(sorted(tmp_path.glob("frame_*.jpg"))):
            # Frame i was sampled at i / fps seconds into the recording.
            t_ms = int((i / fps) * 1000)
            frames.append(Frame(t_ms=t_ms, jpeg=path.read_bytes()))
        return frames
