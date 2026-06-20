"""The vision boundary.

A `VisionDetector` consumes a recorded session (video bytes + duration) and
returns timestamped product detections. Pinning detections to physical
locations is *not* the detector's job — that happens in `mapping.py` using the
recorded path. This keeps the vision model swappable: implement one method to
plug in a cloud vision API or a trained on-device model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class RawDetection:
    """A product observed at a moment in the video, before it is located."""

    t_ms: int
    label: str
    raw_text: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
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
