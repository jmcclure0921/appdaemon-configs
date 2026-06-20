from app.geo import distance
from app.models import MapEntry, OptimizeRequest, Point, StoreMap
from app.optimizer import _path_length, optimize_route


def _entry(label, x, y, category=None):
    return MapEntry(
        label=label,
        category=category,
        position=Point(x=x, y=y),
        path_distance_m=abs(x) + abs(y),
        observation_count=1,
    )


def _map():
    # A few products scattered so a greedy order is not the input order.
    return StoreMap(
        store_id="s",
        entries=[
            _entry("Whole Milk", 0, 10, "dairy"),
            _entry("Bananas", 0, 2, "produce"),
            _entry("Frozen Pizza", 0, 20, "frozen"),
            _entry("Bread", 0, 5, "bakery"),
        ],
    )


def test_orders_stops_along_the_walk():
    route = optimize_route(_map(), OptimizeRequest(items=["pizza", "milk", "bananas", "bread"]))
    dists = [s.path_distance_m for s in route.stops]
    assert dists == sorted(dists)  # nearest-first up a linear aisle
    assert route.ordered_query_list[0] == "bananas"
    assert route.ordered_query_list[-1] == "pizza"


def test_unmatched_items_reported():
    route = optimize_route(_map(), OptimizeRequest(items=["milk", "saffron threads"]))
    assert "saffron threads" in route.unmatched
    assert any("milk" in s.items for s in route.stops)


def test_groups_items_in_the_same_section():
    store = StoreMap(
        store_id="s",
        entries=[
            MapEntry(label="Dairy & Eggs", position=Point(x=0, y=10),
                     path_distance_m=10, keywords=["milk", "eggs", "butter"]),
            MapEntry(label="Produce", position=Point(x=0, y=2),
                     path_distance_m=2, keywords=["bananas"]),
        ],
    )
    route = optimize_route(store, OptimizeRequest(items=["milk", "bananas", "eggs"]))
    # milk + eggs collapse into one Dairy stop; bananas its own.
    assert len(route.stops) == 2
    dairy = next(s for s in route.stops if s.section == "Dairy & Eggs")
    assert dairy.items == ["milk", "eggs"]


def test_total_distance_is_consistent():
    route = optimize_route(_map(), OptimizeRequest(items=["milk", "bananas", "pizza", "bread"]))
    pts = [Point(x=0, y=0)] + [s.position for s in route.stops]
    assert abs(route.total_distance_m - _path_length(pts, False)) < 1e-6


def test_round_trip_is_longer_than_open():
    items = ["milk", "bananas", "pizza", "bread"]
    open_route = optimize_route(_map(), OptimizeRequest(items=items, round_trip=False))
    closed = optimize_route(_map(), OptimizeRequest(items=items, round_trip=True))
    assert closed.total_distance_m > open_route.total_distance_m


def test_two_opt_beats_nearest_neighbour_on_a_trap():
    # Positions where pure nearest-neighbour from origin makes a bad first hop.
    m = StoreMap(
        store_id="s",
        entries=[
            _entry("A", 1, 0),
            _entry("B", 2, 0),
            _entry("C", 3, 0),
            _entry("D", 0, 1),  # close to start but off the main line
        ],
    )
    route = optimize_route(m, OptimizeRequest(items=["A", "B", "C", "D"]))
    # Optimal open route walks D,A,B,C (or A,B,C then D) — verify it's short.
    pts = [Point(x=0, y=0)] + [s.position for s in route.stops]
    assert _path_length(pts, False) <= 4.5
