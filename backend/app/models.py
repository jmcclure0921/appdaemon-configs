"""Pydantic models — the wire shapes from docs/api-contract.md."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

SessionStatus = Literal["uploaded", "processing", "mapped", "failed"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Point(BaseModel):
    """A location in the store's local planar frame, meters, entrance at (0,0)."""

    x: float
    y: float


class PathPoint(BaseModel):
    """One sample of the walking path, captured by the app while recording."""

    t_ms: int = Field(ge=0)
    lat: Optional[float] = None
    lon: Optional[float] = None
    heading_deg: Optional[float] = None
    step: Optional[int] = None


# ---- Stores ---------------------------------------------------------------


class StoreCreate(BaseModel):
    name: str = Field(min_length=1)
    address: Optional[str] = None


class Store(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


# ---- Sessions -------------------------------------------------------------


class SessionMeta(BaseModel):
    """The `meta` JSON part of a session upload."""

    recorded_at: datetime = Field(default_factory=_now)
    duration_ms: int = Field(ge=0)
    path: list[PathPoint] = Field(default_factory=list)


class Detection(BaseModel):
    id: str
    session_id: str
    t_ms: int
    label: str
    raw_text: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    confidence: float = 0.0
    position: Point
    path_distance_m: float = 0.0


class Session(BaseModel):
    id: str
    store_id: str
    status: SessionStatus = "uploaded"
    recorded_at: datetime = Field(default_factory=_now)
    duration_ms: int = 0
    path: list[PathPoint] = Field(default_factory=list)
    detection_count: int = 0


# ---- Store map ------------------------------------------------------------


class MapEntry(BaseModel):
    label: str
    category: Optional[str] = None
    position: Point
    path_distance_m: float = 0.0
    observation_count: int = 0
    avg_price: Optional[float] = None


class StoreMap(BaseModel):
    store_id: str
    entries: list[MapEntry] = Field(default_factory=list)


# ---- Optimization ---------------------------------------------------------


class OptimizeRequest(BaseModel):
    items: list[str] = Field(min_length=1)
    start: Optional[Point] = None
    round_trip: bool = False


class RouteStop(BaseModel):
    order: int
    query: str
    label: str
    position: Point
    path_distance_m: float
    matched: bool = True


class OptimizedRoute(BaseModel):
    stops: list[RouteStop] = Field(default_factory=list)
    unmatched: list[str] = Field(default_factory=list)
    total_distance_m: float = 0.0
    ordered_query_list: list[str] = Field(default_factory=list)
