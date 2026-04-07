"""
auth_routes.py

FastAPI router for АГСК-3 lightweight registration.
    POST /api/auth/register  { email, name } → sets cookie, returns { user }
    POST /api/auth/check                     → returns { user } or 401
    POST /api/auth/logout                    → clears cookie

Author: Kairat Baikulov | 2026-04-07

Usage in app.py:
    from auth_routes import auth_router
    app.include_router(auth_router)
"""

from __future__ import annotations

import re
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from pydantic import BaseModel, Field, field_validator

from auth_middleware import (
    _http,
    sign_token,
    get_current_user,
    COOKIE_NAME,
    COOKIE_MAX_AGE,
)

# ─────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class RegisterPayload(BaseModel):
    email: str = Field(..., max_length=320)
    name: str = Field(..., min_length=2, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Некорректный email")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Имя слишком короткое")
        return v


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _get_client_ip(request: Request) -> Optional[str]:
    """Extract real client IP from proxy headers."""
    headers = request.headers
    return (
        headers.get("cf-connecting-ip")
        or headers.get("x-real-ip")
        or (headers.get("x-forwarded-for") or "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )


def _upsert_user(email: str, name: str, ip: Optional[str], ua: str) -> dict:
    """
    Upsert user via Supabase REST. Uses ON CONFLICT behavior via Prefer header.
    Returns user dict {id, email, name}.
    """
    # Supabase upsert: POST /users with Prefer: resolution=merge-duplicates
    # Requires a unique constraint on email (already in schema_supabase.sql)
    payload = {
        "email": email,
        "name": name,
        "first_ip": ip,
        "first_ua": ua[:500] if ua else None,
    }
    resp = _http.post(
        "/users",
        json=payload,
        headers={
            "Prefer": "resolution=merge-duplicates,return=representation",
        },
        params={"on_conflict": "email"},
    )
    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка регистрации: {resp.status_code} {resp.text[:200]}",
        )
    rows = resp.json()
    if not rows:
        raise HTTPException(status_code=500, detail="Ошибка регистрации: пустой ответ")

    user = rows[0]

    # Bump visit_count (separate call — upsert doesn't know old value)
    try:
        _http.patch(
            "/users",
            params={"id": f"eq.{user['id']}"},
            json={"last_seen_at": "now()"},
            headers={"Prefer": "return=minimal"},
        )
    except Exception:
        pass  # non-critical

    return {"id": user["id"], "email": user["email"], "name": user["name"]}


# ─────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/register")
def register(payload: RegisterPayload, request: Request, response: Response):
    """Register (or re-identify) user by email + name."""
    ip = _get_client_ip(request)
    ua = request.headers.get("user-agent", "")
    try:
        user = _upsert_user(payload.email, payload.name, ip, ua)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[auth/register] error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка регистрации, попробуйте позже")

    token = sign_token(user["id"])
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )
    return {"user": user}


@auth_router.post("/check")
def check(request: Request):
    """Verify current session via cookie. Returns user or 401."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail={"error": "not_registered"})
    return {"user": user}


@auth_router.post("/logout")
def logout(response: Response):
    """Clear registration cookie."""
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
