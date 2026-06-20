"""Vision detector selection.

`get_detector()` returns the configured `VisionDetector`, chosen by the
`SHELFMAPPER_VISION` environment variable:

- `stub`   (default) — deterministic, no model or API key required.
- `claude`           — real frame-sampling + Claude multimodal extraction
                       (needs ffmpeg, the `anthropic` SDK, and ANTHROPIC_API_KEY).
"""
from __future__ import annotations

import os

from .base import RawDetection, VisionDetector
from .stub import StubVisionDetector

__all__ = ["RawDetection", "VisionDetector", "get_detector"]


def get_detector() -> VisionDetector:
    backend = os.environ.get("SHELFMAPPER_VISION", "stub").lower()
    if backend == "stub":
        return StubVisionDetector()
    if backend == "claude":
        from .claude_vision import ClaudeVisionDetector

        return ClaudeVisionDetector()
    raise ValueError(f"Unknown vision backend: {backend!r}")
