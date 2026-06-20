"""Match free-text shopping-list items to store map entries."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Optional

from .models import MapEntry

# Below this similarity, we treat an item as unmatched rather than guess wildly.
_THRESHOLD = 0.34


def _tokens(s: str) -> set[str]:
    return {t for t in "".join(c if c.isalnum() else " " for c in s.lower()).split()}


def _score(query: str, entry: MapEntry) -> float:
    """Blend token overlap, substring presence, and fuzzy ratio in [0, 1]."""
    q = query.lower().strip()
    label = entry.label.lower()
    qt, lt = _tokens(q), _tokens(label)
    if not qt:
        return 0.0

    overlap = len(qt & lt) / len(qt)  # how much of the query is covered
    substring = 1.0 if q in label or label in q else 0.0
    ratio = SequenceMatcher(None, q, label).ratio()
    category_hit = 0.0
    if entry.category and entry.category.lower() in qt:
        category_hit = 0.5

    return max(overlap, substring, ratio, category_hit) * 0.7 + min(
        overlap, 1.0
    ) * 0.3


def match_item(query: str, entries: list[MapEntry]) -> Optional[MapEntry]:
    """Return the best map entry for `query`, or None if nothing clears the bar."""
    best: Optional[MapEntry] = None
    best_score = 0.0
    for e in entries:
        s = _score(query, e)
        if s > best_score:
            best, best_score = e, s
    return best if best_score >= _THRESHOLD else None
