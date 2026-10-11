# Model card — ClauseGuard clause-type classifier

> **Status: trained, evaluated, and NOT recommended for serving yet.**
>
> A real checkpoint exists (`distilbert-cuad-v1-cpu-2ep`). It scores
> **macro-F1 0.566 over the 13 CUAD classes that have test support** and
> **0.302 on the Indian evaluation set**. But measured against the actual
> product it is **worse than the keyword baseline it was meant to replace** —
> see "Why this model is not the default" below. The baseline remains the
> served classifier. SRS §6 (Data requirement) requires dataset provenance and label mapping
> to be documented for reproducibility, so this file is filled in *as* the
> model is built rather than reconstructed afterwards.
>
> **What is already settled:**
> - The 20-class taxonomy (`backend/app/services/classification/labels.py`).
> - The full CUAD-category mapping, with every dropped category and its reason
>   (`ml/configs/label_mapping.yaml`).
> - The conversion procedure, verified end to end against a synthetic
>   CUAD-shaped dataset: 24/24 clauses received the expected label, and the
>   split was by contract.
>
> **What the app serves meanwhile:** a keyword baseline whose `model_version`
> is `baseline-keyword-v1`, recorded on every prediction, every report and the
> health endpoint, with confidence capped at 0.80. See
> `docs/ADRs/0003-classifier-interface-and-baseline.md`. **No figure produced
> by the baseline is a reportable result.**
>
> Every `TO BE FILLED` marker below needs the training run.

## Intended use

Triage aid that classifies clauses in English-language Indian MSME commercial
contracts (vendor, supply, NDA, service) by legal type, so that a rule-based
rubric can flag the ones worth a paid legal opinion.

**Not** a source of legal advice, and not a substitute for review by a licensed
professional (SRS §2.5, §5.5).

## Out-of-scope use

- Consumer Terms-of-Service unfairness detection — the CLAUDETTE/UNFAIR-ToS
  task this project is only *inspired by*, not a reimplementation of.
- Non-English contracts (SRS §6: out of scope for V1.0).
- Scanned or image-only documents (TBD-7: out of scope).
- Jurisdictions other than India, where the rubric's statutory references do
  not apply.

## Architecture

| | |
|---|---|
| Served model | DistilBERT (`distilbert-base-uncased`), fine-tuned |
| Comparison model | Legal-BERT (`nlpaueb/legal-bert-base-uncased`), identical data and splits |
| Task | Multi-label sequence classification, 20 sigmoid heads |
| Loss | `BCEWithLogitsLoss`, class-weighted |
| Max sequence length | 256 tokens, sliding window with max-pool across windows |
| Inference target | CPU (SRS §2.4) |
| Model version string | `distilbert-cuad-v1-cpu-2ep` — recorded in `clause_predictions.model_version` |
| Trained on | CPU, 2 epochs, 1,602 steps, 6,740 s (1 h 52 m) |
| Final training loss | 0.210 |

DistilBERT is served rather than Legal-BERT because SRS §2.4 mandates CPU
inference and the TBD-3 latency budget is 30 s for 50 clauses. The Legal-BERT
run exists so that choice is evidenced by measurement rather than asserted.

## Training data

### Primary: CUAD
Contract Understanding Atticus Dataset — 510 commercial contracts, 41
annotated clause categories (Reference 1 and 6 in SRS §1.5).

**CUAD is a span-extraction dataset, not a classification dataset.** It is
distributed in SQuAD format, where each category is a question and the answer
is a highlighted span. Conversion to multi-label clause classification:

1. Parse annotated spans per contract; each span carries its CUAD category.
2. Segment each contract using **the production segmenter**
   (`backend/app/services/segmentation/`). Using a different segmenter here
   than at inference time would create train/serve skew.
3. Assign label *L* to a clause when an *L*-span overlaps it with
   IoU ≥ 0.5, or ≥0.9 of the span contained in the clause **and** the
   span being ≥15% of the clause length (the second condition was added
   after the audit — see the audit record).
4. Clauses with no overlapping span become negatives, after discarding
   boilerplate (signature blocks, schedules, tables of contents) which would
   otherwise dominate the negative class.
5. Split **by contract**, never by clause — clauses within one contract are
   highly correlated and clause-level splitting leaks.

| | |
|---|---|
| Contracts | 510 |
| Clause instances after conversion | **20,062** |
| Train / validation / test split (by contract) | 343 / 73 / 74 contracts → 12,817 / 2,368 / 4,877 clauses |
| IoU threshold used | 0.5 IoU, **or** 0.9 span containment with the span ≥15% of the clause |
| Manual audit of mapped clauses | **Done, 7 Oct 2026** — three rounds; see "Audit record" below |
| Measured label noise on positives after corrections | **~23%** (6 of 26 inspected labels wrong) |
| Conversion logic verified on synthetic data | Yes — 24/24 expected labels, split by contract, 6 synthetic contracts |
| Default IoU / containment thresholds | 0.5 IoU, or 0.9 of the span contained in the clause |

Step 5's audit is a gate, not a formality: if the span-to-clause mapping is
noisy, every downstream metric is meaningless. It happens **before** the first
training run.

### Audit record

The audit was run three times, each round finding defects and each correction
measurably reducing label noise. This is the project's clearest demonstration
of why the gate exists: none of these defects would have been visible in the
loss curve.

| Round | Label noise on positives | Defects found and corrected |
|---|---|---|
| 1 | ~40% | **70 of 510 contracts produced no clauses at all** — the segmenter's cascade accepted a strategy on group *count* alone, so contracts numbering only a few long recitals yielded 4,000-character blobs that were all flagged over-long and dropped. Fixed by rejecting a strategy whose output is mostly over-long (`MAX_OVERLONG_FRACTION`). Recovered 50 contracts and 29% more labelled examples. Also: SEC filing furniture ("[ * ] = Certain confidential information … omitted …") appearing *inside* clause bodies; heading-only fragments passing the length floor; the audit sample itself being ~85% negatives and so barely testing labels at all. |
| 2 | ~35% | **Tables of contents were being labelled.** A contents page ("20.1 Confidential Terms 41 20.2 Governing Law 41 …") is mostly alphabetic, so it passed the boilerplate ratio check, and because it lists every heading in the document, spans landed on it. One was found labelled `parties_definitions`. Fixed with a contents detector; `parties_definitions` support fell from 301 to 22, which is the measure of how much noise this contributed. Also: a short span inside a large fused block was labelling the whole block, so containment-based assignment now additionally requires the span to be ≥15% of the clause, and `MAX_CHARS` was tightened from 4000 to 2500 to match the segmenter's own ceiling. |
| 3 | **~23%** | **Four CUAD categories were mapped to classes that do not fit them.** `Non-Disparagement` → `exclusivity_noncompete` (a conduct/morals clause is not a competition restriction); `Covenant Not To Sue` and `Third Party Beneficiary` → `audit_compliance` (neither is an audit provision — the audit found a trademark-ownership clause labelled this way); `Post-Termination Services` → `notices_misc` (the audit found a termination clause labelled this way). All four moved to `dropped`, so they become negatives. A forced mapping is worse than no mapping: it teaches a wrong association rather than nothing. |

**Residual ~23% noise, and what causes it.** The remaining errors are
annotated spans landing on text adjacent to the clause they describe — a
`Governing Law` span falling in a block of general boilerplate, an `Audit
Rights` span falling in an equipment-custody clause. Reducing this further
needs per-category span handling rather than one global rule, which is beyond
the scope of this version.

**Consequence for the results.** 23% label noise on positives is a ceiling on
achievable precision: a model that learned the task perfectly would still be
scored against partly-wrong labels. Per-class precision should be read with
that in mind, and the figure should be quoted alongside any F1 reported from
CUAD.

### Supplementary: Indian domain-adaptation corpus

CUAD is US-centric, long-form and M&A-focused (SRS §2.5), while the target is
short-form Indian vendor and supply agreements. Sources, per SRS §2.7 and
TBD-5:

| Source | Licence / basis | Documents | Clauses labelled |
|---|---|---|---|
| GeM General Terms and Conditions | Public government document | TO BE FILLED | TO BE FILLED |
| Model forms, Indian Contract Act 1872 | Public | TO BE FILLED | TO BE FILLED |
| MSMED Act 2006 / Samadhaan material | Public | TO BE FILLED | TO BE FILLED |
| BSE / NSE disclosed material contracts | Public filings | TO BE FILLED | TO BE FILLED |
| Public law-firm / industry template repositories | Per-source, recorded individually | TO BE FILLED | TO BE FILLED |
| Synthetic agreements, manually reviewed | Generated for this project | TO BE FILLED | TO BE FILLED |

| **Synthetic Indian clauses, written for this project** | Authored here; no third-party licence | n/a | **180** (170 positive, 10 negative; all 20 classes) |

No paywalled or licence-restricted material is scraped. Target of 150–200
clauses is met **by the synthetic set alone**, which is a weaker basis than
real harvested clauses: see `ml/eval/README.md` for why metrics on it should be
read as optimistic. Substituting ~50 real clauses from the sources above is the
highest-value remaining improvement to the evaluation.

## Label taxonomy

20 classes, collapsed from CUAD's 41 and extended for Indian norms (SRS §6).
Five classes marked **thin** are poorly represented in CUAD and depend on the
Indian corpus.

| # | Key | Display name | Source | Support |
|---|---|---|---|---|
| 1 | `parties_definitions` | Parties & Definitions | Parties, Document Name | **22** |
| 2 | `term_effective_date` | Term & Effective Date | Agreement/Effective/Expiration Date | **172** |
| 3 | `renewal_auto_renewal` | Renewal & Auto-Renewal | Renewal Term, Notice Period To Terminate Renewal | **84** |
| 4 | `termination_convenience` | Termination for Convenience | Termination For Convenience | **65** |
| 5 | `termination_cause_cure` | Termination for Cause & Cure | Indian corpus — **thin** | **0** — no CUAD support |
| 6 | `payment_terms` | Payment Terms & Pricing | Price Restrictions, Minimum Commitment, Revenue/Profit Sharing | **231** |
| 7 | `late_payment_interest_gst` | Late Payment, Interest & GST | Indian addition — **thin** | **0** — no CUAD support |
| 8 | `indemnity` | Indemnity | Indian corpus + insurance-adjacent | **0** — no CUAD support |
| 9 | `limitation_of_liability` | Limitation of Liability | Cap On Liability, Uncapped Liability | **230** |
| 10 | `warranties` | Warranties & Representations | Warranty Duration | **43** |
| 11 | `confidentiality` | Confidentiality | Indian corpus + NDAs — **thin** | **0** — no CUAD support |
| 12 | `ip_ownership_licence` | IP Ownership & Licence | IP Ownership Assignment, License Grant, Joint IP Ownership | **371** |
| 13 | `exclusivity_noncompete` | Exclusivity & Non-Compete | Exclusivity, Non-Compete, No-Solicit | **225** |
| 14 | `assignment_control` | Assignment & Change of Control | Anti-Assignment, Change Of Control | **292** |
| 15 | `governing_law` | Governing Law & Jurisdiction | Governing Law | **151** |
| 16 | `dispute_arbitration` | Dispute Resolution & Arbitration | Indian addition — **thin** | **0** — no CUAD support |
| 17 | `force_majeure` | Force Majeure | Indian corpus — **thin** | **0** — no CUAD support |
| 18 | `audit_compliance` | Audit, Inspection & Compliance | Audit Rights | **130** |
| 19 | `insurance` | Insurance | Insurance | **101** |
| 20 | `notices_misc` | Notices & Miscellaneous | Notice | **0** — no CUAD support |

The full CUAD-category → class mapping, including every category that was
dropped and why, goes in `ml/configs/label_mapping.yaml` (Phase 3).

## Thresholds

Per TBD-2: a global floor of **0.45**, plus per-class thresholds fitted on the
validation split for best per-class F1. A clause with no label above its class
threshold is reported as `Uncategorized` (REQ-3.4) rather than being assigned a
guess.

| Class | Fitted threshold |
|---|---|
| `exclusivity_noncompete` | 0.9 |
| `assignment_control` | 0.9 |
| `governing_law` | 0.9 |
| `audit_compliance` | 0.9 |
| `insurance` | 0.9 |
| `term_effective_date` | 0.85 |
| `renewal_auto_renewal` | 0.85 |
| `limitation_of_liability` | 0.85 |
| `warranties` | 0.85 |
| `ip_ownership_licence` | 0.85 |
| `termination_convenience` | 0.75 |
| `payment_terms` | 0.75 |
| `termination_cause_cure` | 0.5 |
| `late_payment_interest_gst` | 0.5 |
| `indemnity` | 0.5 |
| `confidentiality` | 0.5 |
| `dispute_arbitration` | 0.5 |
| `force_majeure` | 0.5 |
| `notices_misc` | 0.5 |
| `parties_definitions` | 0.05 |

The seven classes sitting at the untuned default of 0.50, plus
`parties_definitions` at 0.05, are the tell: those are classes with no
validation examples to fit against, so no threshold could be chosen.

## Evaluation

Metrics are **macro-F1 and per-class precision / recall / F1**. Accuracy is not
reported: on a 20-label imbalanced multi-label task it is dominated by true
negatives and would overstate performance.

### CUAD held-out test set

| Model | Macro-F1 (all 20) | Macro-F1 (13 supported) | Micro-F1 | n |
|---|---|---|---|---|
| DistilBERT, 2-epoch CPU | 0.3678 | **0.5658** | 0.5639 | 4,877 |
| Legal-BERT | not run | — | — | — |

**Read the second column, not the first.** Seven of the twenty classes have
**zero examples in the CUAD test split**, so each scores F1 0.000 and is still
counted in the 20-class macro average, dragging it from 0.566 to 0.368. The
0.566 figure over the 13 classes that actually appear is the honest one, and it
agrees closely with micro-F1 0.564.

Per-class, CUAD test:

| Class | P | R | F1 | Support |
|---|---|---|---|---|
| `parties_definitions` | 0.000 | 0.000 | 0.000 | 10 |
| `term_effective_date` | 0.600 | 0.706 | 0.649 | 51 |
| `renewal_auto_renewal` | 0.773 | 0.708 | 0.739 | 24 |
| `termination_convenience` | 0.235 | 0.191 | 0.210 | 21 |
| `termination_cause_cure` | 0.000 | 0.000 | 0.000 | 0 |
| `payment_terms` | 0.387 | 0.547 | 0.453 | 75 |
| `late_payment_interest_gst` | 0.000 | 0.000 | 0.000 | 0 |
| `indemnity` | 0.000 | 0.000 | 0.000 | 0 |
| `limitation_of_liability` | 0.776 | 0.722 | 0.748 | 72 |
| `warranties` | 0.667 | 0.133 | 0.222 | 15 |
| `confidentiality` | 0.000 | 0.000 | 0.000 | 0 |
| `ip_ownership_licence` | 0.623 | 0.681 | 0.651 | 141 |
| `exclusivity_noncompete` | 0.776 | 0.506 | 0.612 | 89 |
| `assignment_control` | 0.741 | 0.588 | 0.656 | 68 |
| `governing_law` | 0.851 | 0.889 | 0.870 | 45 |
| `dispute_arbitration` | 0.000 | 0.000 | 0.000 | 0 |
| `force_majeure` | 0.000 | 0.000 | 0.000 | 0 |
| `audit_compliance` | 0.698 | 0.787 | 0.740 | 47 |
| `insurance` | 0.744 | 0.879 | 0.806 | 33 |
| `notices_misc` | 0.000 | 0.000 | 0.000 | 0 |

Mean precision 0.605 against mean recall 0.564 over supported classes — roughly
balanced. Best: `governing_law` 0.870, `insurance` 0.806,
`limitation_of_liability` 0.748. Worst with support: `termination_convenience`
0.210 and `warranties` 0.222 (recall 0.133 — it almost never fires).

### Indian evaluation set (`ml/eval/indian_eval_set.jsonl`)

| Model | Macro-F1 | Micro-F1 | n |
|---|---|---|---|
| DistilBERT, 2-epoch CPU | 0.3022 | 0.2718 | 180 |

All 20 classes have support here, so no averaging artefact applies.

| Class | P | R | F1 | Support |
|---|---|---|---|---|
| `parties_definitions` | 0.000 | 0.000 | 0.000 | 11 |
| `term_effective_date` | 0.429 | 0.429 | 0.429 | 7 |
| `renewal_auto_renewal` | 1.000 | 0.429 | 0.600 | 7 |
| `termination_convenience` | 0.500 | 0.125 | 0.200 | 8 |
| `termination_cause_cure` | 0.000 | 0.000 | 0.000 | 14 |
| `payment_terms` | 1.000 | 0.069 | 0.129 | 29 |
| `late_payment_interest_gst` | 0.000 | 0.000 | 0.000 | 14 |
| `indemnity` | 0.000 | 0.000 | 0.000 | 14 |
| `limitation_of_liability` | 1.000 | 0.583 | 0.737 | 12 |
| `warranties` | 0.000 | 0.000 | 0.000 | 12 |
| `confidentiality` | 0.000 | 0.000 | 0.000 | 13 |
| `ip_ownership_licence` | 1.000 | 0.400 | 0.571 | 10 |
| `exclusivity_noncompete` | 0.750 | 0.429 | 0.545 | 7 |
| `assignment_control` | 0.600 | 0.429 | 0.500 | 7 |
| `governing_law` | 0.800 | 0.571 | 0.667 | 7 |
| `dispute_arbitration` | 0.000 | 0.000 | 0.000 | 12 |
| `force_majeure` | 0.000 | 0.000 | 0.000 | 10 |
| `audit_compliance` | 1.000 | 0.500 | 0.667 | 8 |
| `insurance` | 1.000 | 1.000 | 1.000 | 5 |
| `notices_misc` | 0.000 | 0.000 | 0.000 | 11 |

**The shape of this table matters more than its headline.** Mean precision
0.454 against mean recall **0.248**: the model is severely conservative on
Indian text. Several classes reach precision 1.000 — when it does fire it is
usually right — but `payment_terms` has recall 0.069, meaning it misses 27 of
29 payment clauses.

And the six classes CUAD cannot teach score **exactly 0.000 despite having
10–14 examples each**. That is the predicted finding, confirmed: a model cannot
predict a class it has never seen.

### The domain gap

| Comparison | CUAD test | Indian set | Gap |
|---|---|---|---|
| Macro-F1, all 20 classes | 0.3678 | 0.3022 | +0.0656 |
| Macro-F1, like-for-like (supported classes) | 0.5658 | 0.3022 | **+0.2636** |
| Micro-F1 | 0.5639 | 0.2718 | **+0.2921** |

The first row understates the gap badly, because the CUAD figure is itself
depressed by the seven unsupported classes. The like-for-like comparison —
**0.566 on US M&A contracts against 0.302 on Indian MSME contracts** — is the
one to quote. Performance roughly halves on the domain the product actually
serves.

**This gap is the central empirical result of the project.** CUAD measures US
M&A contracts; the product targets Indian MSME agreements. Reporting both, and
discussing the difference, is more honest and more useful than a single number
from the easier distribution.

### Latency

| Measurement | Target | Observed |
|---|---|---|
| Classifier alone, 50 clauses, 2 threads | — | median 5.17 s, max 5.22 s |
| **Full pipeline, 51 clauses** | **≤ 30 s (TBD-3)** | **median 2.64 s, max 2.78 s — WITHIN BUDGET** |

Stage breakdown of the full pipeline with the trained model: extraction 0.006 s,
segmentation <0.001 s, **classification 2.627 s**, risk scoring 0.002 s.
Classification went from 0.018 s with the keyword baseline to 2.627 s with
DistilBERT — a 146× increase that still leaves the 30 s budget with better than
10× headroom. SRS §5.1 is now verified by measurement rather than estimated.

## Why this model is not the default

The trained checkpoint exists, loads, and serves correctly. It is **not** the
served classifier, because measured against the product it is worse than the
keyword baseline it was built to replace.

Both classifiers were run over the same 16-clause Indian supply agreement
fixture, through the real pipeline:

| Classifier | Clauses typed | Risk findings raised | Clauses left unassessable | Spurious "missing clause" warnings |
|---|---|---|---|---|
| **Keyword baseline** | **15 / 16** | **18** | **1** | 1 |
| Trained DistilBERT | 7 / 16 | 9 | 9 | 3 |

The trained model types fewer than half the clauses, raises half the findings,
and triggers two false "this contract has no payment terms / no confidentiality
clause" warnings — because it failed to recognise clauses that are plainly
present.

### It is not a threshold problem

The obvious suspicion is that the CUAD-fitted thresholds (0.85–0.90 for most
classes) are simply too high for Indian phrasing. They are not the cause:

| Threshold applied | Clauses typed |
|---|---|
| CUAD-fitted (0.05–0.90) | 6 / 16 |
| Flat 0.45 | 7 / 16 |
| Flat 0.30 | 7 / 16 |
| Flat 0.20 | 7 / 16 |

Dropping the threshold to 0.20 recovers nothing. The model's output for those
clauses is near zero whatever the cut-off, which means it has no signal for
them at all rather than signal sitting just below a badly-placed line.

### The actual cause

Two compounding reasons, and the first is structural:

1. **Seven of the twenty classes had zero CUAD training support** —
   `termination_cause_cure`, `late_payment_interest_gst`, `indemnity`,
   `confidentiality`, `dispute_arbitration`, `force_majeure`, `notices_misc`.
   The model was never shown a single example of any of them, so it cannot
   predict them. No amount of tuning changes that. These are also, as the
   taxonomy notes from the outset, the **most MSME-relevant** categories.
2. **Domain shift on the classes it did learn.** `ip_ownership_licence` and
   `exclusivity_noncompete` had 371 and 225 training examples respectively, yet
   neither fired on the Indian-style clauses in the fixture. US M&A drafting and
   Indian vendor drafting differ enough in vocabulary and sentence construction
   to lose the match.

The keyword baseline has neither problem: its cues were written for all twenty
classes, in Indian contractual language, by hand.

### What would fix it

In rough order of value per unit of effort:

1. **Train on the Indian corpus as well as CUAD**, not CUAD alone. The 180
   synthetic clauses in `ml/eval/` are currently evaluation-only; a larger
   version split into train and test would give the seven orphaned classes
   actual support. This is the single highest-value next step.
2. **Serve a union of both classifiers** — the transformer for the 13 classes
   it knows, the keyword cues for the 7 it cannot. The `Classifier` protocol
   already makes this a drop-in addition rather than a rewrite.
3. **Harvest real Indian clauses** rather than synthetic ones, addressing the
   domain shift directly.
4. Train the 3-epoch GPU configuration, which would improve the 13 supported
   classes but cannot help the 7 unsupported ones.

### The honest reading of this result

A trained transformer scoring 0.566 macro-F1 is a legitimate outcome for a
model built on 1,935 labelled examples carrying ~23% label noise. The failure
is not in the training; it is in **expecting a US M&A dataset to teach an Indian
MSME task**. The project's own taxonomy predicted exactly which six classes
CUAD could not supply, and the measurement confirmed it precisely.

That prediction being borne out is a better result than a flattering F1 would
have been, and it is why the architecture keeps risk scoring independent of the
model: with the classifier underperforming, the rubric layer still works, and
the product still functions on the baseline.

## Known limitations

1. Classes 5, 7, 11, 16 and 17 are the most MSME-relevant and the least
   represented in CUAD. Expect the weakest per-class F1 here.
2. CUAD's domain (long US M&A contracts) differs from the deployment domain
   (short Indian vendor agreements) in length, vocabulary and drafting
   convention.
3. Multi-label output means a clause can receive contradictory types; the
   rubric layer must tolerate that rather than assume one type per clause.
4. The model classifies type only. It does **not** judge risk — that is the
   rubric engine's job (PLAN.md §5), which is why risk decisions remain
   explainable without interpreting model internals.
5. No calibration study has been done, so confidence values should be read as
   ordinal, not as probabilities.

## Reproducibility

| | |
|---|---|
| Random seed | TO BE FILLED |
| Hardware | TO BE FILLED (expected: Google Colab T4) |
| `transformers` version | TO BE FILLED |
| `torch` version | TO BE FILLED |
| Training command | `python ml/scripts/train.py --config ml/configs/distilbert.yaml` |
| Commit hash of training run | TO BE FILLED |
