"""Password hashing and JWT issuing (REQ-6.1, SRS 5.3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# bcrypt with the library default cost. Chosen over a bare SHA family because
# SRS 5.3 requires "industry-standard practices": a fast hash is trivially
# brute-forced from a stolen table, a deliberately slow one is not.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(hours=12)

# bcrypt silently truncates input beyond 72 bytes, so a longer password would
# have its tail ignored. Rejecting is better than a false sense of strength.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 8


class InvalidTokenError(Exception):
    """The token is absent, malformed, expired, or not ours."""


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except ValueError:
        # Malformed stored hash: treat as a failed login, never as a pass.
        return False


def create_access_token(user_id: uuid.UUID, *, ttl: timedelta | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + (ttl or ACCESS_TOKEN_TTL)).timestamp()),
        "iss": "clauseguard",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            issuer="clauseguard",
            options={"require": ["exp", "sub", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("token subject is not a user id") from exc
