"""The 20-class clause taxonomy (REQ-3.1, SRS 6).

Collapsed from CUAD's 41 M&A-oriented categories and extended for Indian
commercial norms. The ``cuad_sources`` field is the audit trail SRS 6 requires
for label mapping; ``thin_in_cuad`` marks the classes that depend on the
Indian domain-adaptation corpus rather than CUAD.

This module is the single source of truth for label keys. ``ml/`` imports it,
the rubric's ``applies_to`` is validated against it, and the frontend reads
display names from the API — so a label added here propagates everywhere
instead of being duplicated in three places.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ClauseType:
    key: str
    display: str
    description: str
    cuad_sources: tuple[str, ...] = ()
    thin_in_cuad: bool = False
    # Keywords used only by the interim baseline classifier, never by the
    # trained model. Kept beside the class so the two stay in step.
    baseline_cues: tuple[str, ...] = field(default=())


UNCATEGORIZED = "uncategorized"

CLAUSE_TYPES: tuple[ClauseType, ...] = (
    ClauseType(
        key="parties_definitions",
        display="Parties & Definitions",
        description="Who the agreement is between, and the defined terms it uses.",
        cuad_sources=("Parties", "Document Name"),
        baseline_cues=("this agreement is made", "between", "hereinafter", "shall mean",
                       "definitions", "means and includes"),
    ),
    ClauseType(
        key="term_effective_date",
        display="Term & Effective Date",
        description="When the contract starts and how long it lasts.",
        cuad_sources=("Agreement Date", "Effective Date", "Expiration Date"),
        baseline_cues=("effective date", "commence on", "term of this agreement",
                       "shall remain in force", "expire on"),
    ),
    ClauseType(
        key="renewal_auto_renewal",
        display="Renewal & Auto-Renewal",
        description="Whether and how the contract extends past its initial term.",
        cuad_sources=("Renewal Term", "Notice Period To Terminate Renewal"),
        baseline_cues=("automatically renew", "auto-renew", "renewal term",
                       "successive periods", "unless either party gives notice"),
    ),
    ClauseType(
        key="termination_convenience",
        display="Termination for Convenience",
        description="Ending the contract without needing a reason.",
        cuad_sources=("Termination For Convenience",),
        baseline_cues=("terminate this agreement at any time", "for convenience",
                       "without cause", "without assigning any reason"),
    ),
    ClauseType(
        key="termination_cause_cure",
        display="Termination for Cause & Cure",
        description="Ending the contract for breach, and any chance to fix it first.",
        thin_in_cuad=True,
        baseline_cues=("material breach", "cure period", "remedy such breach",
                       "rectify", "default", "terminate for cause"),
    ),
    ClauseType(
        key="payment_terms",
        display="Payment Terms & Pricing",
        description="What is owed, when, and how prices may change.",
        cuad_sources=("Price Restrictions", "Minimum Commitment", "Revenue/Profit Sharing",
                      "Volume Restriction"),
        baseline_cues=("payment", "invoice", "price", "fees", "consideration",
                       "payable within", "purchase order"),
    ),
    ClauseType(
        key="late_payment_interest_gst",
        display="Late Payment, Interest & GST",
        description="Consequences of late payment, interest, and tax handling.",
        thin_in_cuad=True,
        baseline_cues=("gst", "goods and services tax", "interest at the rate",
                       "late payment", "delayed payment", "tds", "tax deducted at source",
                       "msmed"),
    ),
    ClauseType(
        key="indemnity",
        display="Indemnity",
        description="Who covers whose losses if something goes wrong.",
        cuad_sources=("Insurance",),
        baseline_cues=("indemnify", "indemnity", "hold harmless", "defend and hold",
                       "indemnified party"),
    ),
    ClauseType(
        key="limitation_of_liability",
        display="Limitation of Liability",
        description="Any ceiling on what each side can be made to pay.",
        cuad_sources=("Cap On Liability", "Uncapped Liability"),
        baseline_cues=("limitation of liability", "aggregate liability", "shall not exceed",
                       "consequential damages", "in no event shall", "liable for"),
    ),
    ClauseType(
        key="warranties",
        display="Warranties & Representations",
        description="Promises each side makes about facts and quality.",
        cuad_sources=("Warranty Duration",),
        baseline_cues=("warrants", "warranty", "represents and warrants",
                       "representations", "fit for purpose", "merchantability"),
    ),
    ClauseType(
        key="confidentiality",
        display="Confidentiality",
        description="What information must be kept secret, and for how long.",
        thin_in_cuad=True,
        baseline_cues=("confidential information", "confidentiality", "non-disclosure",
                       "shall not disclose", "proprietary information"),
    ),
    ClauseType(
        key="ip_ownership_licence",
        display="IP Ownership & Licence",
        description="Who owns intellectual property, and who may use it.",
        cuad_sources=("IP Ownership Assignment", "License Grant", "Joint IP Ownership",
                      "Non-Transferable License", "Irrevocable Or Perpetual License"),
        baseline_cues=("intellectual property", "copyright", "trademark", "patent",
                       "licence", "license", "work product", "assigns all right"),
    ),
    ClauseType(
        key="exclusivity_noncompete",
        display="Exclusivity & Non-Compete",
        description="Restrictions on dealing with competitors or other customers.",
        cuad_sources=("Exclusivity", "Non-Compete", "No-Solicit Of Customers",
                      "No-Solicit Of Employees", "Competitive Restriction Exception"),
        # Not bare "exclusive": it matches "exclusive of GST" and "exclusive
        # jurisdiction", which are a tax term and a forum term respectively.
        baseline_cues=("exclusivity", "exclusive supplier", "exclusive distributor",
                       "exclusively to", "sole supplier", "non-compete",
                       "shall not compete", "shall not solicit", "restraint of trade",
                       "shall not supply to"),
    ),
    ClauseType(
        key="assignment_control",
        display="Assignment & Change of Control",
        description="Whether the contract can be transferred to someone else.",
        cuad_sources=("Anti-Assignment", "Change Of Control", "Rofr/Rofo/Rofn"),
        baseline_cues=("assign", "assignment", "change of control", "successors and assigns",
                       "novation", "transfer its rights"),
    ),
    ClauseType(
        key="governing_law",
        display="Governing Law & Jurisdiction",
        description="Which country's law applies and which courts decide.",
        cuad_sources=("Governing Law",),
        baseline_cues=("governing law", "governed by the laws", "jurisdiction",
                       "courts at", "exclusive jurisdiction"),
    ),
    ClauseType(
        key="dispute_arbitration",
        display="Dispute Resolution & Arbitration",
        description="How disagreements get resolved before or instead of court.",
        thin_in_cuad=True,
        baseline_cues=("arbitration", "arbitral", "arbitrator", "dispute resolution",
                       "mediation", "conciliation", "seat of arbitration"),
    ),
    ClauseType(
        key="force_majeure",
        display="Force Majeure",
        description="What happens if events outside either side's control intervene.",
        thin_in_cuad=True,
        baseline_cues=("force majeure", "act of god", "beyond the reasonable control",
                       "pandemic", "natural calamity"),
    ),
    ClauseType(
        key="audit_compliance",
        display="Audit, Inspection & Compliance",
        description="Rights to inspect records, premises or processes.",
        cuad_sources=("Audit Rights",),
        baseline_cues=("audit", "inspect", "inspection", "books and records",
                       "compliance with applicable law", "right to examine"),
    ),
    ClauseType(
        key="insurance",
        display="Insurance",
        description="Cover each side must maintain.",
        cuad_sources=("Insurance",),
        baseline_cues=("insurance", "insured", "policy of insurance", "coverage of not less"),
    ),
    ClauseType(
        key="notices_misc",
        display="Notices & Miscellaneous",
        description="How formal notices are sent, plus standard boilerplate.",
        cuad_sources=("Notice",),
        baseline_cues=("notice shall be", "in writing to", "registered post",
                       "entire agreement", "severability", "waiver", "counterparts"),
    ),
)

BY_KEY: dict[str, ClauseType] = {c.key: c for c in CLAUSE_TYPES}
LABEL_KEYS: tuple[str, ...] = tuple(c.key for c in CLAUSE_TYPES)
NUM_LABELS = len(CLAUSE_TYPES)

# Sanity checks that run at import: a duplicated key or a miscounted taxonomy
# would otherwise surface as a silent label-mismatch during training.
assert len(BY_KEY) == len(CLAUSE_TYPES), "duplicate clause-type key"
assert 15 <= NUM_LABELS <= 20, f"SRS 2.5 permits 15-20 classes, found {NUM_LABELS}"


def display_name(key: str) -> str:
    if key == UNCATEGORIZED:
        return "Uncategorized"
    return BY_KEY[key].display


def thin_classes() -> tuple[str, ...]:
    """Classes under-represented in CUAD, reported separately in evaluation."""
    return tuple(c.key for c in CLAUSE_TYPES if c.thin_in_cuad)
