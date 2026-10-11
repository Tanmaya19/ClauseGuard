"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, decode_access_token
from app.db.models import User
from app.db.session import get_db

# auto_error=False so a missing header produces our own 401 with a consistent
# body shape, rather than FastAPI's 403.
_bearer = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user, or raise 401.

    Every contract route depends on this. SRS 5.3 requires that contract
    content reach only the uploading account, so route handlers additionally
    filter by ``user_id`` — authentication alone is not authorisation.
    """
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR

    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise CREDENTIALS_ERROR from exc

    user = db.get(User, user_id)
    if user is None:
        # A valid token for a deleted account.
        raise CREDENTIALS_ERROR

    return user
