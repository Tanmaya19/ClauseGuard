# Screens

TBD-6 deferred detailed wireframes to a separate design document. The five
screens are now implemented, so this file records what they are and where the
code lives, rather than holding mockups of software that already exists.

| Screen | Component | Requirements |
|---|---|---|
| Authentication | `frontend/src/pages/Auth.tsx` | REQ-6.1 |
| Upload | `frontend/src/pages/Upload.tsx` | REQ-1.1, REQ-1.2 (client-side size check), REQ-1.4 guidance |
| Processing | `frontend/src/pages/Processing.tsx` | SRS 3.1 live stage display; polls `/contracts/{id}/status` |
| Report | `frontend/src/pages/Report.tsx` | REQ-5.1, REQ-5.2, REQ-5.3, REQ-5.4 |
| Dashboard | `frontend/src/pages/Dashboard.tsx` | REQ-6.3, REQ-6.4 |

Shared: `components/Nav.tsx`, `components/Disclaimer.tsx` (the persistent
disclaimer SRS 5.2 requires).

## Design decisions worth knowing

**The risk palette is defined twice, deliberately.** `frontend/tailwind.config.js`
holds the web colours and `backend/app/services/reporting/pdf_renderer.py` holds
the print colours, each with a comment pointing at the other. The PDF values are
darkened so the text stays legible in greyscale print. REQ-5.2's green / amber /
red scale is the contract between them.

**Risk levels are labelled as actions, not jargon.** "Needs attention",
"Worth a look", "Looks standard", "Not assessed" — rather than
"High-Risk / Caution / Safe / Unassessable", which are the internal enum names.
SRS 2.3's primary user has no legal training, and SRS 5.4 Usability asks for
plain language in the UI.

**High-risk clauses render expanded by default.** The product exists to draw the
eye to what matters; making the user click to find it would defeat the purpose.

**Summary tiles are filters.** Clicking "Needs attention" filters the clause
list to those clauses, which is the first thing a user wants after seeing the
count.

**No charting library.** The dashboard's activity chart is ~20 lines of inline
SVG-free markup. A dozen bars is not worth 150 kB of bundle.
