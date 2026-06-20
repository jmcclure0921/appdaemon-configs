# ShelfMapper

Map grocery stores by walking them, then optimize your shopping list for the
shortest walking path.

You walk a store once with the app, recording the shelves as video while the
phone captures your walking path (GPS + motion sensors). A cloud vision backend
turns the video into a map of *what product is where*. Later, you paste in a
shopping list and the app gives you an ordered route that minimizes how far you
walk.

```
┌──────────────┐        video + path         ┌──────────────────┐
│  Android app │ ─────────────────────────▶  │  FastAPI backend │
│  (Kotlin)    │                             │                  │
│              │   product → location map    │  vision module   │
│  record /    │ ◀─────────────────────────  │  store map       │
│  shop / route│                             │  route optimizer │
└──────────────┘   optimized route           └──────────────────┘
```

## Repository layout

| Path        | What it is                                                       |
| ----------- | ---------------------------------------------------------------- |
| `android/`  | Native Kotlin app (Jetpack Compose, CameraX, fused location).    |
| `backend/`  | Python FastAPI service: ingest, vision, store map, optimizer.    |
| `docs/`     | Architecture notes and the shared HTTP API contract.             |

Start with [`docs/api-contract.md`](docs/api-contract.md) — it is the source of
truth that both the app and the backend implement.

## The core loop

1. **Record** — Walk the store. The app records shelf video and timestamps your
   path (latitude/longitude + step/heading from device motion).
2. **Map** — The app uploads the session. The backend samples frames, runs
   vision to detect products + read labels/prices, and pins each detection to a
   position along your recorded path. Detections aggregate into a per-store map.
3. **Optimize** — Give the app a shopping list. The backend matches each item to
   a location in the store map and returns a route (an ordered list of stops)
   that minimizes total walking distance from the entrance.

## Status

This is an early foundation, not a finished product. What works today:

- **Backend**: end-to-end ingest → vision (pluggable, with a working stub) →
  store-map build → route optimization, with tests. Run it locally with
  `uvicorn`.
- **Android**: a complete project scaffold implementing the record / shop /
  route screens against the API contract. Needs the Android SDK to build.

The vision step is behind an interface (`backend/app/vision/base.py`) with two
implementations: a deterministic **stub** (so the whole loop runs with no GPU,
API key, or ffmpeg) and a real **Claude** detector that samples video frames and
extracts products + prices from the shelf tags via a multimodal model. Select
with `SHELFMAPPER_VISION=stub|claude`; see `backend/README.md`.

## Quick start (backend)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# docs at http://localhost:8000/docs
pytest            # run the test suite
```

See [`backend/README.md`](backend/README.md) and
[`android/README.md`](android/README.md) for details.
