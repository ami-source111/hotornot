"""Session-based authentication for the web moderation panel."""
from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from src.core.config import settings

_serializer = URLSafeTimedSerializer(settings.secret_key)
SESSION_COOKIE = "mod_session"
SESSION_MAX_AGE = 60 * 60 * 8  # 8 hours


def create_session_token(username: str) -> str:
    return _serializer.dumps({"u": username})


def decode_session_token(token: str) -> str | None:
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("u")
    except (BadSignature, SignatureExpired):
        return None


def get_current_moderator(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return decode_session_token(token)


def require_moderator(request: Request) -> str:
    user = get_current_moderator(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"},
        )
    return user


def verify_credentials(username: str, password: str) -> bool:
    return (
        username == settings.web_admin_user
        and password == settings.web_admin_password
    )
