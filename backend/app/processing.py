"""Session processing: run vision, locate detections, mark the session mapped.

Kept separate from the HTTP layer so it can run inline (tests) or in a
background task (the API), and so a real job queue can call it later.
"""
from __future__ import annotations

from .mapping import locate_detections
from .models import Session
from .repository import Repository
from .vision import VisionDetector


def process_session(
    repo: Repository,
    detector: VisionDetector,
    session: Session,
    video: bytes | None,
) -> Session:
    session.status = "processing"
    repo.update_session(session)
    try:
        raw = detector.detect(
            session_id=session.id, duration_ms=session.duration_ms, video=video
        )
        located = locate_detections(session.id, raw, session.path)
        repo.set_detections(session.id, located)
        session.detection_count = len(located)
        session.status = "mapped"
    except Exception:  # noqa: BLE001 - mark failed, surface via status
        session.status = "failed"
    repo.update_session(session)
    return session
