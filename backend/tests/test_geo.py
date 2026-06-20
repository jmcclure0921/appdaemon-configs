import math

from app.geo import distance, project, resolve_path
from app.models import PathPoint, Point


def test_project_origin_is_zero():
    p = project(40.0, -75.0, 40.0, -75.0)
    assert abs(p.x) < 1e-6 and abs(p.y) < 1e-6


def test_project_known_offset_north():
    # ~0.001 deg latitude north ≈ 111 m.
    p = project(40.001, -75.0, 40.0, -75.0)
    assert abs(p.x) < 0.5
    assert 110 < p.y < 112


def test_resolve_path_cumulative_distance_gps():
    # A straight 3-point northward walk.
    path = [
        PathPoint(t_ms=0, lat=40.0, lon=-75.0),
        PathPoint(t_ms=1000, lat=40.0005, lon=-75.0),
        PathPoint(t_ms=2000, lat=40.001, lon=-75.0),
    ]
    rp = resolve_path(path)
    assert math.isclose(rp.cum_dist_m[0], 0.0, abs_tol=1e-6)
    assert 110 < rp.total_distance_m < 112


def test_resolve_path_interpolates_midpoint():
    path = [
        PathPoint(t_ms=0, lat=40.0, lon=-75.0),
        PathPoint(t_ms=2000, lat=40.001, lon=-75.0),
    ]
    rp = resolve_path(path)
    pos, dist = rp.at(1000)
    assert 55 < pos.y < 56  # halfway up ~111 m
    assert 55 < dist < 56


def test_resolve_path_dead_reckoning_without_gps():
    # No GPS; walk straight north (heading 0) accumulating steps.
    path = [
        PathPoint(t_ms=0, step=0, heading_deg=0.0),
        PathPoint(t_ms=1000, step=10, heading_deg=0.0),
    ]
    rp = resolve_path(path)
    assert rp.total_distance_m > 0
    assert distance(Point(x=0, y=0), rp.positions[-1]) > 5
