"""Match free-text shopping-list items to store map entries."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Optional

from .models import MapEntry

# Below this similarity, we treat an item as unmatched rather than guess wildly.
_THRESHOLD = 0.5
# A pure character-level fuzzy match only counts at near-exact similarity, so a
# coincidental overlap (e.g. "saffron" vs "seafood") can't pull in a section.
_FUZZY_MIN = 0.85


def _tokens(s: str) -> set[str]:
    return {t for t in "".join(c if c.isalnum() else " " for c in s.lower()).split()}


def _score_one(q: str, target: str) -> float:
    """How well `q` matches a single target string (section name or example item).

    Real signal comes from shared words (token overlap) or one being a substring
    of the other. A fuzzy character ratio only contributes when it's near-exact,
    so it catches typos ("banannas") without inventing matches between unrelated
    words that happen to share letters.
    """
    t = target.lower().strip()
    qt, tt = _tokens(q), _tokens(t)
    if not qt or not tt:
        return 0.0
    overlap = len(qt & tt) / len(qt)  # fraction of the query's words covered
    substring = 1.0 if q in t or t in q else 0.0
    ratio = SequenceMatcher(None, q, t).ratio()
    fuzzy = ratio if ratio >= _FUZZY_MIN else 0.0
    return max(overlap, substring, fuzzy)


def _score(query: str, entry: MapEntry) -> float:
    """Best match of `query` against the section name, category, and example items."""
    q = query.lower().strip()
    targets = [entry.label, *entry.keywords]
    if entry.category:
        targets.append(entry.category)
    return max((_score_one(q, t) for t in targets), default=0.0)


def match_item(query: str, entries: list[MapEntry]) -> Optional[MapEntry]:
    """Return the best section for `query`, or None if nothing clears the bar."""
    best: Optional[MapEntry] = None
    best_score = 0.0
    for e in entries:
        s = _score(query, e)
        if s > best_score:
            best, best_score = e, s
    return best if best_score >= _THRESHOLD else None
