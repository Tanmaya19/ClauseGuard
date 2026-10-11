"""PDF report rendering with reportlab (REQ-5.3).

reportlab rather than WeasyPrint: WeasyPrint needs GTK/Pango system libraries
that do not install cleanly on Windows, and this project is developed there.
reportlab is pure Python and renders identically on Windows and in the Linux
container. See docs/ADRs/0002-reportlab-over-weasyprint.md.

The PDF deliberately mirrors the web report rather than being a terse export:
the SRS audience (SRS 2.3) is a business owner who is likely to print this and
take it into a negotiation, so the explanations travel with the clauses.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.db.models import RiskLevel
from app.schemas.contracts import ReportResponse

# REQ-5.2: the same green/amber/red scale as the web view. Darkened from the
# screen palette so the text on them stays legible in greyscale print.
RISK_COLOURS: dict[str, colors.Color] = {
    RiskLevel.SAFE.value: colors.HexColor("#1B7F4B"),
    RiskLevel.CAUTION.value: colors.HexColor("#B26A00"),
    RiskLevel.HIGH_RISK.value: colors.HexColor("#B3261E"),
    RiskLevel.UNASSESSABLE.value: colors.HexColor("#5F6368"),
}
RISK_TINTS: dict[str, colors.Color] = {
    RiskLevel.SAFE.value: colors.HexColor("#EAF5EE"),
    RiskLevel.CAUTION.value: colors.HexColor("#FDF3E3"),
    RiskLevel.HIGH_RISK.value: colors.HexColor("#FBEAE8"),
    RiskLevel.UNASSESSABLE.value: colors.HexColor("#F1F3F4"),
}
RISK_LABELS = {
    RiskLevel.SAFE.value: "Looks standard",
    RiskLevel.CAUTION.value: "Worth a look",
    RiskLevel.HIGH_RISK.value: "Needs attention",
    RiskLevel.UNASSESSABLE.value: "Not assessed",
}

MAX_CLAUSE_CHARS_IN_PDF = 2600


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "CGTitle", parent=base["Title"], fontSize=20, spaceAfter=2 * mm
        ),
        "subtitle": ParagraphStyle(
            "CGSubtitle",
            parent=base["Normal"],
            fontSize=9.5,
            textColor=colors.HexColor("#5F6368"),
            alignment=TA_CENTER,
            spaceAfter=6 * mm,
        ),
        "h2": ParagraphStyle(
            "CGH2", parent=base["Heading2"], fontSize=13, spaceBefore=5 * mm, spaceAfter=2 * mm
        ),
        "clause_heading": ParagraphStyle(
            "CGClauseHeading", parent=base["Heading3"], fontSize=11, spaceAfter=1 * mm
        ),
        "body": ParagraphStyle(
            "CGBody", parent=base["BodyText"], fontSize=9, leading=12.5, alignment=TA_JUSTIFY
        ),
        "clause_text": ParagraphStyle(
            "CGClauseText",
            parent=base["BodyText"],
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#202124"),
            alignment=TA_JUSTIFY,
            leftIndent=3 * mm,
            rightIndent=3 * mm,
        ),
        "why": ParagraphStyle(
            "CGWhy", parent=base["BodyText"], fontSize=9, leading=12.5, leftIndent=3 * mm
        ),
        "meta": ParagraphStyle(
            "CGMeta",
            parent=base["Normal"],
            fontSize=7.5,
            textColor=colors.HexColor("#5F6368"),
        ),
        "disclaimer": ParagraphStyle(
            "CGDisclaimer",
            parent=base["BodyText"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#3C4043"),
            alignment=TA_JUSTIFY,
        ),
    }


def _escape(text: str) -> str:
    """reportlab Paragraph parses a mini-HTML, so contract text must be escaped.

    Contracts contain ``&`` and occasionally ``<`` (as in "< 30 days"), either
    of which would otherwise raise a parse error mid-render.
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


class _ReportDoc(BaseDocTemplate):
    """Document template that stamps the disclaimer on every page footer.

    SRS 5.2 and 5.5 require the disclaimer to be *persistent*. A single page
    of front matter would not survive someone printing page 4 and taking it
    into a meeting, so it goes in the running footer.
    """

    def __init__(self, buffer: io.BytesIO, title: str) -> None:
        super().__init__(
            buffer,
            pagesize=A4,
            title=title,
            author="ClauseGuard",
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=20 * mm,
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="body",
        )
        self.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=self._footer)])

    @staticmethod
    def _footer(canvas, doc) -> None:  # noqa: ANN001 — reportlab callback signature
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#80868B"))
        canvas.drawString(
            18 * mm,
            12 * mm,
            "ClauseGuard automated triage — not legal advice. Have significant "
            "contracts reviewed by a licensed professional.",
        )
        canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Page {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#DADCE0"))
        canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
        canvas.restoreState()


def _summary_table(report: ReportResponse, style: ParagraphStyle) -> Table:
    counts = report.summary.get("risk_counts", {})
    rows = [["", "Clauses", ""]]

    for level in (RiskLevel.HIGH_RISK, RiskLevel.CAUTION, RiskLevel.SAFE, RiskLevel.UNASSESSABLE):
        count = counts.get(level.value, 0)
        if count == 0 and level is RiskLevel.UNASSESSABLE:
            continue
        rows.append(
            [
                Paragraph(f"<b>{RISK_LABELS[level.value]}</b>", style),
                str(count),
                Paragraph(_level_blurb(level), style),
            ]
        )

    table = Table(rows[1:], colWidths=[38 * mm, 16 * mm, None], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#E8EAED")),
            ]
            + [
                ("TEXTCOLOR", (0, i), (0, i), RISK_COLOURS[level.value])
                for i, level in enumerate(
                    [
                        lv
                        for lv in (
                            RiskLevel.HIGH_RISK,
                            RiskLevel.CAUTION,
                            RiskLevel.SAFE,
                            RiskLevel.UNASSESSABLE,
                        )
                        if counts.get(lv.value, 0) or lv is not RiskLevel.UNASSESSABLE
                    ]
                )
            ]
        )
    )
    return table


def _level_blurb(level: RiskLevel) -> str:
    return {
        RiskLevel.HIGH_RISK: "Clauses we would raise before signing.",
        RiskLevel.CAUTION: "Clauses worth understanding, possibly negotiable.",
        RiskLevel.SAFE: "Nothing in our rubric flagged these.",
        RiskLevel.UNASSESSABLE: "We could not identify the clause type confidently.",
    }[level]


def _clause_block(clause, styles: dict[str, ParagraphStyle]) -> KeepTogether:
    risk = clause.risk.value
    heading = clause.heading or f"Clause {clause.ordinal + 1}"
    types = ", ".join(p.display for p in clause.predictions) or "Uncategorized"

    banner = Table(
        [
            [
                Paragraph(f"<b>{_escape(heading)}</b>", styles["clause_heading"]),
                Paragraph(
                    f'<para align="right"><b>{RISK_LABELS[risk]}</b></para>',
                    styles["clause_heading"],
                ),
            ]
        ],
        colWidths=[None, 36 * mm],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), RISK_TINTS[risk]),
                ("TEXTCOLOR", (1, 0), (1, 0), RISK_COLOURS[risk]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBEFORE", (0, 0), (0, -1), 2.2, RISK_COLOURS[risk]),
            ]
        )
    )

    text = clause.text
    if len(text) > MAX_CLAUSE_CHARS_IN_PDF:
        text = text[:MAX_CLAUSE_CHARS_IN_PDF] + " […truncated in this export]"

    flow = [
        banner,
        Spacer(1, 1.5 * mm),
        Paragraph(f"<i>Type:</i> {_escape(types)}", styles["meta"]),
        Spacer(1, 1 * mm),
        Paragraph(_escape(text), styles["clause_text"]),
    ]

    if clause.findings:
        flow.append(Spacer(1, 1.5 * mm))
        flow.append(Paragraph("<b>Why this is flagged</b>", styles["meta"]))
        for finding in clause.findings:
            flow.append(
                Paragraph(
                    f"• {_escape(finding.explanation)}", styles["why"]
                )
            )

    if clause.needs_manual_review:
        flow.append(Spacer(1, 1 * mm))
        flow.append(
            Paragraph(
                "<i>We could not cleanly separate this clause, so read it in the "
                "original document as well.</i>",
                styles["meta"],
            )
        )

    flow.append(Spacer(1, 4 * mm))
    # KeepTogether stops a clause being split from its own explanation across a
    # page break, which would make the report hard to follow in print.
    return KeepTogether(flow)


def render_report_pdf(report: ReportResponse) -> bytes:
    styles = _styles()
    buffer = io.BytesIO()
    doc = _ReportDoc(buffer, title=f"ClauseGuard report — {report.filename}")

    flow: list = [
        Paragraph("Contract Risk Report", styles["title"]),
        Paragraph(
            f"{_escape(report.filename)} &nbsp;·&nbsp; generated "
            f"{report.generated_at.strftime('%d %B %Y')}",
            styles["subtitle"],
        ),
    ]

    # --- Disclaimer up front, as well as in the footer -----------------
    disclaimer = Table([[Paragraph(report.disclaimer, styles["disclaimer"])]], colWidths=[None])
    disclaimer.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DADCE0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flow += [disclaimer, Spacer(1, 5 * mm)]

    # --- Summary (REQ-5.4) ---------------------------------------------
    summary = report.summary
    flow.append(Paragraph("At a glance", styles["h2"]))
    flow.append(
        Paragraph(
            f"We split this contract into <b>{summary.get('clause_count', 0)}</b> clauses "
            f"and checked each against rubric version <b>{report.rubric_version}</b>.",
            styles["body"],
        )
    )
    flow += [Spacer(1, 2 * mm), _summary_table(report, styles["body"]), Spacer(1, 3 * mm)]

    # --- Contract-level findings ---------------------------------------
    contract_findings = summary.get("contract_findings") or []
    if contract_findings:
        flow.append(Paragraph("Missing from this contract", styles["h2"]))
        flow.append(
            Paragraph(
                "These are protections we expected to find and could not:", styles["body"]
            )
        )
        for finding in contract_findings:
            flow.append(Spacer(1, 1.5 * mm))
            flow.append(
                Paragraph(f"• {_escape(finding.get('explanation', ''))}", styles["why"])
            )
        flow.append(Spacer(1, 3 * mm))

    # --- Clause by clause (REQ-5.1) ------------------------------------
    flow.append(PageBreak())
    flow.append(Paragraph("Clause by clause", styles["h2"]))
    flow.append(Spacer(1, 2 * mm))
    flow += [_clause_block(c, styles) for c in report.clauses]

    # --- Provenance (SRS 5.5) ------------------------------------------
    flow += [
        Spacer(1, 4 * mm),
        Paragraph(
            f"Rubric version {report.rubric_version} · model {_escape(report.model_version)} · "
            f"exported {datetime.now(UTC).strftime('%d %B %Y %H:%M UTC')}",
            styles["meta"],
        ),
    ]

    doc.build(flow)
    return buffer.getvalue()
