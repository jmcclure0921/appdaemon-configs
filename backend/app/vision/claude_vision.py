"""A real `VisionDetector` backed by a Claude multimodal model.

Each sampled video frame is sent to the model, which reads the shelf price tags
and identifies the products visible, returning a structured list (name, category,
price, confidence) via the Messages API's structured-output support. This folds
OCR and product understanding into one call, so there's no separate text-parsing
stage.

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

# Collapse the same product seen across consecutive frames into one detection.
_DEDUP_WINDOW_MS = 4_000

_SYSTEM_PROMPT = (
    "You are a grocery shelf scanner. You are shown a single still frame from a "
    "video of someone walking down a store aisle. Identify the distinct products "
    "visible on the shelves, reading the shelf price tags for the product name and "
    "price where legible.\n"
    "Rules:\n"
    "- Only report products that are clearly on a shelf in THIS frame.\n"
    "- Normalize each name to a concise product name (e.g. '2% Milk', not the full "
    "tag text). Put the raw tag text, if any, in raw_text.\n"
    "- category: a short aisle-style category (produce, dairy, meat, bakery, "
    "pantry, frozen, beverages, snacks, household), or null if unsure.\n"
    "- price: the shelf price as a number, or null if not legible.\n"
    "- confidence: 0..1 for how sure you are the product is present and identified.\n"
    "- If no products are clearly visible, return an empty list."
)


class ProductReading(BaseModel):
    """One product the model saw in a frame."""

    name: str
    raw_text: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    # No range constraint: structured outputs ignore min/max, and we'd rather
    # accept a stray value than fail validation on a whole frame. Clamped below.
    confidence: float = 0.5


class FrameProducts(BaseModel):
    products: list[ProductReading] = Field(default_factory=list)


# A frame sampler: (video_bytes, duration_ms) -> frames. Injectable for tests.
Sampler = Callable[[bytes, int], list[Frame]]


def _default_sampler(video: bytes, duration_ms: int) -> list[Frame]:
    return sample_frames(video)


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
                key = " ".join(reading.name.lower().split())
                prev = last_seen.get(key)
                last_seen[key] = frame.t_ms
                # Skip a product already reported in a recent nearby frame.
                if prev is not None and frame.t_ms - prev < _DEDUP_WINDOW_MS:
                    continue
                detections.append(
                    RawDetection(
                        t_ms=frame.t_ms,
                        label=reading.name.strip(),
                        raw_text=reading.raw_text,
                        category=reading.category,
                        price=reading.price,
                        confidence=max(0.0, min(1.0, reading.confidence)),
                    )
                )

        detections.sort(key=lambda d: d.t_ms)
        return detections

    def _read_frame(self, jpeg: bytes) -> list[ProductReading]:
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
                        {"type": "text", "text": "List the products on the shelves."},
                    ],
                }
            ],
            output_format=FrameProducts,
        )
        parsed = response.parsed_output
        return parsed.products if parsed else []
