"""In-memory data store.

Deliberately simple so the loop runs with zero infrastructure. The method
surface is intentionally repository-shaped, so swapping in Postgres/SQLite later
is a contained change.
"""
from __future__ import annotations

import threading
import uuid

from .models import Detection, Session, Store


class Repository:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stores: dict[str, Store] = {}
        self._sessions: dict[str, Session] = {}
        # session_id -> detections
        self._detections: dict[str, list[Detection]] = {}

    # ---- stores ----------------------------------------------------------
    def create_store(self, name: str, address: str | None) -> Store:
        with self._lock:
            store = Store(id=str(uuid.uuid4()), name=name, address=address)
            self._stores[store.id] = store
            return store

    def get_store(self, store_id: str) -> Store | None:
        return self._stores.get(store_id)

    def list_stores(self) -> list[Store]:
        return list(self._stores.values())

    # ---- sessions --------------------------------------------------------
    def add_session(self, session: Session) -> None:
        with self._lock:
            self._sessions[session.id] = session

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def update_session(self, session: Session) -> None:
        with self._lock:
            self._sessions[session.id] = session

    # ---- detections ------------------------------------------------------
    def set_detections(self, session_id: str, detections: list[Detection]) -> None:
        with self._lock:
            self._detections[session_id] = detections

    def detections_for_session(self, session_id: str) -> list[Detection]:
        return list(self._detections.get(session_id, []))

    def detections_for_store(self, store_id: str) -> list[Detection]:
        with self._lock:
            store_session_ids = {
                s.id for s in self._sessions.values() if s.store_id == store_id
            }
            out: list[Detection] = []
            for sid in store_session_ids:
                out.extend(self._detections.get(sid, []))
            return out
