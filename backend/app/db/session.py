"""Engine and session management.

Synchronous SQLAlchemy is used deliberately — see
docs/ADRs/0001-sync-sqlalchemy-and-uuid-keys.md. In short: the heaviest work
in this system is CPU-bound transformer inference, which blocks an event loop
regardless of how the database is accessed, so async drivers would add
complexity without buying throughput.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.sqlalchemy_url,
    pool_pre_ping=True,  # survives the database restarting under a dev container
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a session that is always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
