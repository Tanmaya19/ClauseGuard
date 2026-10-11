# Requirements traceability matrix

Maps every requirement in SRS v1.0 to the code that implements it and the test
that proves it.

**Status key:** ✅ implemented and tested · ⚠️ implemented, verification
depends on the trained model · ⬜ not implemented

Paths are relative to `backend/` unless stated otherwise.

---

## 4.1 Contract Upload and Parsing

| Req | Requirement | Implementation | Test | Status |
|---|---|---|---|---|
| REQ-1.1 | Accept PDF and DOCX only | `services/extraction/__init__.py::detect_format` — magic bytes, not the extension | `test_extraction.py::test_detects_*`, `test_rejects_legacy_doc_*`, `test_api.py::test_legacy_doc_is_rejected_synchronously` | ✅ |
| REQ-1.2 | Reject files over 10 MB (TBD-1) | `api/v1/contracts.py::upload`, `core/config.py::max_upload_bytes` | `test_api.py::test_oversize_upload_is_rejected_with_the_limit_in_the_message` | ✅ |
| REQ-1.3 | Extract text preserving clause boundaries | `services/extraction/pdf.py` (line-level spans + font-based headings), `docx.py` (styles + tables) | `test_extraction.py::test_extracts_full_text`, `test_block_offsets_point_at_the_assembled_text`, `test_identifies_headings` | ✅ |
| REQ-1.4 | Notify user when no text is extractable | `NoExtractableTextError`, `Contract.error_code`, `_ERROR_MESSAGES` | `test_extraction.py::test_image_only_pdf_is_reported_as_unreadable`, `test_api.py::test_scanned_pdf_fails_with_plain_language` | ✅ |
| REQ-1.5 | Store original file and extracted text per account | `services/storage.py`, `Contract.storage_path`, `Contract.raw_text` | `test_api.py::test_reanalysis_reuses_the_stored_file` | ✅ |

## 4.2 Clause Segmentation

| Req | Requirement | Implementation | Test | Status |
|---|---|---|---|---|
| REQ-2.1 | Segment by heuristics + sentence-boundary model | `services/segmentation/segmenter.py` — numbering → heading → paragraph cascade; pysbd for long runs | `test_segmentation.py::test_numbered_contract_uses_the_numbering_strategy`, `test_long_unstructured_text_is_split_at_sentence_boundaries` | ✅ |
| REQ-2.2 | Unique id, original order retained | `Clause.id` (UUID), `Clause.ordinal`, `uq_clauses_contract_ordinal` | `test_segmentation.py::test_ordinals_are_sequential_and_preserve_document_order`, `test_migrations.py` | ✅ |
| REQ-2.3 | Fall back to paragraph segmentation | `_segment_by_paragraph` | `test_segmentation.py::test_paragraph_fallback_when_there_is_no_structure` | ✅ |
| REQ-2.4 | Flag ambiguous clauses for manual review | `Clause.needs_manual_review`, `_review_flag` | `test_segmentation.py::test_overlong_numbered_clause_is_flagged_not_silently_split`, `test_fragment_is_flagged_for_review` | ✅ |

## 4.3 Clause-Type Classification

| Req | Requirement | Implementation | Test | Status |
|---|---|---|---|---|
| REQ-3.1 | 15–20 clause types from CUAD taxonomy | `services/classification/labels.py` — 20 classes; `ml/configs/label_mapping.yaml` maps all 41 CUAD categories | `test_api.py::test_clause_types_endpoint_returns_the_taxonomy`; import-time assertion in `labels.py` | ✅ |
| REQ-3.2 | Multi-label classification | `clause_predictions`, one row per (clause, label) | `test_migrations.py`, `test_api.py::test_predictions_carry_confidence_and_display_names` | ✅ |
| REQ-3.3 | Report confidence per predicted type | `ClausePrediction.confidence` + `[0,1]` check constraint | `test_api.py::test_predictions_carry_confidence_and_display_names` | ✅ |
| REQ-3.4 | "Uncategorized" below threshold (TBD-2) | zero prediction rows; `min_confidence_threshold` floor plus per-class `thresholds.json` | `test_rubric.py::test_unclassified_clause_is_unassessable_not_safe` | ✅ |
| — | Accuracy of the trained model | `ml/scripts/train.py`, `evaluate.py` | **Trained and evaluated.** CUAD test macro-F1 0.566 over 13 supported classes; Indian set 0.302. Full tables in `ml/MODEL_CARD.md` | ✅ measured |
| — | Which classifier is served | `services/classification/model.py::get_classifier` | **Baseline retained**: trained model types 7/16 fixture clauses vs baseline 15/16. Reasoning in `ml/MODEL_CARD.md` | ✅ decided |

## 4.4 Risk Scoring

| Req | Requirement | Implementation | Test | Status |
|---|---|---|---|---|
| REQ-4.1 | Three risk levels | `RiskLevel` enum, `engine.py::_compose` | `test_rubric.py::test_high_severity_dominates_composition`, `test_clause_with_no_findings_is_safe` | ✅ |
| REQ-4.2 | Documented criteria, not a model score | `rubrics/v1.0.yaml` (21 clause rules + 4 contract rules), `RiskFinding.rule_id` | `test_rubric.py::test_every_rule_documents_a_criterion_and_an_explanation`, `test_rules_only_reference_known_detectors` | ✅ |
| REQ-4.3 | Plain-language explanation for every flag | `RiskFinding.explanation` (NOT NULL), rubric `explanation` field | `test_rubric.py::test_explanations_avoid_legal_jargon`, `test_api.py::test_report_contains_clauses_types_risks_and_explanations` | ✅ |
| REQ-4.4 | Rubric updatable without retraining | YAML loaded and validated at runtime; `rubric_versions`; `POST /contracts/{id}/reanalyse` | `test_rubric.py::test_rubric_loads_and_is_hashed`, `test_api.py::test_reanalysis_reuses_the_stored_file` | ✅ |

## 4.5 Report Generation and Export

| Req | Requirement | Implementation | Test | Status |
|---|---|---|---|---|
| REQ-5.1 | In-app clause-by-clause report | `api/v1/reports.py::get_report`, `frontend/src/pages/Report.tsx` | `test_api.py::test_report_contains_clauses_types_risks_and_explanations` | ✅ |
| REQ-5.2 | Colour-code clauses by risk level | `frontend/tailwind.config.js` palette, `RISK_META`; mirrored in `pdf_renderer.py::RISK_COLOURS` | verified in the running stack; palettes cross-referenced in comments | ✅ |
| REQ-5.3 | Export full report as PDF | `services/reporting/pdf_renderer.py` (reportlab — ADR 0002) | `test_api.py::test_pdf_export` | ✅ |
| REQ-5.4 | Overall contract summary at top | `Report.summary_json` via `pipeline.py::_summary`; summary tiles in `Report.tsx` | `test_api.py::test_report_summary_counts_match_the_clauses` | ✅ |

## 4.6 User Account and Contract History

| Req | Requirement | Implementation | Test | Status |
|---|---|---|---|---|
| REQ-6.1 | Secure account creation and login | `api/v1/auth.py`, `core/security.py` — bcrypt + JWT | `test_api.py::test_register_then_login`, `test_duplicate_registration_is_rejected`, `test_wrong_password_and_unknown_user_are_indistinguishable` | ✅ |
| REQ-6.2 | Contracts associated with the authenticated user | `Contract.user_id` FK with cascade; every query filters on it | `test_api.py::test_another_account_cannot_reach_a_contract`, `test_history_is_scoped_to_the_account` | ✅ |
| REQ-6.3 | History/dashboard with date and risk summary | `api/v1/contracts.py::history`, `dashboard`; `frontend/src/pages/Dashboard.tsx` | `test_api.py::test_history_lists_contracts_with_risk_summary`, `test_dashboard_aggregates` | ✅ |
| REQ-6.4 | Re-open and re-download past reports | `reports` table + `summary_json`; dashboard "Open" | `test_api.py::test_report_contains_*` after re-fetch, `test_reanalysis_reuses_the_stored_file` | ✅ |

## 5. Non-functional requirements

| Ref | Requirement | Implementation | Test | Status |
|---|---|---|---|---|
| §5.1 | ≤30 s processing (TBD-3) | `pipeline.py` stage design | `scripts/measure_latency.py` — **2.78 s worst case for 51 clauses with the trained DistilBERT** (2.627 s of it classification); 0.2 s with the baseline | ✅ verified |
| §5.1 | 5 concurrent analyses (TBD-4) | `pipeline.py::_slots`, a `BoundedSemaphore`; work queues rather than being dropped | `scripts/load_test.py` — **10 concurrent (2× capacity): 10/10 accepted, 10/10 completed, identical results, 8.46× speedup** | ✅ |
| §5.2 | Never assert certainty | confidence on every prediction; baseline capped at 0.80; `UNASSESSABLE` instead of a guess | `test_rubric.py::test_unclassified_clause_is_unassessable_not_safe` | ✅ |
| §5.2 | Persistent disclaimer | `schemas/contracts.py::DISCLAIMER` served by the API; `Disclaimer.tsx` sticky footer; PDF running footer on every page | `test_api.py::test_report_contains_*` asserts it is served | ✅ |
| §5.3 | TLS in transit | `frontend/nginx.tls.conf`, `docker-compose.tls.yml`, `scripts/generate_dev_certs.sh` | Verified against the running stack: **TLSv1.3 / AES-256-GCM**, HTTP→HTTPS 301, HSTS + CSP + X-Frame-Options + nosniff + Referrer-Policy | ✅ |
| §5.3 | Data restricted to the owning account | `api/deps.py::current_user` + `user_id` filter in every query; UUID keys (ADR 0001) | `test_api.py::test_another_account_cannot_reach_a_contract` (404, not 403) | ✅ |
| §5.3 | Hashed passwords, token sessions | `core/security.py` — bcrypt, 72-byte limit enforced; HS256 JWT with `exp`/`iss` required | `test_api.py::test_password_beyond_bcrypt_limit_is_rejected`, `test_protected_routes_require_a_valid_token` | ✅ |
| §5.3 | Account-level deletion of contracts | `DELETE /contracts/{id}` — DB cascade + file removal | `test_api.py::test_deletion_removes_the_contract_and_its_report` | ✅ |
| §5.4 | Explainability | `RiskFinding.explanation` non-nullable; generated `docs/RUBRIC.md` | `test_rubric.py::test_every_rule_documents_a_criterion_and_an_explanation` | ✅ |
| §5.4 | Usability for non-lawyers | plain-language rubric copy; `docs/USER_GUIDE.md`; risk labels worded as actions ("Needs attention") not jargon | `test_rubric.py::test_explanations_avoid_legal_jargon` | ✅ |
| §5.4 | Graceful degradation | `RiskLevel.UNASSESSABLE`; per-rule exception isolation; health returns 503 not 500; classifier falls back to baseline | `test_rubric.py::test_a_failing_detector_does_not_fail_the_report`, `test_health.py::test_health_degrades_rather_than_crashes_without_a_database` | ✅ |
| §5.4 | Models swappable/retrainable | `Classifier` protocol + `get_classifier()` (ADR 0003); `model_version` on every prediction | `test_rubric.py` runs against the protocol | ✅ |
| §5.4 | Containerised | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` (db + api + web) | CI `docker` job | ✅ |
| §5.5 | Rubric changes version-tracked | `rubric_versions.yaml_sha256`; version denormalised onto findings, risk and reports; hash mismatch logged as an error | `test_rubric.py::test_rubric_loads_and_is_hashed`, `test_migrations.py` | ✅ |
| §5.5 | Not represented as legal advice | disclaimer in API, UI footer, PDF footer, user guide, auth screen | as above | ✅ |

## 6. Other requirements

| Ref | Requirement | Implementation | Test | Status |
|---|---|---|---|---|
| Legal/domain | Categories reviewed for Indian relevance | 5 Indian-specific classes (`termination_cause_cure`, `late_payment_interest_gst`, `confidentiality`, `dispute_arbitration`, `force_majeure`); 4 rules cite Indian statute | `test_rubric.py::test_msmed_rule_cites_the_statute`; statute table in `docs/RUBRIC.md` | ✅ |
| Data | Dataset provenance documented | `ml/MODEL_CARD.md`, `ml/configs/label_mapping.yaml` (every CUAD category mapped or explicitly dropped with a reason) | `prepare_cuad.py` fails on an unknown class | ✅ |
| i18n | Out of scope for V1.0 | stated in the user guide and the SRS addendum | — | ✅ (scoped out) |
| Reuse | Decoupled classifier and risk layers | `services/classification/` has no import of `services/risk/` and vice versa; the rubric consumes only label strings | `test_rubric.py` exercises the rubric with hand-made label sets, no model involved | ✅ |

---

## Deliberate gaps

Recorded here rather than left implicit:

1. **The trained classifier underperforms the keyword baseline on the target
   domain, and is therefore not served.** Training completed and is fully
   measured (CUAD 0.566, Indian 0.302), but seven of twenty classes had zero
   CUAD support and cannot be predicted at all. The baseline types 15/16 fixture
   clauses against the trained model's 7/16. Remediation order is in
   `ml/MODEL_CARD.md`; the highest-value step is training on the Indian corpus
   in addition to CUAD.
2. **The Indian evaluation set is synthetic.** 180 clauses, meeting the TBD-5
   count target, with all 20 classes covered and weighted toward the six CUAD
   cannot teach. But the clauses were *written* for this project rather than
   harvested from real contracts, which makes them more canonical than real
   drafting — so metrics on this set are an **optimistic** estimate of in-domain
   performance. See `ml/eval/README.md`.
3. **Asymmetry detection does not know which party the user is**, so it flags
   one-sidedness in either direction. Capturing the user's role at upload would
   let it narrow to clauses that disadvantage them.
4. **No production TLS certificate is committed**, and none should be. The TLS
   configuration is verified with a self-signed certificate; a real deployment
   needs a CA-issued one, documented in `docs/DEPLOYMENT.md`.
