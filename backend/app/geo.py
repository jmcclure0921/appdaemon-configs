"""Geometry: project GPS to a local meters frame and resolve path positions.

The store is mapped in a local planar frame in meters with the entrance (the
first usable path sample) at the origin. We use an equirectangular projection,
which is accurate to well under a meter across the footprint of a single store.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .models import PathPoint, Point

# Mean Earth radius (meters).
_EARTH_R = 6_371_000.0

# Average human stride length (meters), used only when GPS is unavailable and we
# fall back to step-count-driven dead reckoning.
_STRIDE_M = 0.72


def project(lat: float, lon: float, lat0: float, lon0: float) -> Point:
    """Equirectangular projection of (lat, lon) relative to origin (lat0, lon0)."""
    lat_r = math.radians(lat)
    lat0_r = math.radians(lat0)
    x = math.radians(lon - lon0) * math.cos((lat_r + lat0_r) / 2.0) * _EARTH_R
    y = math.radians(lat - lat0) * _EARTH_R
    return Point(x=x, y=y)


def distance(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


@dataclass
class ResolvedPath:
    """A walking path resolved to local-frame positions with cumulative distance.

    `points[i]` is at time `times_ms[i]`, local position `positions[i]`, and
    cumulative walking distance `cum_dist_m[i]` from the start.
    """

    times_ms: list[int]
    positions: list[Point]
    cum_dist_m: list[float]

    @property
    def total_distance_m(self) -> float:
        return self.cum_dist_m[-1] if self.cum_dist_m else 0.0

    def at(self, t_ms: int) -> tuple[Point, float]:
        """Linearly interpolate (position, cumulative distance) at time `t_ms`."""
        if not self.times_ms:
            return Point(x=0.0, y=0.0), 0.0
        if t_ms <= self.times_ms[0]:
            return self.positions[0], self.cum_dist_m[0]
        if t_ms >= self.times_ms[-1]:
            return self.positions[-1], self.cum_dist_m[-1]
        # Find the segment [i, i+1] containing t_ms.
        lo, hi = 0, len(self.times_ms) - 1
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if self.times_ms[mid] <= t_ms:
                lo = mid
            else:
                hi = mid
        t0, t1 = self.times_ms[lo], self.times_ms[hi]
        frac = 0.0 if t1 == t0 else (t_ms - t0) / (t1 - t0)
        p0, p1 = self.positions[lo], self.positions[hi]
        pos = Point(x=p0.x + (p1.x - p0.x) * frac, y=p0.y + (p1.y - p0.y) * frac)
        dist = self.cum_dist_m[lo] + (self.cum_dist_m[hi] - self.cum_dist_m[lo]) * frac
        return pos, dist


def resolve_path(path: list[PathPoint]) -> ResolvedPath:
    """Turn raw captured path points into a `ResolvedPath`.

    Preference order per point: GPS (projected) → step-count dead reckoning →
    hold previous position. Points are de-duplicated by time so interpolation is
    strictly increasing in `t_ms`.
    """
    times: list[int] = []
    positions: list[Point] = []

    # Establish the GPS origin from the first point that has a fix.
    lat0 = lon0 = None
    for p in path:
        if p.lat is not None and p.lon is not None:
            lat0, lon0 = p.lat, p.lon
            break

    last_pos = Point(x=0.0, y=0.0)
    last_step: int | None = None
    last_heading = 0.0
    for p in path:
        if times and p.t_ms <= times[-1]:
            # Ignore out-of-order / duplicate timestamps.
            continue
        if p.lat is not None and p.lon is not None and lat0 is not None:
            pos = project(p.lat, p.lon, lat0, lon0)  # type: ignore[arg-type]
        elif p.step is not None and last_step is not None:
            # Dead reckoning: advance by stride * delta-steps along heading.
            d = (p.step - last_step) * _STRIDE_M
            h = math.radians(p.heading_deg if p.heading_deg is not None else last_heading)
            pos = Point(x=last_pos.x + d * math.sin(h), y=last_pos.y + d * math.cos(h))
        else:
            pos = last_pos
        if p.step is not None:
            last_step = p.step
        if p.heading_deg is not None:
            last_heading = p.heading_deg
        last_pos = pos
        times.append(p.t_ms)
        positions.append(pos)

    if not times:
        return ResolvedPath(times_ms=[], positions=[], cum_dist_m=[])

    cum = [0.0]
    for i in range(1, len(positions)):
        cum.append(cum[-1] + distance(positions[i - 1], positions[i]))
    return ResolvedPath(times_ms=times, positions=positions, cum_dist_m=cum)
