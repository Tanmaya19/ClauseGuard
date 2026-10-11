"""Segmentation tests (REQ-2.1 to REQ-2.4)."""

from __future__ import annotations

import pytest

from app.db.models import SegmentationMethod
from app.services.extraction import extract
from app.services.extraction.base import ExtractedBlock, ExtractedDocument
from app.services.segmentation import MAX_CLAUSE_CHARS, rules, segment
from tests.fixtures import make_docx, make_pdf, make_unnumbered_docx


def _document(*texts: str, headings: set[int] | None = None) -> ExtractedDocument:
    headings = headings or set()
    blocks: list[ExtractedBlock] = []
    cursor = 0
    for i, text in enumerate(texts):
        blocks.append(
            ExtractedBlock(
                text=text,
                char_start=cursor,
                char_end=cursor + len(text),
                is_heading=i in headings,
            )
        )
        cursor += len(text) + 1
    return ExtractedDocument(text="\n".join(texts), blocks=blocks)


# --- Numbering rules -----------------------------------------------------
@pytest.mark.parametrize(
    "line",
    [
        "1. Indemnity",
        "12.3 Limitation of Liability",
        "4) Payment Terms",
        "ARTICLE IV - Confidentiality",
        "Section 7 Governing Law",
        "Clause 12.3 applies",
    ],
)
def test_numbering_opens_a_clause(line: str) -> None:
    assert rules.numbering_label(line) is not None


@pytest.mark.parametrize(
    "line",
    [
        "(a) The Supplier shall indemnify the Customer",
        "(iv) any consequential loss",
        "• bullet point continuation",
        "- dash continuation",
        "the parties agree as follows",
        "1872. was the year of the Contract Act",
    ],
)
def test_sub_items_and_prose_do_not_open_a_clause(line: str) -> None:
    """Sub-items must not open clauses: splitting "(a)" from "(b)" would
    fragment one indemnity provision and break asymmetry detection."""
    assert rules.numbering_label(line) is None


@pytest.mark.parametrize(
    "line", ["Page 4", "3 / 12", "Table of Contents", "IN WITNESS WHEREOF", "_______"]
)
def test_furniture_is_recognised(line: str) -> None:
    assert rules.is_furniture(line)


# --- Strategy cascade ----------------------------------------------------
@pytest.mark.parametrize("builder", [make_pdf, make_docx])
def test_numbered_contract_uses_the_numbering_strategy(builder) -> None:
    segments = segment(extract(builder(), "c"))

    assert all(s.method is SegmentationMethod.NUMBERING for s in segments)
    # 15 clauses plus the title block.
    assert 15 <= len(segments) <= 17


@pytest.mark.parametrize("builder", [make_pdf, make_docx])
def test_sub_items_stay_with_their_parent_clause(builder) -> None:
    document = _document(
        "12. Indemnity",
        "(a) The Supplier shall indemnify the Customer against all claims.",
        "(b) The Customer shall notify the Supplier promptly of any claim.",
        "13. Notices",
        "Any notice shall be in writing.",
        "14. Governing Law",
        "This Agreement is governed by Indian law.",
    )
    segments = segment(document)

    indemnity = next(s for s in segments if s.heading and "Indemnity" in s.heading)
    assert "(a)" in indemnity.text
    assert "(b)" in indemnity.text


def test_heading_strategy_used_when_numbering_is_absent() -> None:
    document = _document(
        "CONFIDENTIALITY",
        "The Supplier shall not disclose any Confidential Information.",
        "GOVERNING LAW",
        "This Agreement is governed by the laws of India.",
        "INDEMNITY",
        "The Supplier shall indemnify the Customer.",
        headings={0, 2, 4},
    )
    segments = segment(document)

    assert all(s.method is SegmentationMethod.HEADING for s in segments)
    assert len(segments) == 3


def test_paragraph_fallback_when_there_is_no_structure() -> None:
    """REQ-2.3: non-standard formatting must still produce clauses."""
    segments = segment(extract(make_unnumbered_docx(), "c.docx"))

    assert segments
    assert all(s.method is SegmentationMethod.PARAGRAPH for s in segments)


def test_long_unstructured_text_is_split_at_sentence_boundaries() -> None:
    """REQ-2.1's sentence model: a wall of text has to be divided somewhere,
    and a sentence boundary is the only defensible place."""
    sentence = (
        "The Supplier shall deliver the Goods in accordance with the agreed schedule "
        "and shall bear all costs of delivery. "
    )
    document = _document(sentence * 40)

    segments = segment(document)

    assert len(segments) > 1
    # Pieces must not start or end mid-sentence.
    for seg in segments:
        assert seg.text.strip().endswith(".")


# --- Ordering and identity ----------------------------------------------
@pytest.mark.parametrize("builder", [make_pdf, make_docx])
def test_ordinals_are_sequential_and_preserve_document_order(builder) -> None:
    """REQ-2.2: original position is data, not an accident of row order."""
    segments = segment(extract(builder(), "c"))

    assert [s.ordinal for s in segments] == list(range(len(segments)))
    assert [s.char_start for s in segments] == sorted(s.char_start for s in segments)


@pytest.mark.parametrize("builder", [make_pdf, make_docx])
def test_segmentation_is_deterministic(builder) -> None:
    """prepare_cuad.py and the API must agree exactly, or training data is
    shaped differently from served data."""
    data = builder()
    first = [s.text for s in segment(extract(data, "c"))]
    second = [s.text for s in segment(extract(data, "c"))]

    assert first == second


# --- Review flagging -----------------------------------------------------
def test_overlong_numbered_clause_is_flagged_not_silently_split() -> None:
    """REQ-2.4: under numbering, flag for review rather than cut a provision
    in half — the numbering told us where the clause ends, so splitting it
    would contradict the document's own structure.

    Needs enough clauses for the numbering strategy to be viable; with only
    one clause the cascade falls through to paragraph mode, which *does* split
    long runs at sentence boundaries (see the test below).
    """
    document = _document(
        "1. Indemnity",
        "The Supplier shall indemnify the Customer. " * 120,
        "2. Notices",
        "Any notice shall be in writing and sent by registered post.",
        "3. Governing Law",
        "This Agreement is governed by the laws of India.",
    )
    segments = segment(document)

    assert all(s.method is SegmentationMethod.NUMBERING for s in segments)

    indemnity = next(s for s in segments if s.heading and "Indemnity" in s.heading)
    assert indemnity.needs_manual_review
    assert indemnity.review_reason == "unusually_long"
    assert len(indemnity.text) > MAX_CLAUSE_CHARS


def test_fragment_is_flagged_for_review() -> None:
    document = _document("1. Term", "Short.", "2. Notices", "Also short.", "3. X", "Tiny.")
    segments = segment(document)

    assert any(s.review_reason == "unusually_short" for s in segments)


def test_empty_document_yields_no_segments() -> None:
    assert segment(ExtractedDocument(text="", blocks=[])) == []


@pytest.mark.parametrize("builder", [make_pdf, make_docx])
def test_pdf_and_docx_segment_into_identical_clauses(builder) -> None:
    """The invariant that extraction's line-vs-paragraph difference must not
    break: whichever format the contract arrived in, the pipeline sees the
    same clauses."""
    from_pdf = segment(extract(make_pdf(), "a.pdf"))
    from_docx = segment(extract(make_docx(), "a.docx"))

    assert [s.heading for s in from_pdf] == [s.heading for s in from_docx]
    assert [" ".join(s.text.split()) for s in from_pdf] == [
        " ".join(s.text.split()) for s in from_docx
    ]


def test_strategy_is_rejected_when_its_segments_are_mostly_fused() -> None:
    """Regression: a strategy must be judged on segment *quality*, not count.

    Found by auditing the CUAD conversion. A contract that numbers only a few
    long recitals satisfied the numbering strategy's "at least three groups"
    test while producing multi-thousand-character blobs — several provisions
    fused into one segment. Every one was then flagged over-long and dropped,
    which silently lost 70 of CUAD's 510 contracts.

    The cascade must now fall through to a strategy that divides the text
    further, rather than accepting unusable output.
    """
    recital = (
        "The Supplier shall provide the Services in accordance with the "
        "specifications agreed between the parties from time to time. "
    )
    # Three numbered items, each far longer than MAX_CLAUSE_CHARS.
    document = _document(
        "1. Scope",
        recital * 40,
        "2. Obligations",
        recital * 40,
        "3. Payment",
        recital * 40,
    )

    segments = segment(document)

    assert segments, "the cascade must produce something"
    assert all(
        s.method is SegmentationMethod.PARAGRAPH for s in segments
    ), "numbering produced fused blobs and should have been rejected"

    # The point of falling through: the result is usable rather than discarded.
    overlong = [s for s in segments if len(s.text) > MAX_CLAUSE_CHARS]
    assert not overlong, f"{len(overlong)} segments are still fused"


def test_numbering_is_kept_when_only_a_minority_of_segments_are_long() -> None:
    """The quality check must not be so eager that it discards good numbering.

    One long clause among several normal ones is ordinary drafting, and the
    document's own numbering remains the best available signal.
    """
    document = _document(
        "1. Indemnity",
        "The Supplier shall indemnify the Customer. " * 80,
        "2. Notices",
        "Any notice shall be in writing and sent by registered post.",
        "3. Governing Law",
        "This Agreement is governed by the laws of India.",
        "4. Insurance",
        "The Supplier shall maintain insurance throughout the term.",
    )

    segments = segment(document)

    assert all(s.method is SegmentationMethod.NUMBERING for s in segments)
    assert len(segments) == 4
