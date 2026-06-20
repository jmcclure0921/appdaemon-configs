from app.matching import match_item
from app.models import MapEntry, Point


def _entry(label, category=None):
    return MapEntry(label=label, category=category, position=Point(x=0, y=0))


ENTRIES = [
    _entry("2% Milk", "dairy"),
    _entry("Whole Milk", "dairy"),
    _entry("Large Eggs", "dairy"),
    _entry("Bananas", "produce"),
    _entry("Cheddar Cheese", "dairy"),
]


def test_exact_substring_match():
    m = match_item("eggs", ENTRIES)
    assert m is not None and m.label == "Large Eggs"


def test_partial_token_match():
    m = match_item("cheddar", ENTRIES)
    assert m is not None and m.label == "Cheddar Cheese"


def test_no_match_returns_none():
    assert match_item("xyzzy quux", ENTRIES) is None


def test_case_insensitive():
    m = match_item("BANANAS", ENTRIES)
    assert m is not None and m.label == "Bananas"
