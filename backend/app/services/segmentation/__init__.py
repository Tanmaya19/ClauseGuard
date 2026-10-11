"""Clause segmentation (REQ-2.1 to REQ-2.4)."""

from app.services.segmentation.segmenter import (
    MAX_CLAUSE_CHARS,
    MIN_CLAUSE_CHARS,
    Segment,
    segment,
)

__all__ = ["MAX_CLAUSE_CHARS", "MIN_CLAUSE_CHARS", "Segment", "segment"]
