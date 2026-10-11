#!/usr/bin/env python
"""Build ml/eval/indian_eval_set.jsonl from reviewable source.

The clauses live here as readable Python literals rather than directly in the
JSONL, so they can be reviewed and corrected in a diff. Run this script to
regenerate the dataset.

    python ml/eval/build_eval_set.py

PROVENANCE — read this before reporting any metric from this set
----------------------------------------------------------------
These clauses are **synthetic**: written for this project in the style of
Indian MSME vendor, service and non-disclosure agreements, covering the
statutory hooks (MSMED Act payment terms, GST and TDS, the Arbitration and
Conciliation Act 1996, section 27 of the Indian Contract Act) that CUAD has no
coverage of.

They are *not* harvested from real contracts. That is a material limitation,
and it cuts in a specific direction: synthetic clauses written by one author
tend to be **more canonical** than real drafting — more consistent in
vocabulary, less prone to the idiosyncratic phrasing, typos and
locally-invented defined terms that real agreements contain. Metrics on this
set should therefore be read as an **optimistic** estimate of in-domain
performance, not a pessimistic one.

To strengthen the set, replace or supplement these with clauses taken from the
TBD-5 sources (GeM General Terms and Conditions, BSE/NSE disclosed material
contracts, public law-firm templates), recording each source and its licence
basis in ml/MODEL_CARD.md. Keep the `source` field accurate when you do.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.classification.labels import LABEL_KEYS  # noqa: E402

OUTPUT = Path(__file__).parent / "indian_eval_set.jsonl"

SYNTHETIC = "synthetic-indian"

# (clause text, labels)
CLAUSES: list[tuple[str, list[str]]] = [
    # ================================================================
    # late_payment_interest_gst — thin in CUAD, highest priority
    # ================================================================
    ("The Buyer shall make payment of all undisputed invoices within forty-five (45) days from the date of receipt of the invoice, in accordance with the Micro, Small and Medium Enterprises Development Act, 2006. Any delay beyond the said period shall attract compound interest at three times the bank rate notified by the Reserve Bank of India.", ["payment_terms", "late_payment_interest_gst"]),
    ("All prices quoted are exclusive of Goods and Services Tax. GST shall be charged at the rate prevailing on the date of supply and shall be shown separately on each tax invoice raised by the Supplier.", ["late_payment_interest_gst", "payment_terms"]),
    ("The Company shall deduct tax at source at the rates prescribed under the Income Tax Act, 1961 and shall furnish Form 16A to the Service Provider within the statutory timelines.", ["late_payment_interest_gst"]),
    ("In the event of delay in payment beyond the agreed credit period, interest shall accrue on the outstanding amount at the rate of eighteen percent (18%) per annum, calculated from the due date until the date of actual realisation.", ["late_payment_interest_gst", "payment_terms"]),
    ("The Supplier shall be solely responsible for ensuring that its GST registration remains valid and that all invoices raised are GST-compliant. Any input tax credit denied to the Company on account of the Supplier's non-compliance shall be recoverable from the Supplier.", ["late_payment_interest_gst"]),
    ("Payment shall be released only upon the Supplier uploading the corresponding invoice details in the GSTR-1 return for the relevant tax period and the same being reflected in the Company's GSTR-2B.", ["late_payment_interest_gst", "payment_terms"]),
    ("Any statutory levy, cess or duty introduced after the Effective Date shall be borne by the Buyer, provided that the Supplier furnishes documentary evidence of such levy having been paid.", ["late_payment_interest_gst", "payment_terms"]),
    ("Interest on delayed payment shall be payable without the necessity of any demand or notice from the Supplier, and the Buyer's liability to pay such interest shall not be affected by any dispute relating to a part of the invoiced amount.", ["late_payment_interest_gst"]),
    ("The Vendor confirms that it is registered as a micro enterprise under the MSMED Act, 2006 and shall furnish a copy of its Udyam Registration Certificate. The Vendor shall notify the Company forthwith upon any change in its registration status.", ["late_payment_interest_gst", "parties_definitions"]),
    ("Where the Company disputes any part of an invoice, it shall pay the undisputed portion within the agreed period and shall not withhold the entire invoice amount on account of the disputed portion.", ["payment_terms", "late_payment_interest_gst"]),
    ("No interest shall be payable by the Company on any amount withheld or retained under this Agreement, including retention money and security deposits, howsoever long the same may remain outstanding.", ["late_payment_interest_gst", "payment_terms"]),
    ("The Contractor shall raise a single consolidated invoice for each calendar month on or before the fifth day of the succeeding month, failing which payment may be deferred to the next payment cycle without liability for interest.", ["payment_terms", "late_payment_interest_gst"]),
    ("Reverse charge mechanism shall apply to the services rendered hereunder, and the Company shall discharge the GST liability directly to the credit of the Government and issue a payment voucher to the Service Provider.", ["late_payment_interest_gst"]),
    ("The Supplier shall reimburse the Company for any interest or penalty levied on the Company by the tax authorities arising out of any incorrect particulars furnished by the Supplier in its tax invoices.", ["late_payment_interest_gst", "indemnity"]),

    # ================================================================
    # termination_cause_cure — thin in CUAD
    # ================================================================
    ("Either party may terminate this Agreement upon a material breach by the other party, provided that the party alleged to be in breach shall first be given written notice specifying the breach and a period of thirty (30) days within which to remedy the same. Failure to cure within the said period shall entitle the aggrieved party to terminate forthwith.", ["termination_cause_cure"]),
    ("The Company may terminate this Agreement with immediate effect if the Service Provider commits a breach which by its nature is incapable of remedy, or if the Service Provider repeats a breach previously notified and cured.", ["termination_cause_cure"]),
    ("This Agreement shall stand automatically terminated without the requirement of any notice if an order of liquidation is passed against either party, or if a resolution professional is appointed under the Insolvency and Bankruptcy Code, 2016.", ["termination_cause_cure"]),
    ("Upon the Supplier failing to deliver the Goods within the agreed delivery schedule on three or more occasions in any six-month period, the Buyer shall be entitled to terminate this Agreement for cause, notwithstanding that each individual delay may have been condoned.", ["termination_cause_cure"]),
    ("The Principal may terminate this Agreement for cause if the Agent is convicted of any offence involving moral turpitude, or if any officer of the Agent is found to have offered any inducement to an employee of the Principal.", ["termination_cause_cure"]),
    ("Termination for breach shall be without prejudice to any accrued rights or remedies of either party, and shall not affect the continuing obligations of confidentiality set out in Clause 9.", ["termination_cause_cure", "confidentiality"]),
    ("Should the quality of the Services fall below the standards specified in Schedule 2 for two consecutive measurement periods, the Company may issue a performance improvement notice, and if the shortfall persists for a further thirty days, may terminate this Agreement.", ["termination_cause_cure"]),
    ("The Supplier shall be deemed to be in material breach if it assigns this Agreement in contravention of Clause 12, and the Buyer may in such event terminate without affording any opportunity to cure.", ["termination_cause_cure", "assignment_control"]),
    ("Either party may terminate this Agreement forthwith by written notice if the other party ceases to carry on business, or suffers any distress or execution to be levied upon its assets which is not discharged within thirty days.", ["termination_cause_cure"]),
    ("Any termination under this Clause shall take effect from the date specified in the notice of termination, and the Service Provider shall continue to render the Services up to such date unless the Company directs otherwise in writing.", ["termination_cause_cure", "termination_convenience"]),
    ("The Buyer reserves the right to terminate the purchase order in whole or in part if the Goods supplied are found on inspection to be not in conformity with the specifications, and the Supplier fails to replace the non-conforming Goods within fifteen days of intimation.", ["termination_cause_cure", "warranties"]),
    ("On termination for cause attributable to the Supplier, the Supplier shall refund all amounts received in advance in respect of Services not yet rendered, within fifteen days of the date of termination.", ["termination_cause_cure", "payment_terms"]),

    # ================================================================
    # confidentiality — thin in CUAD
    # ================================================================
    ("The Receiving Party shall keep confidential all Confidential Information disclosed by the Disclosing Party and shall not disclose the same to any third party without prior written consent. This obligation shall survive the termination of this Agreement for a period of three (3) years, save in respect of trade secrets, in relation to which the obligation shall continue without limit of time.", ["confidentiality"]),
    ("Confidential Information shall not include information which is or becomes publicly available otherwise than through a breach of this Agreement, or which the Receiving Party can demonstrate was lawfully in its possession prior to disclosure.", ["confidentiality"]),
    ("The Receiving Party shall restrict disclosure of Confidential Information to those of its employees, directors and professional advisers who need to know the same for the purposes of this Agreement, and shall ensure that each such person is bound by obligations of confidentiality no less onerous than those contained herein.", ["confidentiality"]),
    ("Upon termination or upon written demand, the Receiving Party shall forthwith return or, at the option of the Disclosing Party, destroy all documents and materials containing Confidential Information, and shall certify such destruction in writing.", ["confidentiality"]),
    ("Nothing in this Clause shall prevent disclosure of Confidential Information to the extent required by any order of a court of competent jurisdiction or by any regulatory authority, provided that the Receiving Party gives the Disclosing Party prompt notice of such requirement where lawfully permitted to do so.", ["confidentiality"]),
    ("The parties agree that the obligations of confidentiality under this Agreement shall be mutual, and each party shall owe to the other the same duties in respect of information received from the other.", ["confidentiality"]),
    ("The Service Provider shall not, without the prior written consent of the Company, make any public announcement or issue any press release referring to this Agreement or to the Company's name, logo or trade marks.", ["confidentiality", "ip_ownership_licence"]),
    ("The Receiving Party acknowledges that any unauthorised disclosure of Confidential Information would cause irreparable harm for which damages may not be an adequate remedy, and that the Disclosing Party shall be entitled to seek injunctive relief.", ["confidentiality"]),
    ("All personal data shared under this Agreement shall be processed only for the purposes of this Agreement and in accordance with applicable Indian data protection law, and shall not be transferred outside India without prior written approval.", ["confidentiality"]),
    ("The Vendor shall ensure that its personnel execute individual non-disclosure undertakings in the form set out in Annexure C prior to being granted access to the Company's premises or systems.", ["confidentiality"]),
    ("The obligations under this Clause shall continue in perpetuity notwithstanding the expiry or earlier termination of this Agreement, and shall bind the successors and permitted assigns of the Receiving Party.", ["confidentiality"]),
    ("Confidential Information shall mean all information disclosed by either party, whether orally, in writing or in any other form, which is designated as confidential or which by its nature ought reasonably to be regarded as confidential.", ["confidentiality", "parties_definitions"]),

    # ================================================================
    # dispute_arbitration — thin in CUAD
    # ================================================================
    ("Any dispute or difference arising out of or in connection with this Agreement shall be referred to arbitration by a sole arbitrator appointed by mutual consent, in accordance with the Arbitration and Conciliation Act, 1996. The seat of arbitration shall be New Delhi and the proceedings shall be conducted in English.", ["dispute_arbitration"]),
    ("Before referring any dispute to arbitration, the parties shall attempt in good faith to resolve the same through discussion between their respective authorised representatives for a period of thirty days from the date on which the dispute is first notified.", ["dispute_arbitration"]),
    ("The arbitral tribunal shall consist of three arbitrators, one to be appointed by each party and the third, who shall act as the presiding arbitrator, to be appointed by the two arbitrators so appointed.", ["dispute_arbitration"]),
    ("The award of the arbitrator shall be final and binding on the parties, and the costs of the arbitration shall be borne as directed in the award.", ["dispute_arbitration"]),
    ("Notwithstanding the reference of any dispute to arbitration, the Service Provider shall continue to perform its obligations under this Agreement and the Company shall continue to pay all undisputed amounts as they fall due.", ["dispute_arbitration"]),
    ("The parties agree to attempt conciliation under Part III of the Arbitration and Conciliation Act, 1996 before invoking the arbitration clause, and such conciliation shall be concluded within sixty days.", ["dispute_arbitration"]),
    ("Any dispute relating to the quantum of liquidated damages shall be referred to a technical expert appointed jointly by the parties, whose determination shall be final in respect of questions of fact.", ["dispute_arbitration"]),
    ("Nothing in this Clause shall preclude either party from applying to a court of competent jurisdiction for interim or interlocutory relief under section 9 of the Arbitration and Conciliation Act, 1996.", ["dispute_arbitration"]),
    ("The seat and venue of arbitration shall be Mumbai. The arbitration shall be administered by the Mumbai Centre for International Arbitration in accordance with its rules then in force.", ["dispute_arbitration"]),
    ("Disputes arising hereunder shall be referred to arbitration in Singapore under the rules of the Singapore International Arbitration Centre, and the law governing the arbitration agreement shall be the law of Singapore.", ["dispute_arbitration"]),
    ("The parties waive any right of appeal against the arbitral award to the fullest extent permitted by law, and agree that the award may be enforced in any court having jurisdiction over the assets of the party against whom it is made.", ["dispute_arbitration"]),
    ("Each party shall bear its own costs of the pre-arbitral negotiation process, and the fees of the conciliator shall be shared equally between the parties.", ["dispute_arbitration"]),

    # ================================================================
    # force_majeure — thin in CUAD
    # ================================================================
    ("Neither party shall be liable for any failure or delay in performance of its obligations to the extent such failure arises from any act of God, flood, cyclone, earthquake, epidemic or pandemic, war, riot, strike, lockout or any restriction imposed by any government authority, provided that the affected party notifies the other within seven days of the occurrence.", ["force_majeure"]),
    ("Upon the occurrence of a Force Majeure Event, the obligations of the affected party shall be suspended for the duration of the event, and the time for performance shall be extended by a corresponding period.", ["force_majeure"]),
    ("If a Force Majeure Event continues for a continuous period exceeding ninety days, either party may terminate this Agreement by written notice without liability, save for obligations accrued prior to the date of such notice.", ["force_majeure", "termination_cause_cure"]),
    ("The affected party shall use all reasonable endeavours to mitigate the effects of the Force Majeure Event and shall resume performance of its obligations as soon as reasonably practicable after the event ceases.", ["force_majeure"]),
    ("A shortage of labour or raw materials, or an increase in the cost of performance, shall not by itself constitute a Force Majeure Event unless caused by an event otherwise falling within this Clause.", ["force_majeure"]),
    ("Failure to make payment of any amount due under this Agreement shall not be excused by a Force Majeure Event, save where the banking system of the country of remittance is itself rendered inoperative.", ["force_majeure", "payment_terms"]),
    ("The party claiming the benefit of this Clause shall furnish a certificate from the local authority or chamber of commerce evidencing the occurrence and duration of the Force Majeure Event.", ["force_majeure"]),
    ("Any disruption arising from a lockdown, curfew or movement restriction imposed under the Disaster Management Act, 2005 shall be treated as a Force Majeure Event for the purposes of this Agreement.", ["force_majeure"]),
    ("Neither party shall be entitled to claim any compensation, damages or additional cost from the other on account of a Force Majeure Event, and each party shall bear its own losses arising therefrom.", ["force_majeure", "limitation_of_liability"]),
    ("Force Majeure Event shall mean any event beyond the reasonable control of the affected party which could not have been prevented or avoided by the exercise of reasonable diligence.", ["force_majeure", "parties_definitions"]),

    # ================================================================
    # indemnity — thin in CUAD
    # ================================================================
    ("The Service Provider shall indemnify and hold harmless the Company against all claims, demands, losses and expenses arising out of any breach of statutory obligation by the Service Provider under the Employees' Provident Funds and Miscellaneous Provisions Act, 1952 or the Payment of Gratuity Act, 1972 in respect of its personnel deployed hereunder.", ["indemnity"]),
    ("Each party shall indemnify the other against any loss or damage to property or injury to persons caused by the negligence or wilful misconduct of its own employees or agents.", ["indemnity"]),
    ("The Supplier shall indemnify the Buyer against any claim that the Goods, or their use by the Buyer, infringe the intellectual property rights of any third party, and shall at its own cost defend any such claim.", ["indemnity", "ip_ownership_licence"]),
    ("The indemnity under this Clause shall be subject to the indemnified party giving prompt written notice of the claim, permitting the indemnifying party to control the defence, and providing reasonable cooperation at the indemnifying party's cost.", ["indemnity"]),
    ("The Contractor shall indemnify the Employer against any claim, penalty or prosecution under the Contract Labour (Regulation and Abolition) Act, 1970 arising from the deployment of contract labour by the Contractor.", ["indemnity"]),
    ("The indemnity obligations under this Agreement shall survive the expiry or termination hereof and shall not be limited by any limitation of liability contained in Clause 11.", ["indemnity", "limitation_of_liability"]),
    ("The Company shall not be liable to indemnify the Service Provider in respect of any claim arising from instructions given by the Company which the Service Provider ought reasonably to have identified as unlawful.", ["indemnity"]),
    ("The Vendor shall indemnify the Company for all losses suffered by reason of any representation or warranty given by the Vendor under Clause 8 being found to be untrue or misleading in any material respect.", ["indemnity", "warranties"]),
    ("The indemnifying party shall not settle or compromise any claim in a manner that imposes any non-monetary obligation on the indemnified party without that party's prior written consent.", ["indemnity"]),
    ("The Supplier shall indemnify, defend and hold harmless the Buyer, its directors, officers and employees against any and all claims, losses, damages, liabilities, costs and expenses, including loss of profits and consequential damages, arising out of or in connection with the supply of the Goods.", ["indemnity"]),
    ("Neither party shall be required to indemnify the other in respect of any loss to the extent that such loss is caused or contributed to by the act, omission or default of the party claiming the indemnity.", ["indemnity"]),
    ("The Service Provider's aggregate liability under the indemnity in this Clause shall not exceed twice the total charges paid under this Agreement in the twelve months preceding the claim.", ["indemnity", "limitation_of_liability"]),

    # ================================================================
    # payment_terms
    # ================================================================
    ("The consideration payable for the Services shall be as set out in Schedule 1 and shall be inclusive of all costs, charges and expenses incurred by the Service Provider in the performance of the Services, save as expressly provided otherwise.", ["payment_terms"]),
    ("The Buyer shall pay a mobilisation advance equivalent to ten percent of the contract value against submission of an irrevocable bank guarantee of equal amount issued by a scheduled commercial bank.", ["payment_terms"]),
    ("Payment shall be made by electronic transfer to the bank account notified by the Supplier in writing. The Supplier shall bear any charges levied by its own bank.", ["payment_terms"]),
    ("The Company shall retain five percent of each invoice value as retention money, which shall be released upon satisfactory completion of the defect liability period.", ["payment_terms", "warranties"]),
    ("The rates set out in Schedule 1 shall remain firm for the initial period of twelve months and shall thereafter be subject to revision by mutual written agreement, such revision not to exceed the increase in the Wholesale Price Index.", ["payment_terms"]),
    ("The Supplier shall submit, along with each invoice, a certificate confirming payment of wages to all workmen deployed during the relevant period, failing which the Company may withhold payment.", ["payment_terms", "audit_compliance"]),
    ("The Buyer guarantees a minimum offtake of five thousand units per annum, and shall pay for any shortfall at eighty percent of the applicable unit rate.", ["payment_terms"]),
    ("The Company reserves the right to revise the price of any Goods upon intimation to the Supplier, and the revised price shall apply to all purchase orders placed thereafter.", ["payment_terms"]),
    ("All payments under this Agreement shall be made in Indian Rupees, and any exchange rate fluctuation in respect of imported components shall be to the account of the Supplier.", ["payment_terms"]),
    ("The Service Provider shall not be entitled to any payment for Services rendered beyond the scope set out in Schedule 1 unless the same have been authorised in advance by a written change order.", ["payment_terms"]),
    ("The Company may set off against any sum payable to the Supplier any amount owed by the Supplier to the Company under this or any other agreement between the parties.", ["payment_terms"]),
    ("Invoices shall be raised only after acceptance of the Goods by the Company's quality inspection team, and the date of acceptance shall be the reference date for computing the payment period.", ["payment_terms"]),

    # ================================================================
    # limitation_of_liability
    # ================================================================
    ("Notwithstanding anything to the contrary, the aggregate liability of either party under or in connection with this Agreement, whether in contract, tort or otherwise, shall not exceed the total charges paid or payable by the Company during the twelve months immediately preceding the event giving rise to the claim.", ["limitation_of_liability"]),
    ("In no event shall either party be liable to the other for any indirect, incidental, special or consequential loss, including loss of profit, loss of revenue, loss of business opportunity or loss of goodwill, however arising.", ["limitation_of_liability"]),
    ("The limitations of liability in this Clause shall not apply in respect of liability for death or personal injury caused by negligence, for fraud or fraudulent misrepresentation, or for any liability which cannot lawfully be limited.", ["limitation_of_liability"]),
    ("The Supplier shall be liable for all direct and indirect losses suffered by the Buyer arising from any defect in the Goods or any delay in delivery.", ["limitation_of_liability"]),
    ("The liability of the Service Provider for any delay in performance shall be limited to liquidated damages at the rate of half a percent of the contract value per week of delay, subject to an overall cap of five percent.", ["limitation_of_liability", "payment_terms"]),
    ("The Company's liability in respect of any claim shall be reduced to the extent that the loss was caused or increased by the Supplier's failure to mitigate.", ["limitation_of_liability"]),
    ("Each party acknowledges that the limitations and exclusions of liability in this Agreement are reasonable having regard to the consideration payable, and that it has had the opportunity to obtain independent advice.", ["limitation_of_liability"]),
    ("No claim shall be brought by either party under this Agreement more than eighteen months after the party bringing the claim became aware, or ought reasonably to have become aware, of the circumstances giving rise to it.", ["limitation_of_liability"]),

    # ================================================================
    # governing_law
    # ================================================================
    ("This Agreement shall be governed by and construed in accordance with the laws of India. Subject to the arbitration clause above, the courts at Bengaluru shall have exclusive jurisdiction over any matter arising hereunder.", ["governing_law"]),
    ("This Agreement shall be governed by the laws of India, and the parties submit to the non-exclusive jurisdiction of the courts at Chennai.", ["governing_law"]),
    ("The construction, validity and performance of this Agreement shall be governed by the laws of the State of Delaware, and the courts of Delaware shall have exclusive jurisdiction.", ["governing_law"]),
    ("Nothing in this Clause shall limit the right of either party to seek relief from a court having jurisdiction over the location of the assets in respect of which relief is sought.", ["governing_law"]),
    ("This Agreement shall be governed by Indian law. Any dispute shall be subject to the exclusive jurisdiction of the courts at Mumbai, and the parties waive any objection on the ground of forum non conveniens.", ["governing_law"]),
    ("The parties agree that the United Nations Convention on Contracts for the International Sale of Goods shall not apply to this Agreement.", ["governing_law"]),
    ("Stamp duty payable on this Agreement shall be borne equally by the parties, and the original executed counterpart shall be retained by the Company.", ["governing_law", "notices_misc"]),

    # ================================================================
    # renewal_auto_renewal
    # ================================================================
    ("This Agreement shall come into force on the Effective Date and shall remain valid for an initial period of two (2) years, and shall thereafter stand automatically renewed for successive periods of one (1) year each, unless either party gives not less than sixty (60) days prior written notice of its intention not to renew.", ["term_effective_date", "renewal_auto_renewal"]),
    ("This Agreement shall automatically renew for successive periods of twelve months at the end of the initial term. The Agreement shall be deemed renewed unless written notice is given.", ["renewal_auto_renewal"]),
    ("Renewal of this Agreement shall be subject to satisfactory performance review and to the parties agreeing revised commercial terms not later than thirty days prior to the expiry of the then-current term.", ["renewal_auto_renewal"]),
    ("Upon renewal, the charges payable shall stand escalated by five percent over the charges applicable in the immediately preceding term, unless otherwise agreed in writing.", ["renewal_auto_renewal", "payment_terms"]),
    ("The Company shall have the sole option, exercisable by written notice, to extend this Agreement for two further terms of one year each on the same terms and conditions.", ["renewal_auto_renewal"]),
    ("Notice of non-renewal must be served at least one hundred and eighty days before the expiry of the current term, failing which the Agreement shall renew for a further full term.", ["renewal_auto_renewal"]),
    ("This Agreement shall not be renewed by implication, and continuation of the Services beyond the expiry of the term shall not constitute a renewal or extension.", ["renewal_auto_renewal"]),

    # ================================================================
    # termination_convenience
    # ================================================================
    ("The Company may terminate this Agreement at any time without assigning any reason and without liability to the Service Provider.", ["termination_convenience"]),
    ("Either party may terminate this Agreement for convenience by giving the other party ninety (90) days prior written notice, without the requirement to assign any reason.", ["termination_convenience"]),
    ("The Buyer may terminate any purchase order placed hereunder for convenience, in which event the Buyer shall pay for Goods already despatched and reimburse the Supplier's documented work-in-progress costs.", ["termination_convenience", "payment_terms"]),
    ("The Company may terminate this Agreement at its sole discretion upon thirty days notice. The Service Provider shall have no corresponding right of termination during the initial term.", ["termination_convenience"]),
    ("On termination for convenience, the Service Provider shall be entitled to charges for Services rendered up to the effective date of termination but to no further compensation of any nature.", ["termination_convenience", "payment_terms"]),
    ("Termination for convenience shall not relieve either party of obligations which expressly or by implication are intended to survive termination, including those relating to confidentiality and indemnity.", ["termination_convenience"]),

    # ================================================================
    # ip_ownership_licence
    # ================================================================
    ("All intellectual property rights in the deliverables created specifically for the Company under this Agreement shall vest in the Company upon full payment of the applicable charges. The Vendor shall retain all rights in its pre-existing tools, libraries and methodologies, and grants the Company a non-exclusive licence to use the same solely as embedded in the deliverables.", ["ip_ownership_licence"]),
    ("The Supplier hereby assigns to the Customer all right, title and interest in any and all intellectual property created, developed or used in connection with the performance of this Agreement.", ["ip_ownership_licence"]),
    ("The Licensor grants to the Licensee a non-exclusive, non-transferable licence to use the Software within India solely for its internal business purposes, for the duration of this Agreement.", ["ip_ownership_licence"]),
    ("The Service Provider shall ensure that all its personnel engaged on the project execute assignments of copyright in favour of the Company in compliance with section 19 of the Copyright Act, 1957.", ["ip_ownership_licence"]),
    ("The Company grants the Supplier a limited licence to use the Company's trade marks solely for the purpose of labelling the Goods in accordance with the Company's brand guidelines, such licence to terminate automatically on expiry of this Agreement.", ["ip_ownership_licence"]),
    ("Any improvement, modification or derivative work made to the Licensed Technology by the Licensee shall vest jointly in the parties, and neither party shall exploit the same commercially without the written consent of the other.", ["ip_ownership_licence"]),
    ("The Vendor warrants that it has obtained all necessary third-party licences and consents required for the Company's use of the deliverables, and shall furnish evidence thereof on demand.", ["ip_ownership_licence", "warranties"]),
    ("The licence granted hereunder shall be irrevocable and perpetual in respect of deliverables for which full payment has been received, and shall survive termination of this Agreement.", ["ip_ownership_licence"]),

    # ================================================================
    # exclusivity_noncompete
    # ================================================================
    ("The Vendor shall not, during the subsistence of this Agreement and for a period of one (1) year thereafter, directly or indirectly solicit or engage any employee of the Company, nor undertake any business competing with the Company within the territory, it being acknowledged that the enforceability of such restriction is subject to section 27 of the Indian Contract Act, 1872.", ["exclusivity_noncompete"]),
    ("The Supplier shall supply the Goods exclusively to the Company within the State of Tamil Nadu and shall not supply to any other person any goods of a similar description during the term of this Agreement.", ["exclusivity_noncompete"]),
    ("The Distributor is appointed as the sole and exclusive distributor of the Products in the Territory, and the Principal shall not appoint any other distributor or sell directly within the Territory during the term.", ["exclusivity_noncompete"]),
    ("Neither party shall, for a period of twelve months from the date of termination, solicit for employment any person who was employed by the other party and involved in the performance of this Agreement, save in response to a general public advertisement.", ["exclusivity_noncompete"]),
    ("The exclusivity granted under this Clause is conditional upon the Distributor achieving the minimum annual purchase commitment set out in Schedule 3, and shall lapse automatically upon failure to do so.", ["exclusivity_noncompete", "payment_terms"]),
    ("The Service Provider shall be free to render similar services to other clients, provided that it does not thereby place itself in a position of conflict with the interests of the Company.", ["exclusivity_noncompete"]),
    ("The Supplier agrees that it shall not offer to any other customer terms more favourable than those offered to the Company in respect of comparable volumes, and shall extend any such better terms to the Company.", ["exclusivity_noncompete", "payment_terms"]),

    # ================================================================
    # assignment_control
    # ================================================================
    ("The Supplier shall not assign, novate or otherwise transfer its rights or obligations under this Agreement without the prior written consent of the Company.", ["assignment_control"]),
    ("Neither party shall assign this Agreement without the prior written consent of the other, save that either party may assign to an affiliate upon written notice, provided the assignee assumes all obligations hereunder.", ["assignment_control"]),
    ("The Company may assign or transfer this Agreement, in whole or in part, to any successor in business or to any entity acquiring the whole or substantially the whole of its undertaking, without requiring the consent of the Supplier.", ["assignment_control"]),
    ("Any change in the controlling shareholding of the Service Provider shall be notified to the Company within fifteen days, and the Company may terminate this Agreement within sixty days of such notification if it reasonably objects to the new controller.", ["assignment_control", "termination_convenience"]),
    ("The Supplier shall not sub-contract the performance of any material part of its obligations without the prior written approval of the Company, and shall remain liable for the acts and omissions of any approved sub-contractor.", ["assignment_control"]),
    ("This Agreement shall be binding upon and inure to the benefit of the parties and their respective successors and permitted assigns.", ["assignment_control", "notices_misc"]),

    # ================================================================
    # warranties
    # ================================================================
    ("The Supplier represents and warrants that the Goods shall be new, of merchantable quality, free from defects in material and workmanship, and shall conform in all respects to the specifications set out in Schedule 2.", ["warranties"]),
    ("The warranty period shall be twenty-four months from the date of commissioning or thirty months from the date of despatch, whichever expires earlier.", ["warranties"]),
    ("The Service Provider warrants that the Services shall be performed with the degree of skill, care and diligence reasonably expected of a competent professional in the relevant field.", ["warranties"]),
    ("Each party represents and warrants that it is duly incorporated, has full corporate power to enter into this Agreement, and that the person executing this Agreement on its behalf is duly authorised to do so.", ["warranties", "parties_definitions"]),
    ("The Supplier warrants that it has complied and shall continue to comply with all applicable labour, environmental and anti-bribery laws in the performance of this Agreement.", ["warranties", "audit_compliance"]),
    ("Save as expressly set out in this Agreement, all warranties, conditions and terms implied by statute or common law are excluded to the fullest extent permitted by law.", ["warranties", "limitation_of_liability"]),
    ("Any Goods found to be defective during the warranty period shall be repaired or replaced by the Supplier free of cost, including all freight, insurance and incidental charges, within thirty days of intimation.", ["warranties"]),

    # ================================================================
    # audit_compliance
    # ================================================================
    ("The Company shall be entitled, upon giving not less than seven (7) days prior written notice and not more than twice in any financial year, to depute its representatives to inspect the books of account and the premises of the Supplier insofar as they relate to the performance of this Agreement, during normal business hours.", ["audit_compliance"]),
    ("The Customer may at any time and without notice inspect the books and records of the Supplier relating to this Agreement and may require unrestricted access to the Supplier's premises.", ["audit_compliance"]),
    ("The Supplier shall maintain complete and accurate records relating to this Agreement for a period of eight years from the date of the relevant transaction, in accordance with the Companies Act, 2013.", ["audit_compliance"]),
    ("The Service Provider shall comply with the Company's Code of Conduct and anti-bribery policy, and shall permit the Company to audit such compliance on reasonable notice.", ["audit_compliance"]),
    ("The Supplier shall obtain and maintain throughout the term all licences, registrations and approvals required under applicable law for the performance of its obligations, and shall produce the same for inspection on demand.", ["audit_compliance", "warranties"]),
    ("Any discrepancy revealed by an audit which results in an overpayment by the Company shall be refunded by the Supplier within thirty days of notification, together with interest at twelve percent per annum.", ["audit_compliance", "payment_terms"]),

    # ================================================================
    # insurance
    # ================================================================
    ("The Supplier shall maintain a policy of insurance with coverage of not less than the amount specified in Schedule 2 throughout the term of this Agreement, and shall name the Company as an additional insured.", ["insurance"]),
    ("The Contractor shall take out and maintain workmen's compensation insurance in respect of all personnel deployed at the site, in accordance with the Employee's Compensation Act, 1923.", ["insurance"]),
    ("The Service Provider shall maintain professional indemnity insurance of not less than rupees two crore per occurrence, and shall furnish a certificate of currency annually.", ["insurance", "indemnity"]),
    ("Transit insurance in respect of the Goods shall be arranged by the Supplier up to the point of delivery, and the risk in the Goods shall pass to the Buyer upon delivery at the designated site.", ["insurance"]),
    ("Failure by the Supplier to maintain the insurances required under this Clause shall constitute a material breach of this Agreement, and the Company may effect such insurance and recover the premium from the Supplier.", ["insurance", "termination_cause_cure"]),

    # ================================================================
    # notices_misc
    # ================================================================
    ("Any notice required to be given under this Agreement shall be in writing and shall be deemed to have been duly served if sent by registered post with acknowledgement due or by courier to the address of the other party first mentioned above, or by electronic mail to the designated address, with a confirmatory copy by post.", ["notices_misc"]),
    ("This Agreement constitutes the entire agreement between the parties in respect of its subject matter and supersedes all prior negotiations, representations and understandings, whether oral or written.", ["notices_misc"]),
    ("If any provision of this Agreement is held to be invalid or unenforceable, such provision shall be severed and the remaining provisions shall continue in full force and effect.", ["notices_misc"]),
    ("No failure or delay by either party in exercising any right under this Agreement shall operate as a waiver of that right, nor shall any single or partial exercise preclude any further exercise.", ["notices_misc"]),
    ("This Agreement may be executed in counterparts, each of which shall be deemed an original, and the counterparts together shall constitute one and the same instrument.", ["notices_misc"]),
    ("No amendment or variation of this Agreement shall be effective unless made in writing and signed by the authorised representatives of both parties.", ["notices_misc"]),
    ("Nothing in this Agreement shall constitute a partnership, joint venture or relationship of principal and agent between the parties, and neither party shall hold itself out as having authority to bind the other.", ["notices_misc", "parties_definitions"]),

    # ================================================================
    # parties_definitions
    # ================================================================
    ("This Agreement is made on 1 April 2026 between Sunrise Components Private Limited, a company incorporated under the Companies Act, 2013, having its registered office at Coimbatore, Tamil Nadu (hereinafter the Supplier), and Meridian Industries Limited, having its registered office at Mumbai, Maharashtra (hereinafter the Customer).", ["parties_definitions"]),
    ("Goods shall mean the components, parts and assemblies described in Schedule 1, together with all packaging, documentation and spares supplied therewith.", ["parties_definitions"]),
    ("Affiliate shall mean, in relation to a party, any entity which directly or indirectly controls, is controlled by, or is under common control with that party, where control means the holding of more than fifty percent of the voting share capital.", ["parties_definitions"]),
    ("In this Agreement, words importing the singular include the plural and vice versa, and references to a statute include that statute as amended or re-enacted from time to time.", ["parties_definitions"]),
    ("Business Day shall mean a day other than a Saturday, Sunday or a public holiday notified under the Negotiable Instruments Act, 1881 in the State of Maharashtra.", ["parties_definitions"]),
    ("The Schedules and Annexures to this Agreement form an integral part hereof, and in the event of any inconsistency between the body of this Agreement and a Schedule, the body shall prevail.", ["parties_definitions", "notices_misc"]),

    # ================================================================
    # term_effective_date
    # ================================================================
    ("This Agreement shall commence on the Effective Date and shall remain in force for an initial period of twenty-four months unless terminated earlier in accordance with its terms.", ["term_effective_date"]),
    ("The Effective Date of this Agreement shall be the date on which the last of the parties executes the same, notwithstanding the date first written above.", ["term_effective_date"]),
    ("This Agreement shall be deemed to have come into effect retrospectively from 1 January 2026, and all Services rendered on and from that date shall be governed by its terms.", ["term_effective_date"]),
    ("The term of this Agreement shall expire on 31 March 2029 unless extended by mutual written agreement of the parties.", ["term_effective_date"]),
    ("Notwithstanding the expiry of the term, those provisions which by their nature are intended to survive, including Clauses 9, 10 and 14, shall continue in force.", ["term_effective_date", "notices_misc"]),
    ("Performance of the Services shall commence within fifteen days of the Effective Date, and the Service Provider shall submit a mobilisation plan prior to such commencement.", ["term_effective_date"]),

    # ================================================================
    # Negatives — real contract text carrying no clause type from the
    # taxonomy. A model that labels everything would score well without
    # these, so the set needs them.
    # ================================================================
    ("The headings in this Agreement are for convenience of reference only and shall not affect the construction or interpretation of any provision.", []),
    ("IN WITNESS WHEREOF the parties have executed this Agreement on the date first written above through their duly authorised representatives.", []),
    ("For Sunrise Components Private Limited: Name, Designation, Signature, Date. For Meridian Industries Limited: Name, Designation, Signature, Date.", []),
    ("Schedule 1 — Description of Goods. Schedule 2 — Technical Specifications. Schedule 3 — Minimum Purchase Commitments. Annexure A — Form of Bank Guarantee.", []),
    ("Item | Description | Unit | Quantity | Rate | Amount. 1 | Bearing assembly, 40mm | Nos | 500 | 1,250 | 6,25,000.", []),
    ("The Supplier shall deliver the Goods at the Company's warehouse at Plot 14, SIPCOT Industrial Estate, Hosur, between 9:00 a.m. and 5:00 p.m. on any Business Day.", []),
    ("Page 7 of 23", []),
    ("The Company's authorised representative for the purposes of day-to-day coordination shall be the Purchase Manager, and the Supplier's shall be its Regional Sales Head.", []),
    ("This page has been intentionally left blank.", []),
    ("Table of Contents. 1. Definitions. 2. Term. 3. Scope of Supply. 4. Price and Payment. 5. Delivery. 6. Inspection.", []),
]


def main() -> None:
    rows = [
        {"source": SYNTHETIC, "text": " ".join(text.split()), "labels": sorted(labels)}
        for text, labels in CLAUSES
    ]

    # Validate before writing: a typo in a label key would silently become a
    # class the model can never be scored against.
    unknown = {
        label for row in rows for label in row["labels"] if label not in LABEL_KEYS
    }
    if unknown:
        raise SystemExit(f"unknown label keys: {sorted(unknown)}")

    duplicates = [t for t, n in Counter(r["text"] for r in rows).items() if n > 1]
    if duplicates:
        raise SystemExit(f"{len(duplicates)} duplicate clause(s); first: {duplicates[0][:80]}")

    OUTPUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    tally = Counter(label for row in rows for label in row["labels"])
    negatives = sum(1 for row in rows if not row["labels"])

    print(f"Wrote {len(rows)} clauses to {OUTPUT.relative_to(REPO_ROOT)}")
    print(f"  positives: {len(rows) - negatives}   negatives: {negatives}")
    print(f"  label assignments: {sum(tally.values())}")
    print()
    print(f"{'class':<28} {'count':>5}")
    print("-" * 35)

    missing: list[str] = []
    for key in LABEL_KEYS:
        count = tally.get(key, 0)
        if count == 0:
            missing.append(key)
        print(f"{key:<28} {count:>5}")

    if missing:
        print()
        print(f"WARNING: {len(missing)} class(es) have no examples: {missing}")

    target = 150
    if len(rows) < target:
        print()
        print(f"NOTE: {len(rows)} clauses; TBD-5 target is {target}-200.")


if __name__ == "__main__":
    main()
