"""Build an ExtractedDocument from raw text.

Exists for ``ml/scripts/prepare_cuad.py``: CUAD ships contract text as a
string, but the segmenter consumes ``ExtractedDocument`` because the PDF and
DOCX paths carry heading information that segmentation depends on. This module
produces the same structure from plain text so training data goes through the
*production* segmenter rather than a parallel implementation.

Offsets are preserved exactly against the input string, which is what lets
CUAD's character-level span annotations be mapped onto the resulting clauses.
"""

from __future__ import annotations

from app.services.extraction.base import ExtractedBlock, ExtractedDocument

MAX_HEADING_CHARS = 80


def _looks_like_heading(line: str) -> bool:
    """Heading heuristics for text that has lost its formatting.

    Without font data the only signals left are case and brevity, which is
    exactly the convention contracts use for section headings.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > MAX_HEADING_CHARS:
        return False

    letters = [c for c in stripped if c.isalpha()]
    if not letters:
        return False

    # ALL CAPS and short.
    if all(c.isupper() for c in letters):
        return True

    # Title Case with no sentence-ending punctuation, e.g. "Limitation of
    # Liability" standing on its own line.
    words = stripped.split()
    if 1 <= len(words) <= 8 and not stripped.endswith((".", ";", ",")):
        capitalised = sum(1 for w in words if w[:1].isupper())
        return capitalised >= max(1, len(words) - 2)

    return False


def extract_plain_text(text: str) -> ExtractedDocument:
    """Treat each non-blank line as a block, preserving exact offsets."""
    blocks: list[ExtractedBlock] = []
    cursor = 0

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            # Offset of the stripped content within the original string, so a
            # CUAD span lands on the right clause.
            start = cursor + (len(line) - len(line.lstrip()))
            blocks.append(
                ExtractedBlock(
                    text=stripped,
                    char_start=start,
                    char_end=start + len(stripped),
                    is_heading=_looks_like_heading(stripped),
                )
            )
        cursor += len(line) + 1  # +1 for the newline removed by split

    return ExtractedDocument(text=text, blocks=blocks)
