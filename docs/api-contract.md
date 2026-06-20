# ShelfMapper API contract

Version: `v1`. Base path: `/v1`. All bodies are JSON unless noted. Times are
ISO-8601 UTC. IDs are server-generated strings (UUIDs).

This document is the source of truth shared by `android/` and `backend/`. If you
change a shape here, change both sides.

## Coordinate model

A store is mapped in a **local planar frame** measured in **meters**, with the
store entrance at the origin `(0, 0)`. The app captures a raw path; the backend
projects GPS to this local frame (and can later fuse motion/IMU). Every product
location and route stop is expressed as `{ "x": <m>, "y": <m> }`.

The walking path is also stored as cumulative **path distance** in meters, so
products can be ordered "as you walk" even before a full 2-D layout is trusted.

## Resources

### Store

```json
{
  "id": "str",
  "name": "str",
  "address": "str|null",
  "created_at": "iso-8601"
}
```

### PathPoint (captured by the app during recording)

```json
{
  "t_ms": 0,                 // milliseconds since recording start
  "lat": 0.0, "lon": 0.0,    // GPS, nullable when indoors
  "heading_deg": 0.0,        // device heading, nullable
  "step": 0                  // cumulative step count from motion sensor, nullable
}
```

### Session (one recorded walk)

```json
{
  "id": "str",
  "store_id": "str",
  "status": "uploaded|processing|mapped|failed",
  "recorded_at": "iso-8601",
  "duration_ms": 0,
  "path": [ /* PathPoint */ ],
  "detection_count": 0
}
```

### Detection (a store section seen in the video, pinned to the path)

The goal is route optimization, so detections are **store sections** (dairy,
produce, frozen, …), not individual products or prices. `keywords` holds example
items seen in the section so a shopping-list entry can be matched to it.

```json
{
  "id": "str",
  "session_id": "str",
  "t_ms": 0,                       // frame time, used to look up path position
  "label": "str",                  // section name, e.g. "Dairy & Eggs"
  "category": "str|null",          // normalized aisle category
  "keywords": ["milk", "eggs"],    // example items in the section
  "confidence": 0.0,
  "position": { "x": 0.0, "y": 0.0 },
  "path_distance_m": 0.0
}
```

### MapEntry (aggregated section location for a store)

```json
{
  "label": "str",                  // section name, e.g. "Dairy & Eggs"
  "category": "str|null",
  "keywords": ["milk", "eggs"],    // unioned example items, used for matching
  "position": { "x": 0.0, "y": 0.0 },
  "path_distance_m": 0.0,
  "observation_count": 0
}
```

### RouteStop / OptimizedRoute

Items in the same section are grouped into one stop, so you visit each section
once.

```json
{
  "stops": [
    {
      "order": 0,
      "section": "Dairy & Eggs",       // the section to walk to
      "items": ["milk", "eggs"],       // shopping-list items found here
      "position": { "x": 0.0, "y": 0.0 },
      "path_distance_m": 0.0
    }
  ],
  "unmatched": ["saffron"],            // items with no section in the map
  "total_distance_m": 0.0,
  "ordered_query_list": ["milk", "eggs", "..."]  // all items, in stop order
}
```

## Endpoints

| Method | Path                              | Purpose                                  |
| ------ | --------------------------------- | ---------------------------------------- |
| GET    | `/v1/health`                      | Liveness.                                |
| POST   | `/v1/stores`                      | Create a store. Body: `{name, address?}` |
| GET    | `/v1/stores`                      | List stores.                             |
| GET    | `/v1/stores/{store_id}`           | Get one store.                           |
| POST   | `/v1/stores/{store_id}/sessions`  | Upload a session (multipart, see below). |
| GET    | `/v1/sessions/{session_id}`       | Session status + detections summary.     |
| GET    | `/v1/stores/{store_id}/map`       | Aggregated product→location map.         |
| POST   | `/v1/stores/{store_id}/optimize`  | Optimize a shopping list into a route.   |

### Upload a session

`POST /v1/stores/{store_id}/sessions` — `multipart/form-data`:

- `video`: the recorded file (e.g. `video/mp4`). Optional in tests.
- `meta`: a JSON part:

```json
{
  "recorded_at": "iso-8601",
  "duration_ms": 0,
  "path": [ /* PathPoint */ ]
}
```

Returns the `Session` with `status: "processing"`. The backend processes the
video asynchronously; poll `GET /v1/sessions/{id}` until `status` is `mapped`.

### Optimize a shopping list

`POST /v1/stores/{store_id}/optimize`:

```json
{
  "items": ["milk", "eggs", "bananas", "cheddar"],
  "start": { "x": 0.0, "y": 0.0 },     // optional, defaults to entrance (0,0)
  "round_trip": false                   // return to start at the end?
}
```

Returns an `OptimizedRoute`. Items are fuzzy-matched against the store map;
unmatched items are listed separately so the app can still show them.

## Errors

Standard HTTP codes. Body: `{ "detail": "message" }`. `404` for unknown
store/session, `422` for malformed bodies (FastAPI validation).
