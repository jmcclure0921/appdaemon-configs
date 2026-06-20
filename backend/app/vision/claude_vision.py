"""A real `VisionDetector` backed by a Claude multimodal model.

The goal is route optimization, so each sampled frame is classified by the
*store section* it shows (dairy, produce, frozen, …) plus a few example items —
not prices or exact SKUs. The model returns this as structured output in one
call. Section recognition works from an ordinary walking video, so the shopper
doesn't need to stop and scan tags.

Locating detections in the store is *not* this class's job — it emits timestamped
`RawDetection`s and `mapping.py` pins them to the recorded path.

Configuration (environment):
- `ANTHROPIC_API_KEY`         required by the Anthropic SDK.
- `SHELFMAPPER_VISION_MODEL`  model id; defaults to `claude-opus-4-8`.

Cost note: this is a high-volume image-extraction workload (many frames per
session). The model is configurable so you can point it at a cheaper tier
(`claude-haiku-4-5`, `claude-sonnet-4-6`); the system prompt is prompt-cached
across frames, and the Batch API would halve cost for offline processing.
"""
from __future__ import annotations

import base64
import os
from typing import Callable, Optional

from pydantic import BaseModel, Field

from .base import RawDetection
from .frames import Frame, sample_frames

DEFAULT_MODEL = "claude-opus-4-8"

# Collapse the same section seen across consecutive frames into one detection.
_DEDUP_WINDOW_MS = 6_000

_SYSTEM_PROMPT = (
    "You map grocery stores for shopping-route planning. You are shown a single "
    "still frame from a video of someone walking through a store. Identify which "
    "store SECTION(S) the shelves in this frame belong to — we care about where "
    "sections are, not individual prices.\n"
    "Rules:\n"
    "- section: the aisle/section name as a shopper would say it, e.g. 'Dairy & "
    "Eggs', 'Produce', 'Frozen', 'Baking & Spices', 'Snacks', 'Household'.\n"
    "- category: a single normalized lowercase category (produce, dairy, meat, "
    "bakery, pantry, baking, frozen, beverages, snacks, household), or null.\n"
    "- example_items: a few specific products visible in this section (e.g. "
    "['milk', 'eggs', 'cheese']) so a shopping list can be matched to it. You do "
    "NOT need price tags to be legible — recognizing the products is enough.\n"
    "- confidence: 0..1 that the section is correctly identified.\n"
    "- Usually report ONE dominant section per frame; report two only if the frame "
    "clearly straddles an aisle boundary. If nothing is identifiable, return an "
    "empty list."
)


class SectionReading(BaseModel):
    """One store section the model saw in a frame."""

    section: str
    category: Optional[str] = None
    example_items: list[str] = Field(default_factory=list)
    # No range constraint: structured outputs ignore min/max, and we'd rather
    # accept a stray value than fail validation on a whole frame. Clamped below.
    confidence: float = 0.5


class FrameSections(BaseModel):
    sections: list[SectionReading] = Field(default_factory=list)


# A frame sampler: (video_bytes, duration_ms) -> frames. Injectable for tests.
Sampler = Callable[[bytes, int], list[Frame]]


def _default_sampler(video: bytes, duration_ms: int) -> list[Frame]:
    # Frames per second to sample. At a normal ~1 m/s walking pace, 1 fps is ~1
    # frame per meter — fine for locating products, but it can skip a small price
    # tag between frames. Raise it (e.g. 2) for better tag coverage at higher
    # per-session model cost; the detector de-dups products across frames.
    fps = float(os.environ.get("SHELFMAPPER_FRAME_FPS", "1.0"))
    return sample_frames(video, fps=fps)


class ClaudeVisionDetector:
    def __init__(
        self,
        *,
        model: Optional[str] = None,
        client: object | None = None,
        sampler: Optional[Sampler] = None,
    ) -> None:
        self.model = model or os.environ.get("SHELFMAPPER_VISION_MODEL", DEFAULT_MODEL)
        self._client = client
        self._sampler = sampler or _default_sampler

    # Lazily build the Anthropic client so importing this module (and running
    # the stub-based tests) doesn't require the SDK or an API key.
    def _get_client(self):
        if self._client is None:
            import anthropic  # imported lazily on purpose

            self._client = anthropic.Anthropic()
        return self._client

    def detect(
        self,
        *,
        session_id: str,
        duration_ms: int,
        video: Optional[bytes],
    ) -> list[RawDetection]:
        if not video:
            return []

        frames = self._sampler(video, duration_ms)
        detections: list[RawDetection] = []
        last_seen: dict[str, int] = {}

        for frame in frames:
            for reading in self._read_frame(frame.jpeg):
                key = " ".join(reading.section.lower().split())
                prev = last_seen.get(key)
                last_seen[key] = frame.t_ms
                # Skip a section already reported in a recent nearby frame.
                if prev is not None and frame.t_ms - prev < _DEDUP_WINDOW_MS:
                    continue
                detections.append(
                    RawDetection(
                        t_ms=frame.t_ms,
                        label=reading.section.strip(),
                        category=reading.category,
                        keywords=[i.strip() for i in reading.example_items if i.strip()],
                        confidence=max(0.0, min(1.0, reading.confidence)),
                    )
                )

        detections.sort(key=lambda d: d.t_ms)
        return detections

    def _read_frame(self, jpeg: bytes) -> list[SectionReading]:
        b64 = base64.standard_b64encode(jpeg).decode("ascii")
        response = self._get_client().messages.parse(
            model=self.model,
            max_tokens=2048,
            # Cache the system prompt across the many frames of a session.
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": "Which store section(s) is this?"},
                    ],
                }
            ],
            output_format=FrameSections,
        )
        parsed = response.parsed_output
        return parsed.sections if parsed else []
