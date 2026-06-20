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
                raw_text=r.raw_text,
                category=r.category,
                price=r.price,
                confidence=r.confidence,
                position=pos,
                path_distance_m=dist,
            )
        )
    return located


def _norm(label: str) -> str:
    return " ".join(label.lower().split())


def build_map(store_id: str, detections: list[Detection]) -> StoreMap:
    """Aggregate detections (across all of a store's sessions) into a map.

    Observations of the same product label are averaged: position is a
    confidence-weighted centroid, path distance and price are confidence-weighted
    means. This smooths out per-session GPS noise.
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
        priced = [d for d in dets if d.price is not None]
        avg_price = sum(d.price for d in priced) / len(priced) if priced else None  # type: ignore[misc]
        # Use the most frequent original label spelling for display.
        label = max(dets, key=lambda d: d.confidence).label
        category = next((d.category for d in dets if d.category), None)
        entries.append(
            MapEntry(
                label=label,
                category=category,
                position=Point(x=cx, y=cy),
                path_distance_m=cdist,
                observation_count=len(dets),
                avg_price=round(avg_price, 2) if avg_price is not None else None,
            )
        )
    entries.sort(key=lambda e: e.path_distance_m)
    return StoreMap(store_id=store_id, entries=entries)
