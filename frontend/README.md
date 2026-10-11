# Frontend

Not yet scaffolded — this is Phase 6 work (see `PLAN.md` §6). The placeholder
exists so the repository layout matches the plan from the start.

## Planned stack

React + TypeScript on Vite, Tailwind CSS with shadcn/ui components, per the
SRS §2.5 constraint that the frontend framework is React.

## Screens (SRS §3.1, TBD-6)

| Screen | Requirements |
|---|---|
| Upload | Drag-and-drop, client-side size validation against the 10 MB cap (REQ-1.2) |
| Processing | Polls `GET /api/v1/contracts/{id}/status`, renders the pipeline stage |
| Report | Clause list, colour-coded green/yellow/red, expandable explanation panels (REQ-5.1, REQ-5.2), summary header (REQ-5.4), export button (REQ-5.3) |
| Dashboard | Contract history with date and risk summary, contracts-reviewed-over-time (REQ-6.3, REQ-6.4) |
| Auth | Register and login (REQ-6.1) |

## Two things the UI must get right

**The disclaimer is a requirement, not decoration.** SRS §5.2 and §5.5 require a
persistent statement that output is not legal advice, and §5.2 forbids asserting
certainty in a risk label. Both belong in the component layer from the first
commit, not bolted on before the demo.

**Plain language throughout.** The primary user class in SRS §2.3 is a business
owner with no legal background. Legal jargon in the UI defeats the entire point
of the product — see the Usability attribute in §5.4.

## When scaffolding

The processing screen reads `ContractStatus` values straight from the API
(`uploaded`, `extracting`, `segmenting`, `classifying`, `scoring`, `complete`,
`failed`). Those strings are user-facing; keep the UI copy aligned with the
enum in `backend/app/db/models.py`.
