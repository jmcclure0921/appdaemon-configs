"""Vision detector selection.

`get_detector()` returns the configured `VisionDetector`. Today it always
returns the stub; wire in a real detector via the `SHELFMAPPER_VISION`
environment variable once one exists.
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
    raise ValueError(f"Unknown vision backend: {backend!r}")
