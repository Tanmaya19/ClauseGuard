# Risk rubric

> **Generated file — do not edit.**
> Produced from `backend/app/services/risk/rubrics/v1.0.yaml` by
> `backend/scripts/generate_rubric_docs.py`. Edit the YAML and re-run it.

**Version 1.0** · SHA-256 `5b4292417aa815f7a83522a0d685eefbc90f21895b564b5cece49868b0228c0e`

Every risk flag ClauseGuard raises comes from one of the rules below.
There is no model score anywhere in risk assessment: a clause is flagged
because a named, documented criterion matched its text (REQ-4.2), and the
explanation shown to the user is the one recorded here (REQ-4.3).

The rubric is data, not code — it can be extended without retraining
anything (REQ-4.4). Each report records the rubric version that produced
it, so a historical report stays explainable after the rubric changes
(SRS 5.5).

## How a clause gets its risk level

| Outcome | When |
|---|---|
| **High-Risk** | At least one `high` severity rule fired |
| **Caution** | At least one `caution` rule fired, and no `high` rule |
| **Safe** | The clause was classified, and no rule fired |
| **Not assessed** | The clause type could not be identified, or the rule layer errored |

*Not assessed* is deliberate. Reporting an unjudged clause as safe would
be a false reassurance, which SRS 5.2 treats as an informational-safety
concern rather than a cosmetic one.

## Clause rules (21)

### High-Risk (8)

#### `auto_renew_without_notice_window`

**Applies to:** Renewal & Auto-Renewal

**Criterion:** Automatic renewal with no specified window in which a party may opt out.

**Detectors:** `notice_period_absent`, `present_any`

**Shown to the user:**

> This contract renews itself automatically, and it does not say how much notice you must give to stop that happening. You could be committed to another full term without intending to be. Ask for a clear opt-out window, and put a reminder in your calendar before it closes.

#### `broad_ip_assignment`

**Applies to:** IP Ownership & Licence

**Criterion:** Assignment of intellectual property extending beyond work produced under the contract, capturing pre-existing or unrelated IP.

**Detectors:** `absent_any`, `present_any`

**Shown to the user:**

> This clause hands over intellectual property very broadly, and it does not carve out what you already owned before this contract. Tools, templates or code you built earlier could end up belonging to the other side. Ask for your "pre-existing" or "background" IP to be excluded, and for the assignment to cover only what is made specifically for this work.

#### `exclusivity_without_commitment`

**Applies to:** Exclusivity & Non-Compete

**Criterion:** An exclusivity obligation not matched by any minimum volume, value or purchase commitment from the benefiting party.

**Detectors:** `absent_any`, `present_any`

**Shown to the user:**

> You are being asked to deal only with this party, but they are not promising you any minimum amount of business in return. You would be turning away other customers for no guaranteed benefit. Ask for a minimum order commitment alongside the exclusivity, or for the exclusivity to be dropped.

#### `one_sided_indemnity`

**Applies to:** Indemnity

**Criterion:** Indemnity obligations running in one direction only, with no reciprocal undertaking from the other party.

**Detectors:** `one_sided_obligation`

**Shown to the user:**

> Only one side has to cover the other's losses here, and it is not mutual. That means you may carry the cost of problems that were not your fault. Ask for the same protection in return — this is usually described as making the indemnity "mutual" or "reciprocal".

#### `termination_without_notice_period`

**Applies to:** Termination for Convenience

**Criterion:** Termination for convenience with no stated notice period.

**Detectors:** `notice_period_absent`

**Shown to the user:**

> This clause allows the contract to be ended without saying how much notice must be given. You could lose the work with no time to plan. Ask for a clear notice period — 30 to 90 days is common.

#### `uncapped_liability`

**Applies to:** Indemnity, Limitation of Liability

**Criterion:** Absence of any monetary ceiling on liability exposure in a clause that allocates liability.

**Detectors:** `absent_any`

**Shown to the user:**

> This clause makes you responsible for losses without setting any upper limit. If something goes wrong, what you owe could be far more than the contract is worth to you. It is normal and reasonable to ask for a cap — commonly the total fees paid over the previous twelve months.

#### `unilateral_price_variation`

**Applies to:** Payment Terms & Pricing

**Criterion:** A right for one party to change prices or charges without the other's agreement.

**Detectors:** `present_any`

**Shown to the user:**

> One side can change the prices in this contract on their own, without needing your agreement. Your costs or your margin could move without warning. Ask for price changes to need both parties' consent, or to be capped and limited to once a year.

#### `unilateral_termination_for_convenience`

**Applies to:** Termination for Convenience

**Criterion:** A right to terminate without cause granted to one party only.

**Detectors:** `one_sided_right`

**Shown to the user:**

> One side can walk away from this contract at any time, without giving a reason, and the same right is not given to the other. If that side is not you, your work or supply could stop with little warning. Ask for the right to be mutual, or for a minimum notice period.

### Caution (13)

#### `foreign_arbitration_seat`

**Applies to:** Dispute Resolution & Arbitration

**Criterion:** Arbitration seated outside India, which makes the process a foreign- seated arbitration with correspondingly higher cost.

**Detectors:** `foreign_jurisdiction`

**Shown to the user:**

> Arbitration under this clause would take place outside India. Travel, foreign lawyers and overseas arbitrator fees make that very costly for a smaller business. Ask for the seat of arbitration to be an Indian city — arbitration in India is governed by the Arbitration and Conciliation Act, 1996.

#### `foreign_governing_law`

**Applies to:** Governing Law & Jurisdiction

**Criterion:** Governing law or jurisdiction outside India, materially raising the cost of enforcement for an Indian business.

**Detectors:** `foreign_jurisdiction`

**Shown to the user:**

> Any dispute under this contract would be handled under another country's law, or in another country's courts. Pursuing or defending a claim abroad is far more expensive and slower than doing so in India — often enough to make a genuine claim not worth bringing. Ask for Indian law and an Indian city as the venue.

#### `indemnity_covers_indirect_losses`

**Applies to:** Indemnity, Limitation of Liability

**Criterion:** Indemnity extended to indirect, consequential or special damages, which are open-ended by nature.

**Detectors:** `present_any`

**Shown to the user:**

> This clause covers not just direct costs but knock-on losses such as lost profits or lost business. Those amounts are hard to predict and can be very large. Most balanced contracts exclude them for both sides.

#### `liquidated_damages_one_way`

**Applies to:** Payment Terms & Pricing, Termination for Cause & Cure, Warranties & Representations

**Criterion:** Pre-agreed penalties or liquidated damages payable by one party only.

**Detectors:** `one_sided_obligation`, `present_any`

**Shown to the user:**

> This clause sets a fixed penalty that only one side pays if things go wrong. If the other side causes a delay, there is no equivalent consequence for them. Ask for the penalty to work both ways, or for it to be capped as a percentage of the contract value.

#### `long_renewal_optout_window`

**Applies to:** Renewal & Auto-Renewal

**Criterion:** Opt-out notice window for auto-renewal exceeding 90 days, which in practice makes the renewal difficult to avoid.

**Detectors:** `notice_period_gt`, `present_any`

**Shown to the user:**

> To stop this contract renewing, you have to give notice a long way in advance — more than three months. It is easy to miss a deadline that far ahead. Note the date now, and consider asking for a shorter window.

#### `no_cure_period`

**Applies to:** Termination for Cause & Cure

**Criterion:** Termination for breach with no opportunity to remedy the breach before termination takes effect.

**Detectors:** `absent_any`

**Shown to the user:**

> This clause lets the contract be ended for a breach without giving you a chance to put the problem right first. A small or accidental slip could cost you the whole contract. Ask for a "cure period" — typically 15 to 30 days to fix the issue after being told about it.

#### `no_dispute_resolution_mechanism`

**Applies to:** Governing Law & Jurisdiction

**Criterion:** A governing-law clause with no accompanying dispute-resolution process.

**Detectors:** `absent_any`

**Shown to the user:**

> This clause says which law applies but not how a disagreement would actually be sorted out. Without an agreed process, your only route is court, which is slow and expensive. Ask for a short escalation process followed by arbitration in an Indian city.

#### `no_late_payment_interest`

**Applies to:** Payment Terms & Pricing

**Criterion:** Payment terms with no stated consequence for late payment, leaving the supplier without a contractual remedy for delay.

**Detectors:** `absent_any`

**Shown to the user:**

> This clause says when you should be paid but not what happens if payment is late. Without that, there is little pressure to pay on time. Ask for interest on overdue amounts — and note that the MSMED Act, 2006 provides for compound interest on late payments to registered micro and small enterprises regardless of what the contract says.

#### `one_sided_assignment_restriction`

**Applies to:** Assignment & Change of Control

**Criterion:** A restriction on assignment binding one party only, leaving the other free to transfer the contract.

**Detectors:** `one_sided_obligation`

**Shown to the user:**

> You cannot transfer this contract to anyone else, but the restriction does not appear to apply equally to the other side. They could hand the contract to a different company — possibly one you would not have chosen to work with. Ask for the restriction to apply both ways.

#### `payment_term_over_45_days`

**Applies to:** Late Payment, Interest & GST, Payment Terms & Pricing

**Criterion:** MSMED Act, 2006, section 15 — a buyer must pay a registered micro or small enterprise within 45 days of acceptance of goods or services.

**Detectors:** `numeric_days_gt`

**Shown to the user:**

> Payment here is due more than 45 days after invoice. If your business is a registered micro or small enterprise under the MSMED Act, 2006, you are entitled to be paid within 45 days, and a longer period written into a contract does not remove that right. You can raise a delayed-payment claim through the MSME Samadhaan process.

#### `perpetual_confidentiality`

**Applies to:** Confidentiality

**Criterion:** Confidentiality obligations with unlimited duration, which are difficult to comply with and to evidence over time.

**Detectors:** `unbounded_duration`

**Shown to the user:**

> This confidentiality duty never ends. That is a long time to keep controlling who in your business has seen what, and it can be hard to prove you complied years later. Three to five years after the contract ends is a common and more workable period, with indefinite protection kept only for genuine trade secrets.

#### `post_term_noncompete`

**Applies to:** Exclusivity & Non-Compete

**Criterion:** A restraint on trade continuing after the contract ends. Section 27 of the Indian Contract Act, 1872 treats agreements in restraint of trade as void subject to limited exceptions, so enforceability is uncertain.

**Detectors:** `present_all`, `present_any`

**Shown to the user:**

> This clause tries to stop you competing or approaching certain customers even after the contract has ended. Restrictions like this are treated cautiously under Indian law — section 27 of the Indian Contract Act, 1872 makes agreements in restraint of trade void, with limited exceptions — so whether it could actually be enforced is genuinely unclear. If this limits how you earn a living after the contract, it is worth a lawyer's view.

#### `unlimited_audit_rights`

**Applies to:** Audit, Inspection & Compliance

**Criterion:** Audit or inspection rights with no limit on notice, frequency or scope.

**Detectors:** `absent_any`, `present_any`

**Shown to the user:**

> The other side can inspect your records or premises at any time, without having to give notice or limit how often. That is disruptive to run a business around. Ask for reasonable prior notice, during working hours, and no more than once or twice a year.

## Contract-level rules (4)

These check for an entire clause type being *absent* from the
contract. They have no clause to attach to, so they appear in the
report summary rather than against an individual clause.

#### `no_confidentiality_clause`

**Fires when the contract has no:** Confidentiality

**Severity:** Caution

**Criterion:** No confidentiality provision, leaving commercially sensitive information shared under the contract unprotected.

**Shown to the user:**

> This contract does not appear to protect confidential information. Prices, customer lists or methods you share during the work could be passed on. Ask for a confidentiality clause covering both sides.

#### `no_force_majeure_clause`

**Fires when the contract has no:** Force Majeure

**Severity:** Caution

**Criterion:** No force majeure provision anywhere in the contract, leaving performance obligations absolute.

**Shown to the user:**

> This contract does not appear to deal with events outside either side's control — natural disasters, strikes, government restrictions. Without such a clause you could still be held to your obligations when something genuinely prevents you performing. Ask for a force majeure clause.

#### `no_limitation_of_liability_clause`

**Fires when the contract has no:** Limitation of Liability

**Severity:** High-Risk

**Criterion:** No limitation-of-liability provision anywhere in the contract, leaving exposure unbounded by default.

**Shown to the user:**

> This contract does not appear to limit how much either side can be made to pay if things go wrong. That leaves your exposure open-ended. Ask for a liability cap — commonly the total fees paid in the previous twelve months.

#### `no_payment_terms_clause`

**Fires when the contract has no:** Payment Terms & Pricing

**Severity:** High-Risk

**Criterion:** No identifiable payment-terms provision, leaving the timing and basis of payment undefined.

**Shown to the user:**

> We could not find a clause setting out when and how you get paid. That is unusual and important. Make sure payment timing, invoicing and the amount are written down before you sign.

## Statutory references

Rules that cite Indian law, satisfying the SRS section 6 requirement that
categories be reviewed for relevance to Indian commercial norms rather
than inherited wholesale from US-centric CUAD:

| Rule | Statute |
|---|---|
| `payment_term_over_45_days` | MSMED Act, 2006, s.15 — 45-day payment ceiling for registered micro and small enterprises |
| `no_late_payment_interest` | MSMED Act, 2006 — statutory compound interest on delayed payment |
| `post_term_noncompete` | Indian Contract Act, 1872, s.27 — agreements in restraint of trade |
| `foreign_arbitration_seat` | Arbitration and Conciliation Act, 1996 — India-seated arbitration |

## Known limitations

- **Asymmetry detection does not know which side you are.** The
  `one_sided_obligation` and `one_sided_right` detectors flag a clause that
  runs one way, in either direction. Until the upload flow captures whether
  the user is the supplier or the customer, a clause that is one-sided *in
  the user's favour* is flagged too.
- **The rubric reads text, not intent.** A liability cap expressed in an
  unusual form may be missed, and a clause that is fine in its commercial
  context may still be flagged. This is why the output is triage and not
  advice.
- **Detection is English-only**, matching the V1.0 scope in SRS section 6.
