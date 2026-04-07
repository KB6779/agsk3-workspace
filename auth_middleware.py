"""
auth_middleware.py

Lightweight registration auth for АГСК-3 (FastAPI + Supabase).
Signed cookie based, zero new dependencies (uses stdlib hmac + hashlib).

Author: Kairat Baikulov | 2026-04-07

Env vars required:
    SUPABASE_URL   — already set for app.py
    SUPABASE_KEY   — already set for app.py
    AUTH_SECRET    — NEW: random 32+ char string
                     Generate: python -c "import secrets; print(secrets.token_hex(32))"
"""

from __future__ import annotations

import os
import time
import json
import hmac
import hashlib
import base64
from typing import Optional

import httpx
from fastapi import Request, HTTPException, status

# ─────────────────────────────────────────────────────────────
# Config (matches app.py pattern)
# ─────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-only-change-me-in-production")

COOKIE_NAME = "agsk3_uid"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year (in seconds)
TOKEN_MAX_AGE = 365 * 24 * 60 * 60   # token valid for 1 year

if AUTH_SECRET == "dev-only-change-me-in-production":
    print("[auth] WARNING: AUTH_SECRET not set — using insecure default!")

# Reusable Supabase client (same pattern as app.py)
_http = httpx.Client(
    base_url=f"{SUPABASE_URL}/rest/v1",
    headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    },
    timeout=15.0,
)


# ─────────────────────────────────────────────────────────────
# Token sign/verify (HMAC-SHA256, base64-encoded payload + sig)
# ─────────────────────────────────────────────────────────────
def _b64url(data: bytes) -> str:
    """URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """URL-safe base64 decode (handles missing padding)."""
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("ascii"))


def sign_token(user_id: int) -> str:
    """Create signed token {payload_b64}.{sig_b64}."""
    payload = {"uid": int(user_id), "iat": int(time.time())}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64url(payload_bytes)
    sig = hmac.new(AUTH_SECRET.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = _b64url(sig)
    return f"{payload_b64}.{sig_b64}"


def verify_token(token: str) -> Optional[int]:
    """Verify signature + expiry. Returns user_id or None."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        expected_sig = hmac.new(
            AUTH_SECRET.encode("utf-8"),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(_b64url_decode(payload_b64))
        if int(time.time()) - int(payload["iat"]) > TOKEN_MAX_AGE:
            return None
        return int(payload["uid"])
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# FastAPI dependencies
# ─────────────────────────────────────────────────────────────
def get_current_user(request: Request) -> Optional[dict]:
    """
    FastAPI dependency — returns user dict or None (non-blocking).
    Usage:
        @app.get("/profile")
        def profile(user = Depends(get_current_user)):
            if not user: return {"error": "not registered"}
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    user_id = verify_token(token)
    if not user_id:
        return None
    try:
        resp = _http.get("/users", params={"id": f"eq.{user_id}", "select": "id,email,name"})
        if resp.status_code == 200 and resp.json():
            user = resp.json()[0]
            # Async-ish last_seen bump (fire-and-forget, ignore errors)
            try:
                _http.patch(
                    "/users",
                    params={"id": f"eq.{user_id}"},
                    json={"last_seen_at": "now()", "visit_count": user.get("visit_count", 0) + 1},
                    headers={"Prefer": "return=minimal"},
                )
            except Exception:
                pass
            return user
    except Exception as e:
        print(f"[auth] DB lookup failed: {e}")
    return None


def require_user(request: Request) -> dict:
    """
    FastAPI dependency — raises 401 if not registered.
    Usage:
        @app.post("/api/export/gost")
        def export(user: dict = Depends(require_user)):
            ...
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Registration required", "action": "show_register_modal"},
        )
    return user
