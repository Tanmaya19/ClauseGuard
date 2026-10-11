"""Detector primitives for the risk rubric (REQ-4.2).

Each primitive is a small, independently testable predicate. Rules in
``rubrics/*.yaml`` compose them; no rule contains logic of its own. That is
what lets the rubric be edited without touching Python (REQ-4.4) and what keeps
every risk decision traceable to a named criterion rather than a model score.

A primitive returns ``True`` when the condition it names is **present**, which
for the ``absent_*`` family means the absence is present.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Context
# --------------------------------------------------------------------------

# Role words that identify the two sides of a commercial agreement. Used for
# asymmetry detection; deliberately generous, since Indian vendor agreements
# vary in naming ("Service Provider", "Vendor", "Contractor", "Supplier").
SUPPLIER_SIDE = (
    "supplier", "vendor", "service provider", "contractor", "consultant",
    "seller", "licensor", "manufacturer", "agency", "developer",
)
CUSTOMER_SIDE = (
    "customer", "client", "purchaser", "buyer", "licensee", "company",
    "principal", "employer", "owner",
)

# Indian jurisdiction markers. Presence of any means the clause points at India.
INDIAN_JURISDICTION = (
    "india", "indian", "new delhi", "delhi", "mumbai", "bombay", "bengaluru",
    "bangalore", "chennai", "madras", "kolkata", "calcutta", "hyderabad",
    "pune", "ahmedabad", "gurgaon", "gurugram", "noida", "chandigarh",
)
FOREIGN_JURISDICTION = (
    "singapore", "london", "england", "wales", "new york", "delaware",
    "california", "dubai", "united arab emirates", "hong kong", "switzerland",
    "geneva", "zurich", "paris", "france", "germany", "netherlands",
    "united states", "u.s.a", "usa", "united kingdom", "u.k.", "japan",
    "australia", "canada", "mauritius", "cayman",
)


@dataclass(slots=True)
class RiskContext:
    """Everything a detector may inspect about one clause.

    ``contract_text`` is carried so contract-wide facts (which party names the
    agreement actually uses) are available without re-deriving them per clause.
    """

    text: str
    labels: frozenset[str] = frozenset()
    contract_text: str = ""
    _lower: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        self._lower = self.text.lower()

    @property
    def lower(self) -> str:
        return self._lower


# --------------------------------------------------------------------------
# Phrase primitives
# --------------------------------------------------------------------------
def _phrase_present(haystack: str, phrase: str) -> bool:
    """Word-boundary phrase match, so "audit" does not fire on "auditorium"."""
    return re.search(rf"\b{re.escape(phrase.lower())}\b", haystack) is not None


def present_any(ctx: RiskContext, phrases: list[str]) -> bool:
    return any(_phrase_present(ctx.lower, p) for p in phrases)


def present_all(ctx: RiskContext, phrases: list[str]) -> bool:
    return all(_phrase_present(ctx.lower, p) for p in phrases)


def absent_any(ctx: RiskContext, phrases: list[str]) -> bool:
    """True when none of the phrases appear.

    This is the workhorse of the rubric. Most contract risk is an *absence* —
    no liability cap, no cure period, no notice window — and absence is only
    meaningful once the clause type is known, which is why rules carry
    ``applies_to``.
    """
    return not any(_phrase_present(ctx.lower, p) for p in phrases)


def present_pattern(ctx: RiskContext, pattern: str) -> bool:
    return re.search(pattern, ctx.text, re.IGNORECASE) is not None


def absent_pattern(ctx: RiskContext, pattern: str) -> bool:
    return re.search(pattern, ctx.text, re.IGNORECASE) is None


# --------------------------------------------------------------------------
# Numeric primitives
# --------------------------------------------------------------------------
# Period lengths in contracts are written many ways, and the forms are not
# interchangeable in a regex:
#     "within 45 days"                 digits before the unit
#     "within ninety (90) days"        word, then digits in brackets
#     "a period of twenty-four months" words only
#     "Net 30"                         invoicing shorthand, no unit word
# So rather than one pattern per form, find the unit word and look backwards a
# short window for a figure, in digits or in words.

_UNIT_DAYS = {"day": 1, "days": 1, "week": 7, "weeks": 7, "month": 30, "months": 30,
              "year": 365, "years": 365}

_PERIOD_UNIT = re.compile(
    r"\b(?:business|working|calendar|clear)?\s*"
    r"(day|days|week|weeks|month|months|year|years)\b",
    re.IGNORECASE,
)
_DIGITS = re.compile(r"(\d{1,4})")
_NET_TERMS = re.compile(r"\bnet\s+(\d{1,3})\b", re.IGNORECASE)

# Enough spelled-out numbers to cover ordinary contractual periods.
_WORD_UNITS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_WORD_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
_WORD_NUMBER = re.compile(
    r"\b(" + "|".join([*_WORD_TENS, *_WORD_UNITS]) + r")(?:[\s-]+(" +
    "|".join(_WORD_UNITS) + r"))?\b",
    re.IGNORECASE,
)

# How far back from the unit word to look for its figure. "ninety (90) days"
# needs ~12 characters; "a period of twenty-four (24) calendar months" ~30.
_FIGURE_WINDOW = 45


def _word_to_int(first: str, second: str | None) -> int | None:
    first = first.lower()
    if first in _WORD_TENS:
        base = _WORD_TENS[first]
        if second and second.lower() in _WORD_UNITS:
            return base + _WORD_UNITS[second.lower()]
        return base
    return _WORD_UNITS.get(first)


def _period_mentions(text: str) -> list[tuple[int, int]]:
    """Return (length_in_days, character_position) for every period mentioned.

    Position is kept so a detector can ask whether a period appears *near*
    particular language — which is how "is a notice period stated?" differs
    from "does any number appear?".
    """
    found: list[tuple[int, int]] = []

    for match in _PERIOD_UNIT.finditer(text):
        unit = match.group(1).lower()
        multiplier = _UNIT_DAYS[unit]
        window = text[max(0, match.start() - _FIGURE_WINDOW) : match.start()]

        digits = _DIGITS.findall(window)
        if digits:
            # Nearest figure to the unit word wins: in "ninety (90) days" both
            # forms are present and the bracketed digits are authoritative.
            value = int(digits[-1])
        else:
            words = _WORD_NUMBER.findall(window)
            value = _word_to_int(*words[-1]) if words else None  # type: ignore[misc]
            if value is None:
                continue

        # Four-digit figures are years in citations ("the Contract Act, 1872"),
        # not durations.
        if 0 < value < 3650:
            found.append((value * multiplier, match.start()))

    for match in _NET_TERMS.finditer(text):
        found.append((int(match.group(1)), match.start()))

    return found


def _day_counts(text: str) -> list[int]:
    return [days for days, _ in _period_mentions(text)]


def numeric_days_gt(ctx: RiskContext, limit: int) -> bool:
    counts = _day_counts(ctx.text)
    return bool(counts) and max(counts) > limit


def numeric_days_lt(ctx: RiskContext, limit: int) -> bool:
    counts = _day_counts(ctx.text)
    return bool(counts) and min(counts) < limit


def has_no_period(ctx: RiskContext, _arg: bool = True) -> bool:
    """True when the clause states no time period at all."""
    return not _day_counts(ctx.text)


# --- Notice periods ------------------------------------------------------
# "Is a notice period stated?" is not "does any number appear?". A renewal
# clause reading "successive periods of twelve months ... unless notice is
# given" states a *term* of twelve months and no *notice* period at all. Using
# any-number-present as the proxy would read that clause as safe, which is the
# opposite of correct — so notice detection is anchored to notice language.

_NOTICE_WORDS = re.compile(
    r"\b(notice|notify|notifying|notification|intimation|intimate)\b", re.IGNORECASE
)

# Tight, because loose proximity reads the wrong number. In
#
#     "...renew for successive periods of twelve months at the end of the
#      initial term. The Agreement shall be deemed renewed unless written
#      notice is given."
#
# the only figure is the renewal *term*, and the notice requirement has no
# length at all. A 120-character window treated that as a 360-day notice
# period and reported the clause as merely long-winded rather than as an
# auto-renewal with no opt-out — the opposite of the right answer.
#
# So a figure counts as a notice period only when it sits immediately beside
# the notice word ("30 days' prior written notice", "notice of 60 days") and
# no sentence boundary separates them.
_NOTICE_PROXIMITY = 40
_SENTENCE_BREAK = re.compile(r"\.\s")


def _notice_periods(text: str) -> list[int]:
    notices = [(m.start(), m.end()) for m in _NOTICE_WORDS.finditer(text)]
    if not notices:
        return []

    found: list[int] = []
    for days, position in _period_mentions(text):
        for start, end in notices:
            low, high = min(position, start), max(position, end)
            if high - low > _NOTICE_PROXIMITY + (end - start):
                continue
            if _SENTENCE_BREAK.search(text[low:high]):
                continue
            found.append(days)
            break

    return found


def notice_period_absent(ctx: RiskContext, _arg: bool = True) -> bool:
    """True when the clause states no notice period.

    Covers both "no notice language at all" and "notice is mentioned but no
    length is given" — both leave the other party free to act immediately.
    """
    return not _notice_periods(ctx.text)


def notice_period_gt(ctx: RiskContext, limit: int) -> bool:
    periods = _notice_periods(ctx.text)
    return bool(periods) and max(periods) > limit


# --------------------------------------------------------------------------
# Structural primitives
# --------------------------------------------------------------------------
# Verbs that impose a duty. Matched with their surrounding words so we can see
# which party is the subject.
_OBLIGATION = re.compile(
    r"\b(shall|must|agrees to|undertakes to|is required to|will be liable|"
    r"shall be liable|shall indemnify|indemnifies)\b",
    re.IGNORECASE,
)

_SUBJECT_WINDOW = 90


def one_sided_obligation(ctx: RiskContext, _arg: bool = True) -> bool:
    """True when every duty in the clause falls on one side only.

    How it works: for each obligation verb, look back a short window for a
    party role word, and record which side that duty lands on. If duties
    appear and they all land on the same side, the clause is one-directional.

    **Known limitation.** ClauseGuard does not currently ask which party the
    user is, so this flags asymmetry in either direction rather than asymmetry
    against the user specifically. A one-sided clause is worth a user's
    attention regardless of direction — but once the upload flow captures the
    user's role, this detector should narrow to clauses that disadvantage them.
    Recorded in docs/TRACEABILITY.md as future work.
    """
    sides: set[str] = set()

    for match in _OBLIGATION.finditer(ctx.text):
        window = ctx.lower[max(0, match.start() - _SUBJECT_WINDOW) : match.start()]
        if any(_phrase_present(window, t) for t in SUPPLIER_SIDE):
            sides.add("supplier")
        if any(_phrase_present(window, t) for t in CUSTOMER_SIDE):
            sides.add("customer")

    # "each party", "both parties", "either party" are explicitly mutual.
    if present_any(ctx, ["each party", "both parties", "either party", "the parties"]):
        return False

    return len(sides) == 1


_PERMISSION = re.compile(
    r"\b(may|shall be entitled to|is entitled to|reserves the right|"
    r"at its sole discretion|at its option|shall have the right)\b",
    re.IGNORECASE,
)


def one_sided_right(ctx: RiskContext, _arg: bool = True) -> bool:
    """True when a discretionary *right* is given to one side only.

    Distinct from ``one_sided_obligation`` because the grammar differs: a duty
    reads "the Supplier **shall** indemnify", a right reads "the Customer
    **may** terminate". A termination-for-convenience clause is one-sided by
    virtue of who *may* act, so matching only obligation verbs would miss it
    entirely.
    """
    sides: set[str] = set()

    for match in _PERMISSION.finditer(ctx.text):
        window = ctx.lower[max(0, match.start() - _SUBJECT_WINDOW) : match.start()]
        if any(_phrase_present(window, t) for t in SUPPLIER_SIDE):
            sides.add("supplier")
        if any(_phrase_present(window, t) for t in CUSTOMER_SIDE):
            sides.add("customer")

    if present_any(ctx, ["each party", "both parties", "either party", "the parties"]):
        return False

    return len(sides) == 1


def foreign_jurisdiction(ctx: RiskContext, _arg: bool = True) -> bool:
    """True when the clause names a non-Indian forum and no Indian one."""
    has_foreign = any(_phrase_present(ctx.lower, p) for p in FOREIGN_JURISDICTION)
    has_indian = any(_phrase_present(ctx.lower, p) for p in INDIAN_JURISDICTION)
    return has_foreign and not has_indian


def unbounded_duration(ctx: RiskContext, _arg: bool = True) -> bool:
    return present_any(
        ctx,
        [
            "in perpetuity", "perpetual", "perpetually", "indefinitely",
            "for all time", "without limit of time", "survive indefinitely",
        ],
    )


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------
PRIMITIVES = {
    "present_any": present_any,
    "present_all": present_all,
    "absent_any": absent_any,
    "present_pattern": present_pattern,
    "absent_pattern": absent_pattern,
    "numeric_days_gt": numeric_days_gt,
    "numeric_days_lt": numeric_days_lt,
    "has_no_period": has_no_period,
    "notice_period_absent": notice_period_absent,
    "notice_period_gt": notice_period_gt,
    "one_sided_obligation": one_sided_obligation,
    "one_sided_right": one_sided_right,
    "foreign_jurisdiction": foreign_jurisdiction,
    "unbounded_duration": unbounded_duration,
}

__all__ = ["PRIMITIVES", "RiskContext"]
