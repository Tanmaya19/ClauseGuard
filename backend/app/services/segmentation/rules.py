"""Boundary-detection patterns for clause segmentation (REQ-2.1).

The central judgement encoded here: **top-level numbering and headings start a
new clause; lettered and roman sub-items do not.**

A typical indemnity provision reads:

    12. Indemnity
        (a) The Supplier shall indemnify the Customer against ...
        (b) The Customer shall promptly notify the Supplier of ...

Treating ``(a)`` and ``(b)`` as separate clauses would fragment one provision
into pieces that individually lose their meaning — and the risk rubric's
asymmetry detection specifically needs both halves of a reciprocal obligation
in the same clause to tell a one-sided indemnity from a mutual one. So
sub-items continue the clause they belong to.
"""

from __future__ import annotations

import re

# --- Boundaries that start a new clause ----------------------------------

# "1." / "1.1" / "2.3.4" / "5)" followed by real content.
DECIMAL_NUMBERING = re.compile(r"^(\d{1,2}(?:\.\d{1,3}){0,3})[.)]?\s+(?=\S)")

# "ARTICLE IV" / "Section 7" / "Clause 12.3" / "SCHEDULE 2"
KEYWORD_NUMBERING = re.compile(
    r"^(article|clause|section|schedule|annexure|annex|appendix)\s+"
    r"([0-9]{1,3}(?:\.[0-9]{1,3})*|[ivxlcdm]{1,7})\b",
    re.IGNORECASE,
)

# --- Boundaries that do NOT start a new clause ---------------------------

# "(a)" / "(ii)" / "a." at the start of a sub-item.
SUB_ITEM = re.compile(r"^(\(\s*[a-z]{1,3}\s*\)|\(\s*[ivxlcdm]{1,5}\s*\)|[a-z][.)])\s+(?=\S)")

# Bullet glyphs, which are always continuations.
BULLET = re.compile(r"^[•●▪‣⁃\-\*·]\s+")


def numbering_label(line: str) -> str | None:
    """Return the numbering token if this line opens a new clause, else None."""
    stripped = line.lstrip()

    if SUB_ITEM.match(stripped) or BULLET.match(stripped):
        return None

    match = DECIMAL_NUMBERING.match(stripped)
    if match:
        token = match.group(1)
        # A year or a money amount at the start of a line is not a clause
        # number. "2024. The parties agree" is vanishingly rare; "1872" as in
        # the Indian Contract Act is not.
        if "." not in token and len(token) == 4:
            return None
        return token

    match = KEYWORD_NUMBERING.match(stripped)
    if match:
        return f"{match.group(1).title()} {match.group(2)}"

    return None


def is_sub_item(line: str) -> bool:
    stripped = line.lstrip()
    return bool(SUB_ITEM.match(stripped) or BULLET.match(stripped))


# --- Headings ------------------------------------------------------------

# Lines that look like a heading but are document furniture, not clauses.
FURNITURE = re.compile(
    r"^(page\s+\d+|\d+\s*/\s*\d+|table of contents|contents|"
    r"in witness whereof|signature|signed (by|for)|for and on behalf of)\b",
    re.IGNORECASE,
)


def is_furniture(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if FURNITURE.match(stripped):
        return True
    # A line of only digits, punctuation or underscores (page numbers, signature
    # rules) carries no contractual content.
    return not any(c.isalpha() for c in stripped)
