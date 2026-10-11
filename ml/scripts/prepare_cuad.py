#!/usr/bin/env python
"""Convert CUAD from span extraction into a multi-label clause dataset.

CUAD is distributed in SQuAD format: each contract is one `context` string and
each of the 41 categories is a `question` whose answers are highlighted spans.
It is **not** a classification dataset, and converting it is the single most
error-prone step in the whole project — if the mapping is noisy, every metric
downstream is meaningless and the loss curve will not tell you.

Procedure (PLAN.md 4.1):

1. Parse annotated spans per contract.
2. Segment each contract with the **production** segmenter.
3. Label a clause with L when an L-span overlaps it past an IoU threshold.
4. Unlabelled clauses become negatives, after boilerplate removal.
5. Split **by contract**, never by clause.

Usage
-----
    # 1. Download CUAD (about 100 MB):
    #    https://github.com/TheAtticusProject/cuad  ->  CUADv1.json
    #    place it at ml/data/raw/CUADv1.json
    python ml/scripts/prepare_cuad.py --audit 50

The ``--audit`` flag writes a sample of mapped clauses to
``ml/data/processed/audit_sample.txt`` for hand-checking. **Do that before
training.** Eyeball 50 clauses and confirm the labels are right; if they are
not, adjust ``--iou`` and repeat.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

# Import the production code rather than reimplementing it. This is the whole
# point: training data must be shaped by the same segmenter that shapes served
# data, or the model learns on a distribution it will never see again.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.classification.labels import LABEL_KEYS  # noqa: E402
from app.services.extraction import extract_plain_text  # noqa: E402
from app.services.segmentation import segment  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("prepare_cuad")

DEFAULT_RAW = REPO_ROOT / "ml" / "data" / "raw" / "CUADv1.json"
DEFAULT_OUT = REPO_ROOT / "ml" / "data" / "processed"
MAPPING_FILE = REPO_ROOT / "ml" / "configs" / "label_mapping.yaml"

# Clauses shorter than this are fragments; longer ones are failed segmentation.
#
# MAX_CHARS is deliberately aligned with the segmenter's own MAX_CLAUSE_CHARS
# rather than set looser. Auditing showed that blocks between those two values
# are typically several numbered sections fused together — "12.3 Waiver ...
# 12.4 Assignment ... 12.5 Governing Law" as one segment — because the source
# PDF put them on one flattened line. A span for any one of those sections then
# labels the whole blob, which is where most of the observed label noise came
# from. Training only on clauses the segmenter handled cleanly costs some
# volume and buys a great deal of label accuracy.
MIN_CHARS = 40
MAX_CHARS = 2500

# A span must be either a good IoU match, or substantially contained AND
# material relative to the clause. The second condition is what stops a
# two-line highlight inside a 2,000-character fused block from labelling the
# whole block: containment alone is satisfied by any short span that happens to
# fall inside.
MIN_SPAN_FRACTION_OF_CLAUSE = 0.15

# Boilerplate that would otherwise flood the negative class.
BOILERPLATE_CUES = (
    "in witness whereof", "signature page", "table of contents",
    "intentionally left blank", "[signature", "by:", "name:", "title:",
)

# CUAD's contracts are SEC filings, and the filing furniture is printed in the
# page margins. Once the PDF is flattened to text those lines land *inside*
# clause bodies, mid-sentence. Auditing the conversion showed clause text of
# the form:
#
#     "...including
#      [ * ] = Certain confidential information contained in this document,
#      marked by brackets, has been omitted and filed separately with the
#      Securities and Exchange Commission pursuant to Rule 24b-2...
#      making all contact with relevant Regulatory Authorities..."
#
# A whole-clause boilerplate check cannot catch that, because the clause is
# genuine and only its interior is polluted. These lines are therefore removed
# line by line before the clause is emitted. Left in, they would teach the
# model that SEC redaction notices are part of contractual language.
FURNITURE_LINE = re.compile(
    r"^\s*(?:"
    r"\[\s*\*\s*\]\s*=.*?(?:securities and exchange commission|omitted).*"
    r"|source:\s*[A-Z0-9 ,./&'\-]+,?\s*(?:10-[KQ]|8-K|S-1|F-1|20-F|DEF 14A|485BPOS).*"
    r"|certain (?:confidential )?(?:information|portions).*?(?:omitted|redacted).*"
    r"|\*{3,}"
    r"|page\s+\d+\s*(?:of\s*\d+)?"
    r"|confidential treatment (?:has been )?requested.*"
    r")\s*$",
    re.IGNORECASE,
)


def strip_furniture(text: str) -> str:
    kept = [line for line in text.splitlines() if not FURNITURE_LINE.match(line)]
    return "\n".join(kept).strip()


# A clause must contain at least one sentence, not just a section heading.
# "SECTION 4 DEVELOPMENT AND COMMERCIALIZATION OF THE CO-BRANDED SITE" cleared
# the 40-character floor but is a heading, not a provision.
def is_heading_only(text: str) -> bool:
    body = text.strip()
    if len(body) > 200:
        return False
    # No sentence-ending punctuation anywhere, or fewer than eight words.
    if not any(c in body for c in ".;:"):
        return True
    return len(body.split()) < 8


@dataclass(slots=True)
class ClauseExample:
    contract: str
    ordinal: int
    text: str
    labels: list[str]
    segmentation_method: str


# --------------------------------------------------------------------------
# Label mapping
# --------------------------------------------------------------------------
def load_mapping() -> dict[str, str]:
    """CUAD category -> our class key, validated against the taxonomy."""
    raw = yaml.safe_load(MAPPING_FILE.read_text(encoding="utf-8"))

    flat: dict[str, str] = {}
    for class_key, categories in (raw.get("mapping") or {}).items():
        if class_key not in LABEL_KEYS:
            raise SystemExit(f"label_mapping.yaml: unknown class {class_key!r}")
        for category in categories or []:
            if category in flat:
                raise SystemExit(f"label_mapping.yaml: {category!r} mapped twice")
            flat[category] = class_key

    logger.info(
        "Mapping covers %d CUAD categories across %d classes", len(flat), len(LABEL_KEYS)
    )
    return flat


def _normalise_category(question: str) -> str:
    """CUAD questions embed the category after the last 'related to'.

    Format is roughly:
      "Highlight the parts (if any) of this contract related to
       "Governing Law" that should be reviewed..."
    """
    if '"' in question:
        parts = question.split('"')
        if len(parts) >= 2:
            return parts[1].strip()
    return question.strip()


# --------------------------------------------------------------------------
# Conversion
# --------------------------------------------------------------------------
# A table of contents reads as a run of "number heading page-number" triples:
#     "20.1 Confidential Terms 41 20.2 Governing Law 41 20.3 Force Majeure 41"
# It is mostly alphabetic, so the ratio check below passes it, and it contains
# every clause heading in the document — so spans land on it and it acquires
# labels it has no business carrying. One was found in the audit sample
# labelled parties_definitions.
TOC_ENTRY = re.compile(r"\b\d{1,2}(?:\.\d{1,2})?\s+[A-Z][A-Za-z ,'&/-]{3,40}\s+\d{1,3}\b")
TOC_MIN_ENTRIES = 3


def _looks_like_contents(text: str) -> bool:
    return len(TOC_ENTRY.findall(text)) >= TOC_MIN_ENTRIES


def _is_boilerplate(text: str) -> bool:
    lowered = text.lower()
    if any(cue in lowered for cue in BOILERPLATE_CUES):
        return True
    if _looks_like_contents(text):
        return True
    # Mostly non-alphabetic (tables of figures, dotted TOC leaders).
    letters = sum(1 for c in text if c.isalpha())
    return letters < len(text) * 0.5


def _iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    overlap = max(0, min(a_end, b_end) - max(a_start, b_start))
    if overlap == 0:
        return 0.0
    union = max(a_end, b_end) - min(a_start, b_start)
    return overlap / union if union else 0.0


def _span_covered(span_start: int, span_end: int, clause_start: int, clause_end: int) -> float:
    """Fraction of the *span* that lies inside the clause.

    Used alongside IoU because CUAD spans are often much shorter than the
    clause containing them — a one-sentence highlight inside a 900-character
    indemnity clause has a low IoU but is fully contained, and that clause
    unambiguously *is* an indemnity clause.
    """
    overlap = max(0, min(span_end, clause_end) - max(span_start, clause_start))
    length = span_end - span_start
    return overlap / length if length else 0.0


def _assigns_label(
    span_start: int,
    span_end: int,
    clause_start: int,
    clause_end: int,
    clause_length: int,
    iou_threshold: float,
    containment: float,
) -> bool:
    """Decide whether an annotated span labels this clause.

    Two independent routes, and the second carries an extra condition:

    * **IoU** — the span and the clause describe substantially the same text.
    * **Containment** — the span sits inside the clause. CUAD highlights are
      often far shorter than the provision containing them, so this route is
      necessary; but on its own it also labels a whole 2,000-character block
      from a two-line highlight, which is where the audit found most of the
      label noise. It therefore additionally requires the span to be a
      material fraction of the clause.
    """
    if _iou(span_start, span_end, clause_start, clause_end) >= iou_threshold:
        return True

    covered = _span_covered(span_start, span_end, clause_start, clause_end)
    if covered < containment:
        return False

    span_fraction = (span_end - span_start) / clause_length
    return span_fraction >= MIN_SPAN_FRACTION_OF_CLAUSE


def convert(
    raw_path: Path, mapping: dict[str, str], iou_threshold: float, containment: float
) -> list[ClauseExample]:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))

    examples: list[ClauseExample] = []
    unmapped: Counter[str] = Counter()

    for entry in payload["data"]:
        title = entry.get("title") or "unknown"

        for paragraph in entry["paragraphs"]:
            context: str = paragraph["context"]

            # Collect spans as (class_key, start, end).
            spans: list[tuple[str, int, int]] = []
            for qa in paragraph.get("qas", []):
                category = _normalise_category(qa.get("question", ""))
                class_key = mapping.get(category)
                if class_key is None:
                    unmapped[category] += 1
                    continue
                for answer in qa.get("answers", []):
                    start = int(answer["answer_start"])
                    spans.append((class_key, start, start + len(answer["text"])))

            # Step 2: the production segmenter, on the real contract text.
            segments = segment(extract_plain_text(context))

            for seg in segments:
                if seg.needs_manual_review:
                    # Segmenter already said it could not cleanly isolate this;
                    # training on it would teach noise.
                    continue
                if not (MIN_CHARS <= len(seg.text) <= MAX_CHARS):
                    continue
                if _is_boilerplate(seg.text):
                    continue

                cleaned = strip_furniture(seg.text)
                if not (MIN_CHARS <= len(cleaned) <= MAX_CHARS):
                    continue
                if is_heading_only(cleaned):
                    continue

                clause_length = max(seg.char_end - seg.char_start, 1)

                labels = sorted(
                    {
                        class_key
                        for class_key, span_start, span_end in spans
                        if _assigns_label(
                            span_start,
                            span_end,
                            seg.char_start,
                            seg.char_end,
                            clause_length,
                            iou_threshold,
                            containment,
                        )
                    }
                )

                examples.append(
                    ClauseExample(
                        contract=title,
                        ordinal=seg.ordinal,
                        text=cleaned,
                        labels=labels,
                        segmentation_method=seg.method.value,
                    )
                )

    if unmapped:
        logger.warning(
            "%d CUAD categories were not in the mapping and were skipped: %s",
            len(unmapped),
            ", ".join(sorted(unmapped)[:8]),
        )

    return examples


# --------------------------------------------------------------------------
# Splitting
# --------------------------------------------------------------------------
def split_by_contract(
    examples: list[ClauseExample], seed: int
) -> dict[str, list[ClauseExample]]:
    """Split on contracts, not clauses.

    Clauses within one contract share drafting style, defined terms and party
    names. A clause-level split leaks all of that across the boundary and
    inflates every number.
    """
    contracts = sorted({e.contract for e in examples})
    random.Random(seed).shuffle(contracts)

    n = len(contracts)
    train_cut, val_cut = int(n * 0.70), int(n * 0.85)
    assignment = {
        c: ("train" if i < train_cut else "validation" if i < val_cut else "test")
        for i, c in enumerate(contracts)
    }

    splits: dict[str, list[ClauseExample]] = {"train": [], "validation": [], "test": []}
    for example in examples:
        splits[assignment[example.contract]].append(example)
    return splits


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
def report(splits: dict[str, list[ClauseExample]]) -> None:
    logger.info("--- dataset ---")
    for name, rows in splits.items():
        contracts = len({r.contract for r in rows})
        labelled = sum(1 for r in rows if r.labels)
        logger.info(
            "%-10s %5d clauses from %3d contracts (%d labelled, %d negative)",
            name,
            len(rows),
            contracts,
            labelled,
            len(rows) - labelled,
        )

    logger.info("--- per-class support (train) ---")
    tally: Counter[str] = Counter()
    for row in splits["train"]:
        tally.update(row.labels)

    for key in LABEL_KEYS:
        count = tally.get(key, 0)
        flag = "  <-- NO SUPPORT, depends on the Indian corpus" if count == 0 else ""
        logger.info("%-28s %5d%s", key, count, flag)


def write_audit_sample(examples: list[ClauseExample], out: Path, n: int, seed: int) -> None:
    """Write clauses for hand-checking. Do this before training.

    Stratified rather than uniform: only about one clause in six carries a
    label, so a uniform sample is mostly negatives and barely exercises the
    thing being audited, which is whether the *labels* are right. Two thirds of
    the sample is drawn from labelled clauses, one third from negatives (which
    still need checking — a mislabelled negative is a missed positive).
    """
    rng = random.Random(seed)
    labelled = [e for e in examples if e.labels]
    negatives = [e for e in examples if not e.labels]

    want_labelled = min(len(labelled), (n * 2) // 3)
    want_negative = min(len(negatives), n - want_labelled)

    sample = rng.sample(labelled, want_labelled) + rng.sample(negatives, want_negative)
    rng.shuffle(sample)
    lines = [
        "CUAD -> clause mapping audit sample",
        "",
        "Check each clause against its labels. If labels are wrong or missing,",
        "adjust --iou / --containment and regenerate. Do not train until this",
        "sample looks right: a bad mapping is invisible in the loss curve.",
        "=" * 78,
        "",
    ]
    for i, example in enumerate(sample, 1):
        lines += [
            f"[{i}] contract={example.contract} ordinal={example.ordinal} "
            f"method={example.segmentation_method}",
            f"labels: {', '.join(example.labels) or '(negative)'}",
            "-" * 78,
            example.text[:1500],
            "",
            "=" * 78,
            "",
        ]
    out.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote %d clauses for audit to %s", len(sample), out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--iou",
        type=float,
        default=0.5,
        help="Minimum span/clause IoU to assign a label (PLAN.md 4.1 step 3).",
    )
    parser.add_argument(
        "--containment",
        type=float,
        default=0.9,
        help="Alternatively, minimum fraction of the span inside the clause.",
    )
    parser.add_argument("--seed", type=int, default=20241042)
    parser.add_argument(
        "--audit", type=int, default=50, help="How many clauses to write for hand-checking."
    )
    args = parser.parse_args()

    if not args.raw.is_file():
        raise SystemExit(
            f"CUAD not found at {args.raw}.\n"
            "Download CUADv1.json from https://github.com/TheAtticusProject/cuad "
            "and place it there."
        )

    args.out.mkdir(parents=True, exist_ok=True)

    mapping = load_mapping()
    examples = convert(args.raw, mapping, args.iou, args.containment)
    if not examples:
        raise SystemExit("conversion produced no clauses; check the input file")

    splits = split_by_contract(examples, args.seed)
    report(splits)

    for name, rows in splits.items():
        path = args.out / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")
        logger.info("Wrote %s", path)

    if args.audit:
        write_audit_sample(
            examples, args.out / "audit_sample.txt", args.audit, args.seed
        )

    (args.out / "conversion_metadata.json").write_text(
        json.dumps(
            {
                "iou_threshold": args.iou,
                "containment_threshold": args.containment,
                "seed": args.seed,
                "split_strategy": "by contract",
                "labels": list(LABEL_KEYS),
                "counts": {k: len(v) for k, v in splits.items()},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    logger.info("")
    logger.info("NEXT: read ml/data/processed/audit_sample.txt and check 50 clauses")
    logger.info("by hand before running train.py. This is a gate, not a formality.")


if __name__ == "__main__":
    main()
