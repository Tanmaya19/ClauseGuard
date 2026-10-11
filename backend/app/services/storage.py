"""Uploaded-file storage.

Files are written under ``<storage_dir>/<user_id>/<contract_id><ext>``. The
path is derived entirely from UUIDs we generated, never from the user-supplied
filename — a filename like ``../../etc/passwd`` or a Windows reserved name
would otherwise decide where bytes land. The original name is kept in the
database for display only.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

EXTENSIONS = {"pdf": ".pdf", "docx": ".docx"}


def _root() -> Path:
    return Path(get_settings().storage_dir)


def save(user_id: uuid.UUID, contract_id: uuid.UUID, fmt: str, data: bytes) -> str:
    directory = _root() / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / f"{contract_id}{EXTENSIONS.get(fmt, '.bin')}"
    path.write_bytes(data)

    # Stored relative so the database stays portable across deployments with
    # different mount points.
    return str(path.relative_to(_root()).as_posix())


def read(storage_path: str) -> bytes:
    return (_root() / storage_path).read_bytes()


def delete(storage_path: str) -> None:
    try:
        (_root() / storage_path).unlink(missing_ok=True)
    except OSError:
        # The database row is the source of truth; a stranded file is a
        # housekeeping problem, not a failed deletion from the user's view.
        logger.warning("Could not delete %s", storage_path, exc_info=True)


def delete_user_tree(user_id: uuid.UUID) -> None:
    """Remove every stored file for an account (SRS 5.3, data deletion)."""
    shutil.rmtree(_root() / str(user_id), ignore_errors=True)
