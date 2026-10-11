# ADR 0002 — reportlab for PDF export, not WeasyPrint

**Status:** Accepted
**Date:** 2026-10-07
**Phase:** 7

## Context

REQ-5.3 requires the report to be exportable as a downloadable PDF, and
`PLAN.md` named WeasyPrint for the job. WeasyPrint renders HTML and CSS, which
is attractive here because the web report already exists as styled markup — in
principle the same template could serve both.

The complication is the development environment. This project is developed on
Windows, and WeasyPrint depends on GTK, Pango and Cairo as **system**
libraries. On Windows those are not pip-installable: they require a separate
GTK runtime installation, and the import fails at runtime rather than at
install time if it is missing or mismatched.

That produces a specific, bad failure mode: PDF export would work inside the
Linux container and break on the developer's own machine, so `pytest` could not
cover REQ-5.3 locally. A requirement whose tests only run in CI is a
requirement that gets broken quietly.

## Decision

Use **reportlab** and build the PDF from flowables, not from HTML.

The risk palette is duplicated between `pdf_renderer.py` and
`tailwind.config.js`, with a comment in each pointing at the other, so the
colour scale stays consistent between the web view and the export.

## Alternatives considered

**WeasyPrint as planned.** Rejected for the Windows system-dependency problem
above. Would have allowed one HTML template to serve both outputs.

**xhtml2pdf.** Pure Python and HTML-driven, so it looked like the best of both.
Rejected because its CSS support is a narrow subset — no flexbox or grid — so
the web template could not have been reused unmodified anyway, which removes
the main reason to prefer an HTML-based renderer.

**Headless Chromium print-to-PDF.** Highest fidelity, and would genuinely reuse
the real frontend. Rejected as disproportionate: it would add a browser to the
API image for one feature, roughly tripling image size, and introduce a second
runtime to manage in deployment.

## Consequences

- PDF generation works identically on Windows and in the container, so
  `tests/test_api.py::test_pdf_export` runs everywhere.
- No system packages were added to `backend/Dockerfile`, which keeps the image
  small and the build fast.
- The export layout is written in Python rather than CSS, so a change to the
  web report's appearance does not automatically carry over. The two are
  intentionally similar but separately maintained.
- Contract text must be escaped before it reaches a `Paragraph`: reportlab
  parses a mini-HTML dialect, and contracts contain `&` and occasionally `<`
  (as in "< 30 days"), either of which would raise mid-render. Handled by
  `_escape()` in `pdf_renderer.py`.
- The disclaimer is drawn in the page footer by the document template rather
  than placed in the flow once, because SRS 5.2 requires it to be *persistent*
  and a single page of front matter does not survive someone printing page 4.
