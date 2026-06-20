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
| `app/vision/`        | Pluggable vision: interface, stub, Claude detector, frames. |

## Vision: stub and the real Claude detector

`app/vision/base.py` defines `VisionDetector.detect(...) -> list[RawDetection]`.
Select the backend with `SHELFMAPPER_VISION`:

| Value            | Detector                                                         |
| ---------------- | --------------------------------------------------------------- |
| `stub` (default) | Deterministic fake product walk. No model, ffmpeg, or key.      |
| `claude`         | Samples frames and runs a Claude multimodal model on each.      |

### Real detector (`SHELFMAPPER_VISION=claude`)

`app/vision/claude_vision.py` samples JPEG frames from the uploaded video
(`app/vision/frames.py`, via `ffmpeg`) and sends each to a Claude model, which
reads the shelf price tags and returns a structured list of products
(name, category, price, confidence) using the Messages API's structured-output
support — OCR and product identification in one call. Products seen across
consecutive frames are de-duplicated.

```bash
pip install -r requirements-vision.txt   # adds the anthropic SDK
# plus: ffmpeg on PATH, and ANTHROPIC_API_KEY in the environment
export SHELFMAPPER_VISION=claude
export ANTHROPIC_API_KEY=sk-ant-...
export SHELFMAPPER_VISION_MODEL=claude-opus-4-8   # optional; see cost note
uvicorn app.main:app --reload
```

**Cost.** A session is many frames, so this is a high-volume image-extraction
workload. The model is configurable via `SHELFMAPPER_VISION_MODEL` — point it at
`claude-haiku-4-5` or `claude-sonnet-4-6` to cut per-frame cost. The system
prompt is prompt-cached across a session's frames, and moving frame processing
to the Batch API would halve cost again for offline runs.

Locating detections in the store is **not** the detector's concern — `mapping.py`
does that from the recorded path, so any detector slots in unchanged. To add a
different provider, implement a class satisfying `VisionDetector` and register it
in `app/vision/__init__.py:get_detector()`.

## Notes / next steps

- Storage is in-memory and per-process — restarting clears data. The
  `Repository` surface is intentionally DB-shaped for a later swap.
- Processing runs in a FastAPI `BackgroundTask`. For real video this should move
  to a job queue (RQ/Celery/Cloud Tasks) with object storage for the uploads.
- The local frame fuses GPS today; `geo.py` already has a dead-reckoning path
  for indoor stretches without a fix, ready to fuse with IMU/heading.
