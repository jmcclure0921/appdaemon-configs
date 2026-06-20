"""A deterministic stub detector.

It fabricates a plausible aisle-by-aisle walk of grocery products spread across
the session's duration, seeded by the session id so results are reproducible.
This lets the full ingest → map → optimize loop run with no GPU or paid API.
Replace it with a real `VisionDetector` (see base.py) when ready.
"""
from __future__ import annotations

import hashlib
from typing import Optional

from .base import RawDetection

# A small synthetic catalog grouped the way a store is laid out: items near each
# other in this list are detected near each other in time (i.e. same aisle).
_CATALOG: list[tuple[str, str, float]] = [
    ("Bananas", "produce", 0.59),
    ("Gala Apples", "produce", 1.29),
    ("Baby Spinach", "produce", 2.99),
    ("Roma Tomatoes", "produce", 1.49),
    ("Whole Milk", "dairy", 3.49),
    ("2% Milk", "dairy", 3.49),
    ("Large Eggs", "dairy", 2.99),
    ("Cheddar Cheese", "dairy", 4.99),
    ("Greek Yogurt", "dairy", 1.19),
    ("Chicken Breast", "meat", 6.99),
    ("Ground Beef", "meat", 5.49),
    ("Bacon", "meat", 5.99),
    ("White Bread", "bakery", 2.49),
    ("Bagels", "bakery", 3.29),
    ("Spaghetti", "pantry", 1.29),
    ("Marinara Sauce", "pantry", 2.79),
    ("Jasmine Rice", "pantry", 4.49),
    ("Black Beans", "pantry", 0.99),
    ("Peanut Butter", "pantry", 3.99),
    ("Potato Chips", "snacks", 3.49),
    ("Orange Juice", "beverages", 3.99),
    ("Sparkling Water", "beverages", 4.29),
    ("Vanilla Ice Cream", "frozen", 4.99),
    ("Frozen Pizza", "frozen", 5.99),
    ("Paper Towels", "household", 7.99),
    ("Dish Soap", "household", 2.99),
]


def _seed(session_id: str) -> int:
    return int(hashlib.sha256(session_id.encode()).hexdigest(), 16)


class StubVisionDetector:
    """Generates reproducible detections covering the catalog."""

    def detect(
        self,
        *,
        session_id: str,
        duration_ms: int,
        video: Optional[bytes],
    ) -> list[RawDetection]:
        if video is None or duration_ms <= 0:
            return []

        seed = _seed(session_id)
        # Rotate the catalog start so different sessions of the same store still
        # agree on relative ordering but begin at a slightly different point.
        offset = seed % len(_CATALOG)
        ordered = _CATALOG[offset:] + _CATALOG[:offset]

        detections: list[RawDetection] = []
        n = len(ordered)
        for i, (label, category, price) in enumerate(ordered):
            # Spread products evenly across the walk, with a little jitter.
            base = (i + 0.5) / n
            jitter = ((seed >> i) & 0xFF) / 255.0 - 0.5  # in [-0.5, 0.5]
            frac = min(0.999, max(0.0, base + jitter * (0.4 / n)))
            t_ms = int(frac * duration_ms)
            confidence = 0.75 + ((seed >> (i + 8)) & 0x3F) / 255.0  # ~0.75..1.0
            detections.append(
                RawDetection(
                    t_ms=t_ms,
                    label=label,
                    raw_text=f"{label.upper()}  ${price:.2f}",
                    category=category,
                    price=price,
                    confidence=round(min(0.99, confidence), 3),
                )
            )
        detections.sort(key=lambda d: d.t_ms)
        return detections
