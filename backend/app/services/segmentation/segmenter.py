"""Clause segmentation (REQ-2.1 to REQ-2.4).

A three-strategy cascade, tried in order of how much structure it assumes:

1. **numbering** — the document numbers its clauses (``12.``, ``Article IV``).
   Most commercial contracts do, and this is by far the most reliable signal.
2. **heading** — no usable numbering, but extraction identified headings from
   font weight (PDF) or paragraph style (DOCX).
3. **paragraph** — no structure at all. Falls back to paragraph blocks, using
   a sentence-boundary model to divide runs that are too long to be one clause
   (REQ-2.3).

> **This module is imported by `ml/scripts/prepare_cuad.py`.** Training data
> must be segmented by exactly the code that segments at inference time.
> Reimplementing segmentation for training is the classic train/serve skew bug:
> the model learns on text shaped one way, is served text shaped another, and
> accuracy degrades with nothing in the loss curve to show why.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.db.models import SegmentationMethod
from app.services.extraction.base import ExtractedBlock, ExtractedDocument
from app.services.segmentation import rules

logger = logging.getLogger(__name__)

# A clause longer than this is almost certainly several provisions that the
# segmenter failed to separate. Flagged for review (REQ-2.4), not split:
# cutting a provision in half is worse than presenting it whole with a warning.
MAX_CLAUSE_CHARS = 2500

# Shorter than this and it is a fragment — a stray heading, a page number that
# escaped the furniture filter, half a table row.
MIN_CLAUSE_CHARS = 40

# Below this many detected clauses, a strategy is treated as having failed and
# the cascade moves on. A real contract has more provisions than this.
MIN_VIABLE_CLAUSES = 3

# A strategy can produce enough groups while still producing useless ones. Some
# contracts number only a handful of long recitals, so the numbering strategy
# yields (say) six segments averaging 4,000 characters — technically "viable" by
# count, but each one is several provisions fused together.
#
# This was found by auditing the CUAD conversion: 70 of 510 contracts produced
# no usable clauses at all, because their segments were nearly all flagged
# over-long and then dropped. Counting groups is not enough; their sizes have to
# be sane too, and when they are not the cascade should fall through to a
# strategy that divides the text further.
MAX_OVERLONG_FRACTION = 0.5

# When falling back to sentence splitting, group sentences up to this length.
SENTENCE_GROUP_TARGET = 1200


@dataclass(slots=True)
class Segment:
    """One candidate clause. Maps onto the ``clauses`` table."""

    ordinal: int
    text: str
    char_start: int
    char_end: int
    method: SegmentationMethod
    heading: str | None = None
    needs_manual_review: bool = False
    review_reason: str | None = None


def segment(document: ExtractedDocument) -> list[Segment]:
    """Divide an extracted document into ordered clause candidates."""
    blocks = [b for b in document.blocks if not rules.is_furniture(b.text)]

    if not blocks:
        return []

    for strategy, method in (
        (_segment_by_numbering, SegmentationMethod.NUMBERING),
        (_segment_by_heading, SegmentationMethod.HEADING),
        (_segment_by_paragraph, SegmentationMethod.PARAGRAPH),
    ):
        # Paragraph splitting is the last resort: it always accepts, because
        # something has to.
        last_resort = method is SegmentationMethod.PARAGRAPH

        groups = strategy(blocks)
        if len(groups) < MIN_VIABLE_CLAUSES and not last_resort:
            continue

        segments = _finalise(groups, method)
        if last_resort or _segments_are_usable(segments, method):
            logger.info("Segmented with %s into %d clauses", method.value, len(segments))
            return segments

    return []


def _segments_are_usable(segments: list[Segment], method: SegmentationMethod) -> bool:
    """Reject a strategy whose output is mostly fused provisions.

    See ``MAX_OVERLONG_FRACTION``. Without this check a contract that numbers
    only its recitals is segmented into a handful of multi-thousand-character
    blobs, every one of them flagged for review and useless to the classifier.
    """
    if not segments:
        return False

    overlong = sum(1 for s in segments if len(s.text) > MAX_CLAUSE_CHARS)
    fraction = overlong / len(segments)

    if fraction > MAX_OVERLONG_FRACTION:
        logger.info(
            "Rejecting %s: %d of %d segments exceed %d characters",
            method.value,
            overlong,
            len(segments),
            MAX_CLAUSE_CHARS,
        )
        return False

    return True


# --------------------------------------------------------------------------
# Strategies
# --------------------------------------------------------------------------
def _segment_by_numbering(blocks: list[ExtractedBlock]) -> list[list[ExtractedBlock]]:
    groups: list[list[ExtractedBlock]] = []
    current: list[ExtractedBlock] = []

    for block in blocks:
        opens_clause = rules.numbering_label(block.text) is not None
        if opens_clause and current:
            groups.append(current)
            current = [block]
        elif opens_clause:
            current = [block]
        elif current:
            current.append(block)
        else:
            # Preamble before the first numbered clause (recitals, parties).
            current = [block]

    if current:
        groups.append(current)

    return groups


def _segment_by_heading(blocks: list[ExtractedBlock]) -> list[list[ExtractedBlock]]:
    if not any(b.is_heading for b in blocks):
        return []

    groups: list[list[ExtractedBlock]] = []
    current: list[ExtractedBlock] = []

    for block in blocks:
        if block.is_heading and current:
            groups.append(current)
            current = [block]
        else:
            current.append(block)

    if current:
        groups.append(current)

    return groups


def _segment_by_paragraph(blocks: list[ExtractedBlock]) -> list[list[ExtractedBlock]]:
    """One group per block, with over-long blocks divided at sentence bounds.

    This is where REQ-2.1's sentence-boundary model earns its place: with no
    numbering and no headings, a wall of text has to be divided somewhere, and
    a sentence boundary is the only defensible place to do it.
    """
    groups: list[list[ExtractedBlock]] = []

    for block in blocks:
        if len(block.text) <= MAX_CLAUSE_CHARS:
            groups.append([block])
            continue

        pieces = _split_at_sentences(block)
        groups.extend([piece] for piece in pieces)

    return groups


def _split_at_sentences(block: ExtractedBlock) -> list[ExtractedBlock]:
    """Divide one long block into sentence-aligned pieces, preserving offsets."""
    sentences = _sentences(block.text)
    if len(sentences) < 2:
        return [block]

    pieces: list[ExtractedBlock] = []
    buffer: list[str] = []
    buffer_len = 0
    offset = 0

    def flush() -> None:
        nonlocal buffer, buffer_len, offset
        if not buffer:
            return
        text = " ".join(buffer)
        pieces.append(
            ExtractedBlock(
                text=text,
                char_start=block.char_start + offset,
                char_end=block.char_start + offset + len(text),
                page=block.page,
                is_heading=False,
            )
        )
        offset += len(text) + 1
        buffer = []
        buffer_len = 0

    for sentence in sentences:
        buffer.append(sentence)
        buffer_len += len(sentence) + 1
        if buffer_len >= SENTENCE_GROUP_TARGET:
            flush()

    flush()
    return pieces or [block]


def _sentences(text: str) -> list[str]:
    """Sentence boundaries via pysbd, with a regex fallback.

    pysbd is used rather than a naive split on ``.`` because contract text is
    dense with abbreviations ("No.", "Ltd.", "Cl. 4.2", "Rs. 50,000") that a
    period-split would treat as sentence ends, fragmenting clauses mid-phrase.
    """
    try:
        import pysbd

        segmenter = pysbd.Segmenter(language="en", clean=False)
        found = [s.strip() for s in segmenter.segment(text) if s.strip()]
        if found:
            return found
    except Exception:  # pysbd absent or failed on pathological input
        logger.debug("pysbd unavailable; using regex sentence fallback", exc_info=True)

    return [s.strip() for s in re.split(r"(?<=[.;])\s+(?=[A-Z])", text) if s.strip()]


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------
def _finalise(
    groups: list[list[ExtractedBlock]], method: SegmentationMethod
) -> list[Segment]:
    segments: list[Segment] = []
    ordinal = 0

    for group in groups:
        text = "\n".join(b.text for b in group).strip()
        if not text:
            continue

        heading = _heading_for(group, method)
        needs_review, reason = _review_flag(text)

        segments.append(
            Segment(
                ordinal=ordinal,
                text=text,
                char_start=group[0].char_start,
                char_end=group[-1].char_end,
                method=method,
                heading=heading,
                needs_manual_review=needs_review,
                review_reason=reason,
            )
        )
        ordinal += 1

    return segments


def _heading_for(group: list[ExtractedBlock], method: SegmentationMethod) -> str | None:
    first = group[0].text.strip()

    if method is SegmentationMethod.HEADING and group[0].is_heading:
        return first[:512]

    if method is SegmentationMethod.NUMBERING:
        label = rules.numbering_label(first)
        if label:
            # Keep the numbering token plus any short title on the same line,
            # e.g. "12. Indemnity" -> that whole string; a numbered line that
            # runs straight into prose yields just the token.
            remainder = first[len(label) :].lstrip(" .)-–—")
            title = remainder.split(".")[0].strip()
            if title and len(title) <= 80:
                return f"{label} {title}"[:512]
            return label[:512]

    return None


def _review_flag(text: str) -> tuple[bool, str | None]:
    """REQ-2.4: surface ambiguous segments instead of misclassifying silently."""
    if len(text) > MAX_CLAUSE_CHARS:
        return True, "unusually_long"
    if len(text) < MIN_CLAUSE_CHARS:
        return True, "unusually_short"
    return False, None
