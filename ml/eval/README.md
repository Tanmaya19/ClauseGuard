# Indian evaluation set

`indian_eval_set.jsonl` holds labelled clauses in the style of Indian MSME
vendor, service and non-disclosure agreements. It is reported **separately**
from CUAD test metrics, because CUAD measures US M&A contracts while the product
serves Indian commercial agreements, and the gap between the two is the honest
finding (PLAN.md 4.4).

Regenerate it from reviewable source with:

```bash
python ml/eval/build_eval_set.py
```

## Current state

| | |
|---|---|
| Clauses | **180** |
| Positive examples | 170 |
| Negative examples (no label) | 10 |
| Label assignments | 218 |
| Classes covered | 20 of 20 |
| TBD-5 target | 150–200 ✅ |

Per-class counts, weighted deliberately toward the six classes CUAD cannot
teach:

| Class | Count | | Class | Count |
|---|---|---|---|---|
| `payment_terms` | 29 | | `ip_ownership_licence` | 10 |
| `termination_cause_cure` ★ | 14 | | `force_majeure` ★ | 10 |
| `late_payment_interest_gst` ★ | 14 | | `audit_compliance` | 8 |
| `indemnity` ★ | 14 | | `termination_convenience` | 8 |
| `confidentiality` ★ | 13 | | `term_effective_date` | 7 |
| `dispute_arbitration` ★ | 12 | | `renewal_auto_renewal` | 7 |
| `limitation_of_liability` | 12 | | `exclusivity_noncompete` | 7 |
| `warranties` | 12 | | `assignment_control` | 7 |
| `parties_definitions` | 11 | | `governing_law` | 7 |
| `notices_misc` | 11 | | `insurance` | 5 |

★ = thin or absent in CUAD, and the most MSME-relevant.

## Provenance — read before reporting any metric

**These clauses are synthetic.** They were written for this project in the
style of Indian commercial agreements, covering the statutory hooks CUAD has no
coverage of: MSMED Act payment terms and interest, GST and TDS, the Arbitration
and Conciliation Act 1996, section 27 of the Indian Contract Act 1872, the
Contract Labour Act, the Employee's Compensation Act.

They are **not harvested from real contracts**, and that limitation cuts in a
specific direction worth stating plainly:

> Synthetic clauses written by a single author are **more canonical** than real
> drafting. They are more consistent in vocabulary and sentence structure, and
> they lack the idiosyncratic phrasing, typographical errors, inconsistent
> defined terms and odd clause orderings that real agreements contain.
>
> **Metrics on this set are therefore an optimistic estimate of in-domain
> performance, not a pessimistic one.** Report them as such.

A second, subtler caveat: the same author wrote these clauses and the rubric's
keyword cues. There is a real risk of unintentional lexical alignment between
the two, which would flatter the baseline classifier in particular. This matters
less for the trained transformer, which learns from CUAD rather than from the
cues, but it is a reason not to treat baseline numbers on this set as meaningful
at all.

## Strengthening it

Replace or supplement these with clauses from the TBD-5 sources, keeping the
`source` field accurate:

| Source | Basis |
|---|---|
| Government e-Marketplace (GeM) General Terms and Conditions | Public government document |
| Model forms under the Indian Contract Act, 1872 | Public |
| MSME Samadhaan / MSMED Act reference material | Public |
| Material contracts in BSE / NSE company disclosures | Public filings |
| Publicly available law-firm and industry-body templates | Per-source; record each |

Record each source and its licence basis in `ml/MODEL_CARD.md`. Do not scrape
paywalled or licence-restricted material.

Roughly 50 real clauses mixed in would materially improve the set's
credibility, because they would reintroduce exactly the drafting variation the
synthetic clauses lack.

## Format

One JSON object per line, no comments — `evaluate.py` parses every line:

```json
{"source": "synthetic-indian", "text": "The Buyer shall make payment ...", "labels": ["payment_terms", "late_payment_interest_gst"]}
```

| Field | Meaning |
|---|---|
| `source` | Where the clause came from, for the provenance table in `MODEL_CARD.md` |
| `text` | The clause, whitespace-normalised as the segmenter would produce it |
| `labels` | Zero or more keys from `backend/app/services/classification/labels.py` |

An empty `labels` list is a valid negative example, and the set needs them: a
model that labels everything would score well on positives alone.

## Labelling guidance

- Label what the clause **is**, not what risk it carries. Risk is the rubric's
  job, and mixing the two would couple the two layers the architecture
  deliberately keeps apart.
- Multi-label is expected and common — a clause can be both `payment_terms` and
  `late_payment_interest_gst`.
- `build_eval_set.py` validates every label key against the taxonomy and
  rejects duplicate clause text, so a typo fails the build rather than
  producing a class that can never be scored.
