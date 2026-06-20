# ShelfMapper backend

FastAPI service that ingests grocery-walk sessions, maps products to locations,
and optimizes shopping lists into short walking routes. Implements
[`../docs/api-contract.md`](../docs/api-contract.md).

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000
# interactive API docs: http://localhost:8000/docs
pytest                                  # 18 tests
```

## Module map

| Module               | Responsibility                                             |
| -------------------- | ---------------------------------------------------------- |
| `app/main.py`        | FastAPI routes / wiring.                                    |
| `app/models.py`      | Pydantic wire shapes (match the API contract).             |
| `app/geo.py`         | GPS → local-meters projection; path resolution & interp.   |
| `app/mapping.py`     | Pin detections to path positions; aggregate the store map. |
| `app/matching.py`    | Fuzzy match shopping-list items → map entries.             |
| `app/optimizer.py`   | TSP route optimization (nearest-neighbour + 2-opt/Or-opt). |
| `app/processing.py`  | Per-session pipeline: vision → locate → mark mapped.       |
| `app/repository.py`  | In-memory data store (swap for a DB later).                |
| `app/vision/`        | The pluggable vision boundary + a deterministic stub.      |

## Plugging in real vision

`app/vision/base.py` defines `VisionDetector.detect(...) -> list[RawDetection]`.
The stub (`app/vision/stub.py`) fabricates a reproducible product walk so the
loop runs with no model. To use a real detector:

1. Implement a class satisfying `VisionDetector` (sample frames from the video,
   run detection/OCR, emit `RawDetection(t_ms=..., label=..., ...)`).
2. Register it in `app/vision/__init__.py:get_detector()` behind a new value of
   the `SHELFMAPPER_VISION` env var.

Locating detections in the store is **not** the detector's concern — `mapping.py`
does that from the recorded path, so any detector slots in unchanged.

## Notes / next steps

- Storage is in-memory and per-process — restarting clears data. The
  `Repository` surface is intentionally DB-shaped for a later swap.
- Processing runs in a FastAPI `BackgroundTask`. For real video this should move
  to a job queue (RQ/Celery/Cloud Tasks) with object storage for the uploads.
- The local frame fuses GPS today; `geo.py` already has a dead-reckoning path
  for indoor stretches without a fix, ready to fuse with IMU/heading.
