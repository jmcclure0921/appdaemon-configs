"""Pin detections to locations and aggregate per-store maps."""
from __future__ import annotations

import uuid
from collections import defaultdict

from .geo import resolve_path
from .models import Detection, MapEntry, PathPoint, Point, StoreMap
from .vision import RawDetection


def locate_detections(
    session_id: str,
    raw: list[RawDetection],
    path: list[PathPoint],
) -> list[Detection]:
    """Place each raw detection at the path position for its frame time."""
    resolved = resolve_path(path)
    located: list[Detection] = []
    for r in raw:
        pos, dist = resolved.at(r.t_ms)
        located.append(
            Detection(
                id=str(uuid.uuid4()),
                session_id=session_id,
                t_ms=r.t_ms,
                label=r.label,
                category=r.category,
                keywords=list(r.keywords),
                confidence=r.confidence,
                position=pos,
                path_distance_m=dist,
            )
        )
    return located


def _norm(label: str) -> str:
    return " ".join(label.lower().split())


def build_map(store_id: str, detections: list[Detection]) -> StoreMap:
    """Aggregate detections (across all of a store's sessions) into a section map.

    Observations of the same section are averaged: position is a
    confidence-weighted centroid and path distance a confidence-weighted mean,
    smoothing out per-session GPS noise. Example items seen in the section are
    unioned into `keywords` so shopping-list entries can be matched to it.
    """
    groups: dict[str, list[Detection]] = defaultdict(list)
    for d in detections:
        groups[_norm(d.label)].append(d)

    entries: list[MapEntry] = []
    for dets in groups.values():
        wsum = sum(max(d.confidence, 1e-6) for d in dets)
        cx = sum(d.position.x * max(d.confidence, 1e-6) for d in dets) / wsum
        cy = sum(d.position.y * max(d.confidence, 1e-6) for d in dets) / wsum
        cdist = sum(d.path_distance_m * max(d.confidence, 1e-6) for d in dets) / wsum
        # Use the most confident original spelling for display.
        label = max(dets, key=lambda d: d.confidence).label
        category = next((d.category for d in dets if d.category), None)
        # Union example items, preserving first-seen order.
        keywords: list[str] = []
        seen: set[str] = set()
        for d in dets:
            for kw in d.keywords:
                k = _norm(kw)
                if k and k not in seen:
                    seen.add(k)
                    keywords.append(kw)
        entries.append(
            MapEntry(
                label=label,
                category=category,
                keywords=keywords,
                position=Point(x=cx, y=cy),
                path_distance_m=cdist,
                observation_count=len(dets),
            )
        )
    entries.sort(key=lambda e: e.path_distance_m)
    return StoreMap(store_id=store_id, entries=entries)
