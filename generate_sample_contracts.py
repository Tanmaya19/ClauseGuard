"""
Generate three sample commercial contract PDFs for testing ClauseGuard.

Run from the project root:
    python generate_sample_contracts.py

Output: sample_contracts/
    vendor_supply_agreement.pdf
    software_services_agreement.pdf
    non_disclosure_agreement.pdf
"""

import os
from pathlib import Path
from textwrap import dedent

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

OUT_DIR = Path(__file__).parent / "sample_contracts"
OUT_DIR.mkdir(exist_ok=True)

# ── Style helpers ────────────────────────────────────────────────────────────

styles = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "ContractTitle",
    parent=styles["Title"],
    fontSize=16,
    spaceAfter=6,
)
HEADING = ParagraphStyle(
    "ClauseHeading",
    parent=styles["Heading2"],
    fontSize=11,
    spaceBefore=14,
    spaceAfter=4,
    keepWithNext=True,
)
BODY = ParagraphStyle(
    "ClauseBody",
    parent=styles["Normal"],
    fontSize=10,
    leading=14,
    spaceAfter=6,
)
SUB = ParagraphStyle(
    "SubHeading",
    parent=styles["Normal"],
    fontSize=10,
    leading=14,
    spaceAfter=4,
    leftIndent=12,
)

def make_doc(filename: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(OUT_DIR / filename),
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )


def p(text: str, style=None) -> Paragraph:
    return Paragraph(text, style or BODY)


def h(text: str) -> Paragraph:
    return Paragraph(text, HEADING)


def sp(n: int = 1) -> Spacer:
    return Spacer(1, n * 4 * mm)


# ── Contract 1: Vendor Supply Agreement ─────────────────────────────────────

def build_vendor_supply():
    doc = make_doc("vendor_supply_agreement.pdf")
    story = []

    story += [
        p("VENDOR SUPPLY AGREEMENT", TITLE),
        p("This Vendor Supply Agreement (\"Agreement\") is entered into as of 1 January 2025 "
          "between ALPHA INDUSTRIES PRIVATE LIMITED, a company incorporated under the "
          "Companies Act 2013, having its registered office at 45 Industrial Area, Phase II, "
          "Pune 411057 (\"Buyer\"), and the vendor identified in Schedule A (\"Vendor\")."),
        sp(),
    ]

    story += [
        h("1. DEFINITIONS"),
        p("1.1 \"Goods\" means the products described in Schedule A supplied by Vendor to Buyer."),
        p("1.2 \"Delivery Date\" means the date specified in each purchase order issued by Buyer."),
        p("1.3 \"Specifications\" means the technical requirements set out in Schedule B, "
          "as amended by Buyer from time to time at its sole discretion."),
        p("1.4 \"Defective Goods\" means any Goods that do not conform to the Specifications "
          "or are otherwise unfit for purpose as determined solely by Buyer."),
    ]

    story += [
        h("2. PURCHASE ORDERS AND DELIVERY"),
        p("2.1 Buyer shall issue purchase orders from time to time. Each purchase order shall "
          "constitute a binding obligation of Vendor upon issuance by Buyer."),
        p("2.2 Vendor shall deliver Goods on or before the Delivery Date. Time is of the essence. "
          "Buyer may reject any delivery that arrives after the Delivery Date without any "
          "obligation to pay for such Goods."),
        p("2.3 Buyer reserves the right to modify, suspend, or cancel any purchase order at "
          "any time without liability to Vendor."),
    ]

    story += [
        h("3. PRICE AND PAYMENT"),
        p("3.1 Buyer shall pay Vendor the prices set out in Schedule A within ninety (90) "
          "days of Buyer's acceptance of the Goods (\"Payment Terms\")."),
        p("3.2 Buyer may set off against any amount owed to Vendor any amount that Vendor "
          "owes to Buyer, whether arising under this Agreement or otherwise."),
        p("3.3 Buyer may at any time and without notice to Vendor revise the prices set out "
          "in Schedule A. Vendor's continued supply of Goods shall constitute acceptance "
          "of the revised prices."),
    ]

    story += [
        h("4. QUALITY AND INSPECTION"),
        p("4.1 All Goods supplied under this Agreement shall conform to the Specifications "
          "and be free from defects in material and workmanship."),
        p("4.2 Buyer shall have the right to inspect Goods at Vendor's premises at any time "
          "during normal business hours upon 24 hours' notice, or without notice if Buyer "
          "reasonably suspects a quality issue."),
        p("4.3 Vendor shall, at Buyer's option, either replace Defective Goods or refund "
          "the full purchase price within seven (7) days of notification."),
    ]

    story += [
        h("5. INTELLECTUAL PROPERTY"),
        p("5.1 All intellectual property rights in any improvements, modifications, "
          "derivative works, or inventions created by Vendor in connection with the "
          "supply of Goods, whether or not specifically requested by Buyer, shall vest "
          "in Buyer absolutely and Vendor hereby assigns all such rights to Buyer with "
          "full title guarantee."),
        p("5.2 Vendor shall execute such documents and take such steps as Buyer may "
          "reasonably require to give effect to the assignment in Clause 5.1."),
        p("5.3 Vendor grants Buyer a perpetual, irrevocable, royalty-free licence to use "
          "any background intellectual property of Vendor that is incorporated into the Goods."),
    ]

    story += [
        h("6. CONFIDENTIALITY"),
        p("6.1 Vendor shall keep confidential all Confidential Information of Buyer. "
          "\"Confidential Information\" means all information disclosed by Buyer to Vendor "
          "in any form, including but not limited to technical data, trade secrets, "
          "know-how, business plans, and customer data."),
        p("6.2 Vendor shall not disclose Confidential Information to any third party "
          "without Buyer's prior written consent."),
        p("6.3 Vendor shall, at the end of this Agreement or upon Buyer's request, "
          "immediately return or destroy all Confidential Information."),
        p("6.4 This obligation of confidentiality shall survive termination of this "
          "Agreement for a period of ten (10) years."),
    ]

    story += [
        h("7. INDEMNIFICATION"),
        p("7.1 Vendor shall indemnify, defend, and hold harmless Buyer, its affiliates, "
          "officers, directors, employees, and agents from and against any and all claims, "
          "damages, losses, costs, and expenses (including reasonable legal fees) arising "
          "out of or in connection with: (a) any breach of this Agreement by Vendor; "
          "(b) any negligence or wilful misconduct of Vendor; (c) any defect in the Goods; "
          "or (d) any claim that the Goods infringe any third-party intellectual property rights."),
        p("7.2 Vendor shall maintain, at its own cost, adequate insurance coverage including "
          "product liability insurance with a minimum cover of INR 5,00,00,000 "
          "(Rupees Five Crore) per occurrence."),
    ]

    story += [
        h("8. LIMITATION OF LIABILITY"),
        p("8.1 Notwithstanding any other provision of this Agreement, Buyer's total "
          "aggregate liability to Vendor under or in connection with this Agreement, "
          "whether arising in contract, tort (including negligence), breach of statutory duty, "
          "or otherwise, shall not exceed INR 50,000 (Rupees Fifty Thousand)."),
        p("8.2 Buyer shall not be liable to Vendor for any indirect, consequential, "
          "special, incidental, or punitive damages, including loss of profit, loss of "
          "revenue, loss of business, or loss of anticipated savings, however caused and "
          "whether or not Buyer was advised of the possibility of such losses."),
        p("8.3 Nothing in this Clause 8 shall limit Vendor's liability to Buyer."),
    ]

    story += [
        h("9. TERMINATION"),
        p("9.1 Buyer may terminate this Agreement at any time and for any reason by giving "
          "Vendor two (2) days' written notice."),
        p("9.2 Buyer may terminate this Agreement immediately without notice if Vendor "
          "breaches any provision of this Agreement or becomes insolvent."),
        p("9.3 Upon termination, Vendor shall immediately cease supplying Goods and "
          "deliver to Buyer all materials, tooling, and dies provided by Buyer."),
    ]

    story += [
        h("10. GOVERNING LAW AND DISPUTES"),
        p("10.1 This Agreement shall be governed by and construed in accordance with "
          "the laws of England and Wales."),
        p("10.2 Any dispute arising under this Agreement shall be subject to the exclusive "
          "jurisdiction of the courts of England and Wales."),
    ]

    story += [
        h("11. NON-COMPETE"),
        p("11.1 During the term of this Agreement and for a period of three (3) years "
          "thereafter, Vendor shall not, directly or indirectly, supply, manufacture, or "
          "distribute products of the type described in Schedule A to any of Buyer's "
          "competitors, as notified by Buyer from time to time."),
        p("11.2 Vendor shall not solicit, employ, or engage any employee or contractor "
          "of Buyer for a period of two (2) years after termination of this Agreement."),
    ]

    story += [
        h("12. AUTOMATIC RENEWAL"),
        p("12.1 This Agreement shall automatically renew for successive one (1) year "
          "periods unless either party provides written notice of non-renewal at least "
          "ninety (90) days before the end of the then-current term."),
        p("12.2 For the avoidance of doubt, Vendor's failure to give timely notice "
          "shall result in automatic renewal on the same terms."),
    ]

    story += [
        h("13. GENERAL"),
        p("13.1 This Agreement constitutes the entire agreement between the parties "
          "relating to its subject matter and supersedes all prior agreements."),
        p("13.2 Buyer may assign this Agreement without Vendor's consent. "
          "Vendor may not assign this Agreement without Buyer's prior written consent."),
        p("13.3 Buyer may amend this Agreement at any time by notifying Vendor in writing. "
          "Vendor's continued supply of Goods constitutes acceptance of the amendment."),
    ]

    story.append(sp(4))
    story.append(p("SCHEDULE A — VENDOR AND GOODS DETAILS", HEADING))
    story.append(p("Vendor Name: ___________________________"))
    story.append(p("Vendor Address: ___________________________"))
    story.append(p("Goods Description: ___________________________"))
    story.append(p("Unit Price (INR): ___________________________"))

    doc.build(story)
    print(f"Created: {OUT_DIR}/vendor_supply_agreement.pdf")


# ── Contract 2: Software Services Agreement ─────────────────────────────────

def build_software_services():
    doc = make_doc("software_services_agreement.pdf")
    story = []

    story += [
        p("SOFTWARE SERVICES AGREEMENT", TITLE),
        p("This Software Services Agreement (\"Agreement\") is made on 15 March 2025 "
          "between TECHVAULT SOLUTIONS PVT LTD, having its registered office at "
          "Unit 302, Prestige Tower, Bengaluru 560001 (\"Client\"), and the service "
          "provider identified in the Order Form attached hereto (\"Service Provider\")."),
        sp(),
    ]

    story += [
        h("1. SERVICES"),
        p("1.1 Service Provider shall provide the software development, maintenance, and "
          "support services described in the Statement of Work (\"SOW\") attached as "
          "Exhibit A."),
        p("1.2 Service Provider shall perform the Services to the satisfaction of Client. "
          "Client's determination of whether Services meet the required standard shall "
          "be final and binding."),
        p("1.3 Service Provider shall make available to Client such personnel as Client "
          "may reasonably require. Client may require Service Provider to replace any "
          "personnel assigned to the project within 48 hours."),
    ]

    story += [
        h("2. FEES AND PAYMENT"),
        p("2.1 Client shall pay Service Provider the fees set out in Exhibit A within "
          "sixty (60) days of invoice."),
        p("2.2 Client may withhold payment of any invoice it disputes in good faith. "
          "Client shall notify Service Provider of any disputed invoice within 60 days "
          "of receipt."),
        p("2.3 Service Provider shall not be entitled to suspend Services due to "
          "non-payment unless the undisputed overdue amount exceeds INR 10,00,000 "
          "(Rupees Ten Lakh) and remains unpaid for more than 120 days."),
    ]

    story += [
        h("3. INTELLECTUAL PROPERTY RIGHTS"),
        p("3.1 All works, inventions, discoveries, software code, documentation, "
          "designs, data, algorithms, know-how, and all other results arising from "
          "the performance of the Services (\"Deliverables\"), whether or not protectable "
          "as intellectual property, shall be the exclusive property of Client from "
          "the moment of creation."),
        p("3.2 Service Provider hereby assigns to Client, with full title guarantee, "
          "all intellectual property rights in the Deliverables, including all patents, "
          "copyrights, trade secrets, and other proprietary rights, to the fullest "
          "extent permitted by applicable law, on a global basis in perpetuity."),
        p("3.3 Service Provider shall ensure that all of its employees, contractors, "
          "and sub-contractors execute assignments confirming the assignment in "
          "Clause 3.2 prior to commencing any work."),
        p("3.4 This assignment extends to all pre-existing materials, methodologies, "
          "frameworks, and tools developed by Service Provider that are incorporated "
          "into or necessary to use the Deliverables."),
        p("3.5 Service Provider waives all moral rights in the Deliverables to the "
          "maximum extent permitted by applicable law."),
    ]

    story += [
        h("4. CONFIDENTIALITY"),
        p("4.1 Service Provider acknowledges that in the course of providing the Services "
          "it will have access to Confidential Information of Client."),
        p("4.2 Service Provider shall: (a) keep all Confidential Information strictly "
          "confidential; (b) not disclose it to any third party without Client's prior "
          "written consent; (c) use it only for the purpose of performing the Services; "
          "and (d) apply at least the same degree of protection as it applies to its "
          "own confidential information."),
        p("4.3 The obligations in this Clause 4 shall survive termination of this "
          "Agreement for a period of fifteen (15) years."),
    ]

    story += [
        h("5. DATA PROTECTION"),
        p("5.1 Service Provider shall process Client's personal data only in accordance "
          "with Client's written instructions."),
        p("5.2 Service Provider shall implement appropriate technical and organisational "
          "measures to protect personal data against accidental or unlawful destruction, "
          "loss, alteration, unauthorised disclosure, or access."),
        p("5.3 Service Provider shall notify Client within 12 hours of becoming aware "
          "of a personal data breach affecting Client's data."),
    ]

    story += [
        h("6. WARRANTIES"),
        p("6.1 Service Provider warrants that: (a) it has the right to enter into this "
          "Agreement; (b) the Services will be performed with reasonable skill and care; "
          "(c) the Deliverables will conform to the specifications in the SOW; and "
          "(d) the Deliverables will not infringe any third-party intellectual property rights."),
        p("6.2 Service Provider shall, at its own cost, promptly remedy any breach of "
          "the warranty in Clause 6.1 within 5 business days of notification by Client."),
    ]

    story += [
        h("7. INDEMNIFICATION"),
        p("7.1 Service Provider shall indemnify, defend, and hold harmless Client and "
          "its affiliates against all claims, liabilities, damages, costs, and expenses "
          "arising from: (a) any breach of this Agreement by Service Provider; "
          "(b) any infringement of third-party intellectual property rights by the "
          "Deliverables; (c) any gross negligence or wilful misconduct of Service "
          "Provider; or (d) any claims by Service Provider's employees or contractors "
          "arising from the performance of the Services."),
    ]

    story += [
        h("8. LIMITATION OF LIABILITY"),
        p("8.1 To the maximum extent permitted by applicable law, Client's total "
          "liability to Service Provider under this Agreement shall be limited to "
          "the fees actually paid to Service Provider in the three (3) months "
          "immediately preceding the event giving rise to the claim."),
        p("8.2 In no event shall Client be liable to Service Provider for any "
          "loss of profits, loss of revenue, loss of business, loss of data, "
          "or any indirect or consequential loss, even if Client was advised "
          "of the possibility of such loss."),
        p("8.3 The foregoing limitation of liability shall not apply to "
          "Service Provider's liability to Client."),
    ]

    story += [
        h("9. NON-SOLICITATION AND NON-COMPETE"),
        p("9.1 For a period of two (2) years after termination of this Agreement, "
          "Service Provider shall not, directly or indirectly, solicit or employ "
          "any employee or contractor of Client who was involved in this project."),
        p("9.2 For a period of three (3) years after termination, Service Provider "
          "shall not provide services similar to the Services to any competitor "
          "of Client in the same product category, as determined by Client."),
        p("9.3 For a period of two (2) years after termination, Service Provider "
          "shall not engage with any of Client's existing customers or prospects "
          "whose details were disclosed during the course of this Agreement."),
    ]

    story += [
        h("10. TERMINATION"),
        p("10.1 Client may terminate this Agreement at any time for convenience "
          "by giving Service Provider seven (7) days' written notice."),
        p("10.2 Client may terminate immediately without notice if Service Provider "
          "commits a material breach or becomes insolvent."),
        p("10.3 Upon termination, Service Provider shall deliver all work-in-progress "
          "and Deliverables to Client within 24 hours."),
        p("10.4 Service Provider shall not be entitled to any compensation for "
          "termination for convenience, including for any work-in-progress."),
    ]

    story += [
        h("11. AUDIT RIGHTS"),
        p("11.1 Client shall have the right at any time to audit Service Provider's "
          "books, records, systems, and premises relating to this Agreement, "
          "with or without prior notice."),
        p("11.2 Service Provider shall cooperate fully with any such audit and "
          "provide Client and its appointed auditors with access to all relevant "
          "materials and personnel."),
    ]

    story += [
        h("12. GOVERNING LAW"),
        p("12.1 This Agreement shall be governed by and construed in accordance "
          "with the laws of the State of Delaware, United States."),
        p("12.2 Each party submits to the exclusive jurisdiction of the courts "
          "of the State of Delaware for the resolution of all disputes."),
    ]

    story += [
        h("13. AUTOMATIC RENEWAL AND PRICING"),
        p("13.1 This Agreement shall automatically renew for successive one-year "
          "terms unless either party gives 120 days' written notice of non-renewal."),
        p("13.2 Client may revise the fee schedule at any time by giving 30 days' "
          "notice. Service Provider's continued performance shall constitute "
          "acceptance of the revised fees."),
    ]

    doc.build(story)
    print(f"Created: {OUT_DIR}/software_services_agreement.pdf")


# ── Contract 3: Non-Disclosure Agreement ────────────────────────────────────

def build_nda():
    doc = make_doc("non_disclosure_agreement.pdf")
    story = []

    story += [
        p("MUTUAL NON-DISCLOSURE AGREEMENT", TITLE),
        p("This Non-Disclosure Agreement (\"NDA\") is entered into as of 1 April 2025 "
          "between MERIDIAN CAPITAL ADVISORS LLP, having its registered office at "
          "Suite 5, Nariman Point, Mumbai 400021 (\"Disclosing Party\"), and the "
          "Receiving Party identified in Schedule 1."),
        sp(),
    ]

    story += [
        h("1. DEFINITIONS"),
        p("1.1 \"Confidential Information\" means any and all information, whether "
          "technical, commercial, financial, or otherwise, in whatever form communicated "
          "or however maintained, that is disclosed by or on behalf of Disclosing Party "
          "to Receiving Party. Confidential Information includes, without limitation: "
          "business plans, strategies, financial projections, client lists, trade secrets, "
          "software, source code, formulae, processes, know-how, designs, prototypes, "
          "pricing information, personnel information, and any information relating to "
          "any actual or potential transaction."),
        p("1.2 Confidential Information does not include information that: (a) was in the "
          "public domain before disclosure through no fault of Receiving Party; or "
          "(b) was independently developed by Receiving Party without use of or reference "
          "to the Confidential Information, as evidenced by contemporaneous written records."),
    ]

    story += [
        h("2. CONFIDENTIALITY OBLIGATIONS"),
        p("2.1 Receiving Party shall: (a) hold all Confidential Information in strict "
          "confidence; (b) not disclose Confidential Information to any third party "
          "without Disclosing Party's prior written consent; (c) use Confidential "
          "Information solely for the Purpose described in Schedule 1; and "
          "(d) apply security measures no less stringent than those used to protect "
          "its own most confidential information, but in no event less than reasonable care."),
        p("2.2 Receiving Party may disclose Confidential Information to its employees "
          "and professional advisors on a strict need-to-know basis, provided that "
          "each such person is bound by written obligations of confidentiality at "
          "least as stringent as those in this NDA."),
        p("2.3 Receiving Party shall promptly notify Disclosing Party of any actual "
          "or suspected unauthorised disclosure of Confidential Information."),
    ]

    story += [
        h("3. TERM AND DURATION"),
        p("3.1 This NDA shall come into force on the date first written above and "
          "shall remain in effect for a period of twenty (20) years."),
        p("3.2 The obligations of confidentiality in Clause 2 shall survive the "
          "termination or expiry of this NDA indefinitely with respect to trade secrets, "
          "and for a period of ten (10) years with respect to all other "
          "Confidential Information."),
    ]

    story += [
        h("4. RETURN OF CONFIDENTIAL INFORMATION"),
        p("4.1 On request by Disclosing Party, Receiving Party shall promptly return "
          "or securely destroy all Confidential Information and all copies thereof."),
        p("4.2 Receiving Party shall certify in writing, within 5 business days of "
          "such request, that all Confidential Information has been returned or destroyed."),
    ]

    story += [
        h("5. INTELLECTUAL PROPERTY"),
        p("5.1 No licence or right in any intellectual property of Disclosing Party "
          "is granted by this NDA."),
        p("5.2 Any work, analysis, report, invention, or discovery created by "
          "Receiving Party that is based upon, incorporates, or is derived from "
          "the Confidential Information (\"Derived Works\") shall be the exclusive "
          "property of Disclosing Party, and Receiving Party hereby assigns all "
          "rights in such Derived Works to Disclosing Party."),
    ]

    story += [
        h("6. REMEDIES"),
        p("6.1 Receiving Party acknowledges that any breach of this NDA will cause "
          "irreparable harm to Disclosing Party for which monetary damages would be "
          "inadequate."),
        p("6.2 Disclosing Party shall be entitled to seek injunctive relief and other "
          "equitable remedies without the need to post any bond or other security."),
        p("6.3 In the event of a breach, Receiving Party shall pay Disclosing Party "
          "liquidated damages of INR 2,00,00,000 (Rupees Two Crore) per breach, "
          "in addition to all other remedies available at law or in equity."),
    ]

    story += [
        h("7. NON-SOLICITATION"),
        p("7.1 During the term of this NDA and for a period of three (3) years "
          "thereafter, Receiving Party shall not, directly or indirectly, "
          "solicit, hire, or engage any employee, consultant, or contractor "
          "of Disclosing Party."),
    ]

    story += [
        h("8. NO REVERSE ENGINEERING"),
        p("8.1 Receiving Party shall not reverse-engineer, disassemble, decompile, "
          "or attempt to derive the source code, underlying ideas, or algorithms "
          "of any software or technology that constitutes or is included in the "
          "Confidential Information."),
    ]

    story += [
        h("9. GOVERNING LAW AND DISPUTE RESOLUTION"),
        p("9.1 This NDA shall be governed by the laws of the State of New York, "
          "United States of America."),
        p("9.2 Any dispute arising under this NDA shall be resolved by binding "
          "arbitration under the AAA Commercial Arbitration Rules, with the "
          "arbitration seated in New York City."),
        p("9.3 The language of the arbitration shall be English. Each party shall "
          "bear its own costs unless the arbitral tribunal orders otherwise."),
    ]

    story += [
        h("10. REPRESENTATIONS"),
        p("10.1 Each party represents and warrants that: (a) it has full authority "
          "to enter into this NDA; (b) entering into this NDA does not violate "
          "any agreement or obligation to a third party; and (c) it will comply "
          "with all applicable laws and regulations in performing its obligations "
          "under this NDA."),
    ]

    story += [
        h("11. MISCELLANEOUS"),
        p("11.1 This NDA constitutes the entire agreement between the parties "
          "relating to confidentiality of the Confidential Information and "
          "supersedes all prior discussions and agreements."),
        p("11.2 Any amendment to this NDA must be in writing and signed by "
          "authorised representatives of both parties."),
        p("11.3 Disclosing Party may assign this NDA without Receiving Party's "
          "consent. Receiving Party may not assign this NDA without Disclosing "
          "Party's prior written consent."),
        p("11.4 The invalidity of any provision of this NDA shall not affect "
          "the validity of the remaining provisions."),
    ]

    story.append(sp(4))
    story.append(p("SCHEDULE 1 — PARTIES AND PURPOSE", HEADING))
    story.append(p("Receiving Party: ___________________________"))
    story.append(p("Receiving Party Address: ___________________________"))
    story.append(p("Purpose: Evaluation of a potential business transaction between the parties."))

    doc.build(story)
    print(f"Created: {OUT_DIR}/non_disclosure_agreement.pdf")


if __name__ == "__main__":
    build_vendor_supply()
    build_software_services()
    build_nda()
    print("\nAll sample contracts generated in:", OUT_DIR)
