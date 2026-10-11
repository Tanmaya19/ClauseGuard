"""PDF text extraction via PyMuPDF (REQ-1.3).

Uses the "dict" extraction mode rather than plain ``page.get_text()`` because
the latter returns a flat string, discarding the font metadata that lets us
tell a heading from body text. That signal is needed by segmentation and
cannot be recovered later.
"""

from __future__ import annotations

import logging

from app.services.extraction.base import (
    CorruptFileError,
    EncryptedFileError,
    ExtractedBlock,
    ExtractedDocument,
    NoExtractableTextError,
)

logger = logging.getLogger(__name__)

# A page of real contract text runs to thousands of characters. Anything under
# this across the whole document means we got page furniture (headers, stamps,
# page numbers) rather than content — i.e. an image-only PDF.
MIN_MEANINGFUL_CHARS = 200

# A heading is set larger than body text. Contracts are typically 10-11pt, so
# this ratio marks a run as a heading only when it is clearly larger than the
# document's own median size, rather than against a fixed point size.
HEADING_SIZE_RATIO = 1.15
MAX_HEADING_CHARS = 160


def extract_pdf(data: bytes) -> ExtractedDocument:
    import pymupdf  # imported lazily so the module imports without the dep

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # pymupdf raises a variety of types
        raise CorruptFileError(str(exc)) from exc

    try:
        if doc.needs_pass:
            raise EncryptedFileError("PDF requires a password")

        spans = _collect_spans(doc)
        page_count = doc.page_count
    finally:
        doc.close()

    if not spans:
        raise NoExtractableTextError("no text spans found")

    median_size = _median(sorted(s["size"] for s in spans if s["text"].strip()))

    parts: list[str] = []
    blocks: list[ExtractedBlock] = []
    cursor = 0

    for span in spans:
        text = span["text"].strip()
        if not text:
            continue

        start = cursor
        parts.append(text)
        cursor += len(text) + 1  # +1 for the newline joined in below

        blocks.append(
            ExtractedBlock(
                text=text,
                char_start=start,
                char_end=start + len(text),
                page=span["page"],
                is_heading=_looks_like_heading(text, span, median_size),
            )
        )

    assembled = "\n".join(parts)

    if len(assembled.strip()) < MIN_MEANINGFUL_CHARS:
        # REQ-1.4: report this as unreadable rather than handing a few
        # characters of letterhead to the classifier.
        raise NoExtractableTextError(
            f"only {len(assembled.strip())} characters extracted from {page_count} page(s)"
        )

    return ExtractedDocument(text=assembled, blocks=blocks, page_count=page_count)


def _collect_spans(doc: object) -> list[dict]:
    """Flatten the PyMuPDF dict structure into one entry per text line.

    Line granularity, not span granularity: a single line is often split into
    several spans by incidental styling (a bolded defined term mid-sentence),
    and joining those back up front avoids fragmenting clause text.
    """
    collected: list[dict] = []

    for page_number, page in enumerate(doc, start=1):  # type: ignore[call-overload]
        try:
            payload = page.get_text("dict")
        except Exception:  # a single damaged page should not fail the document
            logger.warning("Could not extract page %s; skipping", page_number)
            continue

        for block in payload.get("blocks", ()):
            if block.get("type") != 0:  # 0 = text, 1 = image
                continue
            for line in block.get("lines", ()):
                line_spans = line.get("spans", ())
                if not line_spans:
                    continue
                text = "".join(s.get("text", "") for s in line_spans)
                sizes = [s.get("size", 0.0) for s in line_spans]
                flags = [s.get("flags", 0) for s in line_spans]
                collected.append(
                    {
                        "text": text,
                        "size": max(sizes) if sizes else 0.0,
                        # PyMuPDF flag bit 4 (value 16) marks bold.
                        "bold": any(f & 16 for f in flags),
                        "page": page_number,
                    }
                )

    return collected


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def _looks_like_heading(text: str, span: dict, median_size: float) -> bool:
    if len(text) > MAX_HEADING_CHARS:
        return False
    # A heading does not end in a sentence period; "12. Indemnity" does, so
    # only a trailing period on a long run disqualifies it.
    if median_size and span["size"] >= median_size * HEADING_SIZE_RATIO:
        return True
    if span.get("bold") and len(text) <= 80:
        return True
    # ALL CAPS short lines are the most common contract heading style.
    letters = [c for c in text if c.isalpha()]
    if letters and len(text) <= 80 and all(c.isupper() for c in letters):
        return True
    return False
