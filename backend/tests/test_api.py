"""End-to-end: create store → upload session → map → optimize."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _path(duration_ms=60_000, n=30):
    # A straight northward GPS walk over `duration_ms`.
    pts = []
    for i in range(n):
        frac = i / (n - 1)
        pts.append(
            {
                "t_ms": int(frac * duration_ms),
                "lat": 40.0 + 0.001 * frac,
                "lon": -75.0,
            }
        )
    return pts


def test_health(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_full_loop(client):
    # 1. Create a store.
    r = client.post("/v1/stores", json={"name": "Test Mart", "address": "1 Main St"})
    assert r.status_code == 201
    store_id = r.json()["id"]

    # 2. Upload a session (multipart: meta + a dummy video).
    meta = {"recorded_at": "2026-06-20T10:00:00Z", "duration_ms": 60_000, "path": _path()}
    r = client.post(
        f"/v1/stores/{store_id}/sessions",
        data={"meta": json.dumps(meta)},
        files={"video": ("walk.mp4", b"\x00\x01\x02fakevideo", "video/mp4")},
    )
    assert r.status_code == 202
    session = r.json()
    session_id = session["id"]

    # Background processing runs before TestClient returns; session is mapped.
    r = client.get(f"/v1/sessions/{session_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "mapped"
    assert r.json()["detection_count"] > 0

    # 3. The store map has located products in walk order.
    r = client.get(f"/v1/stores/{store_id}/map")
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert len(entries) > 0
    dists = [e["path_distance_m"] for e in entries]
    assert dists == sorted(dists)

    # 4. Optimize a shopping list.
    r = client.post(
        f"/v1/stores/{store_id}/optimize",
        json={"items": ["milk", "eggs", "bananas", "frozen pizza"]},
    )
    assert r.status_code == 200
    route = r.json()
    assert len(route["stops"]) >= 1
    stop_dists = [s["path_distance_m"] for s in route["stops"]]
    assert stop_dists == sorted(stop_dists)
    assert route["total_distance_m"] >= 0


def test_unknown_store_404(client):
    assert client.get("/v1/stores/nope").status_code == 404
    assert (
        client.post("/v1/stores/nope/optimize", json={"items": ["milk"]}).status_code
        == 404
    )


def test_metadata_only_upload_yields_no_detections(client):
    r = client.post("/v1/stores", json={"name": "Empty"})
    store_id = r.json()["id"]
    meta = {"recorded_at": "2026-06-20T10:00:00Z", "duration_ms": 60_000, "path": _path()}
    r = client.post(f"/v1/stores/{store_id}/sessions", data={"meta": json.dumps(meta)})
    assert r.status_code == 202
    session_id = r.json()["id"]
    # No video → stub returns no detections.
    assert client.get(f"/v1/sessions/{session_id}").json()["detection_count"] == 0
