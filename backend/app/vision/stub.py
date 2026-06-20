"""A deterministic stub detector.

It fabricates a plausible aisle-by-aisle walk through a store's sections,
seeded by the session id so results are reproducible. Each section carries a
few example items so shopping-list matching works. This lets the full
ingest → map → optimize loop run with no GPU or paid API. Replace it with a
real `VisionDetector` (see base.py) when ready.
"""
from __future__ import annotations

import hashlib
from typing import Optional

from .base import RawDetection

# Store sections in a typical front-to-back layout: (section, category, example
# items). Items near each other in this list are detected near each other in
# time (i.e. the order you'd walk them).
_SECTIONS: list[tuple[str, str, list[str]]] = [
    ("Produce", "produce", ["bananas", "apples", "spinach", "tomatoes", "lettuce", "onions"]),
    ("Bakery", "bakery", ["bread", "bagels", "buns", "tortillas"]),
    ("Meat & Seafood", "meat", ["chicken breast", "ground beef", "bacon", "salmon"]),
    ("Dairy & Eggs", "dairy", ["milk", "eggs", "cheddar cheese", "greek yogurt", "butter"]),
    ("Frozen", "frozen", ["frozen pizza", "ice cream", "frozen vegetables", "waffles"]),
    ("Pantry & Canned", "pantry", ["spaghetti", "marinara sauce", "rice", "black beans", "peanut butter"]),
    ("Baking & Spices", "baking", ["flour", "sugar", "cinnamon", "vanilla", "baking soda"]),
    ("Snacks", "snacks", ["potato chips", "crackers", "cookies", "granola bars"]),
    ("Beverages", "beverages", ["orange juice", "sparkling water", "coffee", "soda"]),
    ("Household", "household", ["paper towels", "dish soap", "trash bags", "laundry detergent"]),
]


def _seed(session_id: str) -> int:
    return int(hashlib.sha256(session_id.encode()).hexdigest(), 16)


class StubVisionDetector:
    """Generates reproducible section detections across the walk."""

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
        n = len(_SECTIONS)
        detections: list[RawDetection] = []
        for i, (section, category, items) in enumerate(_SECTIONS):
            # Spread sections evenly across the walk, with a little jitter.
            base = (i + 0.5) / n
            jitter = ((seed >> i) & 0xFF) / 255.0 - 0.5  # in [-0.5, 0.5]
            frac = min(0.999, max(0.0, base + jitter * (0.4 / n)))
            t_ms = int(frac * duration_ms)
            confidence = 0.8 + ((seed >> (i + 8)) & 0x3F) / 512.0  # ~0.8..0.92
            detections.append(
                RawDetection(
                    t_ms=t_ms,
                    label=section,
                    category=category,
                    keywords=list(items),
                    confidence=round(min(0.99, confidence), 3),
                )
            )
        detections.sort(key=lambda d: d.t_ms)
        return detections
