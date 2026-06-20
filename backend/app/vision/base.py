"""The vision boundary.

A `VisionDetector` consumes a recorded session (video bytes + duration) and
returns timestamped product detections. Pinning detections to physical
locations is *not* the detector's job — that happens in `mapping.py` using the
recorded path. This keeps the vision model swappable: implement one method to
plug in a cloud vision API or a trained on-device model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class RawDetection:
    """A store section observed at a moment in the video, before it is located.

    The goal is route optimization, so the signal we care about is the *section*
    (dairy, produce, frozen, …), not individual products or prices. `keywords`
    holds example items seen in the section so a shopping-list entry can be
    matched to it.
    """

    t_ms: int
    label: str  # the section name, e.g. "Dairy"
    category: Optional[str] = None  # normalized aisle category
    keywords: list[str] = field(default_factory=list)  # example items in the section
    confidence: float = 0.0


class VisionDetector(Protocol):
    """Interface every detector implements."""

    def detect(
        self,
        *,
        session_id: str,
        duration_ms: int,
        video: Optional[bytes],
    ) -> list[RawDetection]:
        """Return product detections found in the session video.

        `video` may be ``None`` (e.g. metadata-only uploads in tests); a real
        detector should return an empty list in that case.
        """
        ...
