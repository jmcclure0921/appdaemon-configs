"""Route optimization: order shopping stops to minimize walking distance.

This is an open/closed travelling-salesman problem over the stop positions in
the store's local meters frame, fixed to start at the entrance (or a given
point). We seed with nearest-neighbour and refine with 2-opt, which is fast and
near-optimal for the handful of stops on a typical shopping list.
"""
from __future__ import annotations

from .geo import distance
from .matching import match_item
from .models import (
    MapEntry,
    OptimizedRoute,
    OptimizeRequest,
    Point,
    RouteStop,
    StoreMap,
)


def _path_length(pts: list[Point], round_trip: bool) -> float:
    total = sum(distance(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    if round_trip and len(pts) > 1:
        total += distance(pts[-1], pts[0])
    return total


def _nearest_neighbour(start: Point, stops: list[Point]) -> list[int]:
    remaining = list(range(len(stops)))
    order: list[int] = []
    cur = start
    while remaining:
        j = min(remaining, key=lambda i: distance(cur, stops[i]))
        order.append(j)
        cur = stops[j]
        remaining.remove(j)
    return order


def _local_search(start: Point, stops: list[Point], order: list[int], round_trip: bool) -> list[int]:
    """Improve `order` with 2-opt (segment reversal) and Or-opt (relocating a
    short run of 1-3 stops) until no move shortens the route.

    2-opt alone can't move a single stop to a better slot (e.g. pulling a
    near-start stop to the front), so we combine it with Or-opt.
    """

    def length(o: list[int]) -> float:
        return _path_length([start] + [stops[i] for i in o], round_trip)

    best = order[:]
    best_len = length(best)
    n = len(best)
    improved = True
    while improved:
        improved = False
        # 2-opt: reverse best[i..k].
        for i in range(n - 1):
            for k in range(i + 1, n):
                cand = best[:i] + best[i : k + 1][::-1] + best[k + 1 :]
                cand_len = length(cand)
                if cand_len + 1e-9 < best_len:
                    best, best_len, improved = cand, cand_len, True
        # Or-opt: lift a run of length seg and reinsert it elsewhere.
        for seg in (1, 2, 3):
            for i in range(n - seg + 1):
                run = best[i : i + seg]
                rest = best[:i] + best[i + seg :]
                for j in range(len(rest) + 1):
                    cand = rest[:j] + run + rest[j:]
                    if cand == best:
                        continue
                    cand_len = length(cand)
                    if cand_len + 1e-9 < best_len:
                        best, best_len, improved = cand, cand_len, True
    return best


def optimize_route(store_map: StoreMap, req: OptimizeRequest) -> OptimizedRoute:
    """Match items to map entries and order the matched stops into a short route."""
    start = req.start or Point(x=0.0, y=0.0)

    matched: list[tuple[str, MapEntry]] = []
    unmatched: list[str] = []
    for item in req.items:
        entry = match_item(item, store_map.entries)
        if entry is None:
            unmatched.append(item)
        else:
            matched.append((item, entry))

    if not matched:
        return OptimizedRoute(stops=[], unmatched=unmatched, total_distance_m=0.0)

    positions = [e.position for _, e in matched]
    order = _nearest_neighbour(start, positions)
    order = _local_search(start, positions, order, req.round_trip)

    stops: list[RouteStop] = []
    for rank, idx in enumerate(order):
        query, entry = matched[idx]
        stops.append(
            RouteStop(
                order=rank,
                query=query,
                label=entry.label,
                position=entry.position,
                path_distance_m=entry.path_distance_m,
                matched=True,
            )
        )

    total = _path_length([start] + [positions[i] for i in order], req.round_trip)
    return OptimizedRoute(
        stops=stops,
        unmatched=unmatched,
        total_distance_m=round(total, 2),
        ordered_query_list=[s.query for s in stops],
    )
