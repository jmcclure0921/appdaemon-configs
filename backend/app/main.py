"""FastAPI application wiring the ShelfMapper endpoints (see docs/api-contract.md)."""
from __future__ import annotations

import uuid

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile

from . import __version__
from .matching import match_item  # noqa: F401  (re-exported for callers/tests)
from .mapping import build_map
from .models import (
    OptimizedRoute,
    OptimizeRequest,
    Session,
    SessionMeta,
    Store,
    StoreCreate,
    StoreMap,
)
from .optimizer import optimize_route
from .processing import process_session
from .repository import Repository
from .vision import get_detector

app = FastAPI(title="ShelfMapper", version=__version__)

# Single-process singletons. Swap via dependency_overrides in tests.
_repo = Repository()
_detector = get_detector()


def get_repo() -> Repository:
    return _repo


def get_vision():
    return _detector


@app.get("/v1/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


# ---- stores --------------------------------------------------------------


@app.post("/v1/stores", response_model=Store, status_code=201)
def create_store(body: StoreCreate, repo: Repository = Depends(get_repo)) -> Store:
    return repo.create_store(body.name, body.address)


@app.get("/v1/stores", response_model=list[Store])
def list_stores(repo: Repository = Depends(get_repo)) -> list[Store]:
    return repo.list_stores()


@app.get("/v1/stores/{store_id}", response_model=Store)
def get_store(store_id: str, repo: Repository = Depends(get_repo)) -> Store:
    store = repo.get_store(store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="store not found")
    return store


# ---- sessions ------------------------------------------------------------


@app.post("/v1/stores/{store_id}/sessions", response_model=Session, status_code=202)
async def upload_session(
    store_id: str,
    background: BackgroundTasks,
    meta: str = Form(..., description="JSON SessionMeta"),
    video: UploadFile | None = File(default=None),
    repo: Repository = Depends(get_repo),
    detector=Depends(get_vision),
) -> Session:
    if repo.get_store(store_id) is None:
        raise HTTPException(status_code=404, detail="store not found")
    parsed = SessionMeta.model_validate_json(meta)
    video_bytes = await video.read() if video is not None else None

    session = Session(
        id=str(uuid.uuid4()),
        store_id=store_id,
        status="uploaded",
        recorded_at=parsed.recorded_at,
        duration_ms=parsed.duration_ms,
        path=parsed.path,
        detection_count=0,
    )
    repo.add_session(session)
    # Process out-of-band so the upload returns immediately; client polls status.
    session.status = "processing"
    repo.update_session(session)
    background.add_task(process_session, repo, detector, session, video_bytes)
    return session


@app.get("/v1/sessions/{session_id}", response_model=Session)
def get_session(session_id: str, repo: Repository = Depends(get_repo)) -> Session:
    session = repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


# ---- map & optimize ------------------------------------------------------


@app.get("/v1/stores/{store_id}/map", response_model=StoreMap)
def get_store_map(store_id: str, repo: Repository = Depends(get_repo)) -> StoreMap:
    if repo.get_store(store_id) is None:
        raise HTTPException(status_code=404, detail="store not found")
    return build_map(store_id, repo.detections_for_store(store_id))


@app.post("/v1/stores/{store_id}/optimize", response_model=OptimizedRoute)
def optimize(
    store_id: str, body: OptimizeRequest, repo: Repository = Depends(get_repo)
) -> OptimizedRoute:
    if repo.get_store(store_id) is None:
        raise HTTPException(status_code=404, detail="store not found")
    store_map = build_map(store_id, repo.detections_for_store(store_id))
    return optimize_route(store_map, body)
