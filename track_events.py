"""
track_events.py

Tiny helper to log user events for АГСК-3 analytics (FastAPI + Supabase).
Fire-and-forget — never blocks or breaks the main request flow.

Author: Kairat Baikulov | 2026-04-07

Usage:
    from track_events import track_event, EVENT_TYPES

    @app.post("/api/export/gost")
    def export(user: dict = Depends(require_user)):
        # ... do export ...
        track_event(user["id"], EVENT_TYPES["SPEC_EXPORTED"], {"items": 42})
        return StreamingResponse(...)
"""

from __future__ import annotations

from typing import Optional, Any

from auth_middleware import _http


# ─────────────────────────────────────────────────────────────
# Known event types — use these for consistency
# ─────────────────────────────────────────────────────────────
EVENT_TYPES = {
    "SEARCH":         "search",
    "SPEC_GENERATED": "spec_generated",
    "SPEC_EXPORTED":  "spec_exported",
    "SPEC_SAVED":     "spec_saved",
    "ITEM_ADDED":     "item_added",
    "SESSION_START":  "session_start",
}


def track_event(
    user_id: Optional[int],
    event_type: str,
    metadata: Optional[dict] = None,
) -> None:
    """
    Log an event for the given user.
    Silently no-ops if user_id is None (unregistered session).
    Never raises — tracking must not break the main flow.

    Args:
        user_id: from req.user or None
        event_type: event name (use EVENT_TYPES constants)
        metadata: optional JSONB payload
    """
    if not user_id or not event_type:
        return
    try:
        _http.post(
            "/events",
            json={
                "user_id": int(user_id),
                "event_type": str(event_type),
                "metadata": metadata or {},
            },
            headers={"Prefer": "return=minimal"},
        )
    except Exception as e:
        print(f"[track-events] failed: {e}")
