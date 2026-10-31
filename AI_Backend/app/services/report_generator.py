"""PDF Report Generator for BrandProof AI.

Generates professional, multi-page audit reports:
- Page 1: Original text with errors underlined in red, issue summary, and findings breakdown.
- Page 2: Publication-ready corrected text, AI guideline proofs, and reviewer governance checkpoint.
"""

import io
import html
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print 'Page X of Y' in footer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Footer text
        footer_left = "BrandProof AI — Brand Compliance & Language Quality Audit"
        footer_right = f"Page {self._pageNumber} of {page_count}"

        # Draw running rule above footer
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(36, 32, 612 - 36, 32)

        self.drawString(36, 20, footer_left)
        self.drawRightString(612 - 36, 20, footer_right)
        self.restoreState()


class ReportGeneratorService:
    """Service producing standardized PDF compliance reports."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        """Initializes palette and typography styles for report documents."""
        # Primary Title
        self.styles.add(ParagraphStyle(
            name="ReportTitle",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0F172A"),
        ))

        # Page 2 Subtitle
        self.styles.add(ParagraphStyle(
            name="ReportSubtitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#475569"),
        ))

        # Section Heading
        self.styles.add(ParagraphStyle(
            name="SectionHeading",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=8,
            spaceAfter=4,
        ))

        # Body Text
        self.styles.add(ParagraphStyle(
            name="ReportBody",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=14,
            textColor=colors.HexColor("#1E293B"),
        ))

        # Original content container
        self.styles.add(ParagraphStyle(
            name="OriginalContentStyle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=15,
            textColor=colors.HexColor("#0F172A"),
        ))

        # Corrected content container
        self.styles.add(ParagraphStyle(
            name="CorrectedContentStyle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=15,
            textColor=colors.HexColor("#065F46"),
        ))

        # Small meta
        self.styles.add(ParagraphStyle(
            name="MetaLabel",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#475569"),
        ))

        self.styles.add(ParagraphStyle(
            name="MetaValue",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0F172A"),
        ))

        # Table cell styles
        self.styles.add(ParagraphStyle(
            name="TableCell",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1E293B"),
        ))

        self.styles.add(ParagraphStyle(
            name="TableHead",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0F172A"),
        ))

    def _mark_errors_in_text(self, text: str, findings: List[Dict[str, Any]]) -> str:
        """Escapes the text for ReportLab Paragraph markup and formats each error

        with red color and red underline, plus an anchor footnote tag [1], [2].
        """
        if not text:
            return ""

        # First escape XML special chars
        escaped_text = html.escape(text)

        # Sort findings by length of original_text descending to avoid partial collision
        valid_findings = [f for f in findings if f.get("original_text", "").strip()]

        # Mark errors with red underline
        for idx, f in enumerate(valid_findings, start=1):
            raw_target = f.get("original_text", "").strip()
            if not raw_target:
                continue

            escaped_target = html.escape(raw_target)

            # Replacement tag: Red color + underline + footnote number
            replacement = (
                f'<font color="#DC2626"><u><b>{escaped_target}</b></u></font>'
                f'<font color="#DC2626"><sup><b>[{idx}]</b></sup></font>'
            )

            # Use regex to replace first or safe occurrence (case-insensitive fallback)
            pattern = re.compile(re.escape(escaped_target), re.IGNORECASE)
            # Replace only first occurrence per finding to avoid cascading duplicates
            escaped_text = pattern.sub(replacement, escaped_text, count=1)

        # Standardize newlines into HTML breaks
        formatted_html = escaped_text.replace("\r\n", "\n").replace("\n", "<br/><br/>")
        return formatted_html

    def generate_report_pdf(
        self,
        original_text: str,
        corrected_text: str,
        findings: List[Dict[str, Any]],
        summary: Optional[str] = None,
        title: Optional[str] = "BrandProof AI Content Audit Report",
        model_name: Optional[str] = "Gemini 3.5 Flash",
        created_at: Optional[str] = None,
        content_type: Optional[str] = None,
        brand_context: Optional[str] = None,
    ) -> bytes:
        """Generates a complete 2-page PDF audit report in memory and returns raw bytes."""
        buf = io.BytesIO()

        # Letter size: 612 x 792 pt, 36 pt (0.5 in) margins
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=42,
        )

        date_str = created_at or datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
        doc_title = title or "Marketing Content Audit Report"
        content_type_label = (content_type or "General Marketing Content").title()
        total_findings = len(findings)

        # Count severities
        sev_counts = {"high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev = str(f.get("severity") or "medium").lower()
            if "high" in sev or "crit" in sev:
                sev_counts["high"] += 1
            elif "low" in sev or "info" in sev:
                sev_counts["low"] += 1
            else:
                sev_counts["medium"] += 1

        story = []

        # ======================================================================
        # PAGE 1: ORIGINAL TEXT WITH RED UNDERLINED ERRORS & FINDINGS BREAKDOWN
        # ======================================================================

        # Header Block
        header_table_data = [
            [
                Paragraph(f"<b>{html.escape(doc_title)}</b>", self.styles["ReportTitle"]),
                Paragraph(
                    f"<b>Audit Date:</b> {html.escape(date_str)}<br/>"
                    f"<b>Model:</b> {html.escape(model_name or 'Gemini 3.5 Flash')}<br/>"
                    f"<b>Type:</b> {html.escape(content_type_label)}",
                    self.styles["MetaValue"],
                ),
            ]
        ]
        header_table = Table(header_table_data, colWidths=[360, 180])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)

        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceBefore=2, spaceAfter=8))

        # Executive Summary Callout
        summary_text = summary or (
            f"Analysis completed with {total_findings} detected issue(s). "
            f"High severity: {sev_counts['high']}, Medium: {sev_counts['medium']}, Low: {sev_counts['low']}."
        )
        summary_html = (
            f"<b>Executive Assessment:</b> {html.escape(summary_text)} "
            f"<i>(Review status: Human verification required prior to publishing)</i>"
        )
        summary_table = Table(
            [[Paragraph(summary_html, self.styles["ReportBody"])]],
            colWidths=[540],
        )
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_table)

        story.append(Spacer(1, 10))

        # Section 1: Original Content with Red Underlined Markings
        story.append(Paragraph(
            "<b>1. Original Content (Flagged Errors Underlined in Red)</b>",
            self.styles["SectionHeading"],
        ))
        story.append(Paragraph(
            "Identified grammar, spelling, compliance, and stylistic issues are highlighted below with "
            "<font color='#DC2626'><u><b>red underline markings</b></u></font> and indexed markers [1], [2]...",
            self.styles["ReportSubtitle"],
        ))
        story.append(Spacer(1, 4))

        marked_original_html = self._mark_errors_in_text(original_text, findings)
        orig_content_table = Table(
            [[Paragraph(marked_original_html, self.styles["OriginalContentStyle"])]],
            colWidths=[540],
        )
        orig_content_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF5F5")),  # Subtle warm red background
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FECACA")),        # Soft red border
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(orig_content_table)

        story.append(Spacer(1, 10))

        # Section 2: Detected Issues Table
        story.append(Paragraph("<b>2. Flagged Errors & Rule Violations</b>", self.styles["SectionHeading"]))

        if findings:
            issues_table_data = [
                [
                    Paragraph("<b>#</b>", self.styles["TableHead"]),
                    Paragraph("<b>Flagged Excerpt</b>", self.styles["TableHead"]),
                    Paragraph("<b>Category</b>", self.styles["TableHead"]),
                    Paragraph("<b>Severity</b>", self.styles["TableHead"]),
                    Paragraph("<b>Explanation & Guideline Context</b>", self.styles["TableHead"]),
                ]
            ]

            for idx, item in enumerate(findings[:8], start=1):  # Cap to fit page cleanly
                orig_snippet = str(item.get("original_text") or "").strip()
                cat_label = str(item.get("category") or "grammar").title()
                sev_raw = str(item.get("severity") or "medium").lower()
                sev_color = "#DC2626" if "high" in sev_raw else ("#D97706" if "med" in sev_raw else "#2563EB")
                explanation = str(item.get("explanation") or "").strip()

                ts_val = item.get("timestamp")
                ts_badge = f' <font color="#475569" size="7"><b>[{html.escape(str(ts_val))}]</b></font>' if ts_val else ""
                issues_table_data.append([
                    Paragraph(f"<b>[{idx}]</b>", self.styles["TableCell"]),
                    Paragraph(f'<font color="#DC2626"><u><b>{html.escape(orig_snippet)}</b></u></font>{ts_badge}', self.styles["TableCell"]),
                    Paragraph(html.escape(cat_label), self.styles["TableCell"]),
                    Paragraph(f'<font color="{sev_color}"><b>{sev_raw.upper()}</b></font>', self.styles["TableCell"]),
                    Paragraph(html.escape(explanation), self.styles["TableCell"]),
                ])

            issues_table = Table(issues_table_data, colWidths=[24, 110, 75, 55, 276])
            issues_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(issues_table)
        else:
            story.append(Paragraph(
                "<i>No errors detected. Content adheres fully to brand and language standards.</i>",
                self.styles["ReportBody"],
            ))

        # ======================================================================
        # PAGE 2: CORRECTED TEXT WITH GEMINI ANALYSIS & GUIDELINE PROOFS
        # ======================================================================
        story.append(PageBreak())

        # Page 2 Header
        p2_header_data = [
            [
                Paragraph("<b>Corrected Content & AI Guideline Proofs</b>", self.styles["ReportTitle"]),
                Paragraph(
                    f"<b>Engine:</b> {html.escape(model_name or 'Gemini 3.5 Flash')}<br/>"
                    f"<b>Status:</b> Ready for Review",
                    self.styles["MetaValue"],
                ),
            ]
        ]
        p2_header_table = Table(p2_header_data, colWidths=[380, 160])
        p2_header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(p2_header_table)

        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceBefore=2, spaceAfter=8))

        # Section 3: Final Corrected Text
        story.append(Paragraph(
            "<b>3. Publication-Ready Corrected Copy</b>",
            self.styles["SectionHeading"],
        ))
        story.append(Paragraph(
            "The revised copy below incorporates all grammatical, stylistic, and brand consistency adjustments:",
            self.styles["ReportSubtitle"],
        ))
        story.append(Spacer(1, 4))

        corrected_escaped = html.escape(corrected_text or original_text).replace("\r\n", "\n").replace("\n", "<br/><br/>")
        corrected_box_table = Table(
            [[Paragraph(corrected_escaped, self.styles["CorrectedContentStyle"])]],
            colWidths=[540],
        )
        corrected_box_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),  # Soft green background
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#86EFAC")),        # Soft green border
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(corrected_box_table)

        story.append(Spacer(1, 10))

        # Section 4: Guideline Proofs Matrix
        story.append(Paragraph(
            "<b>4. AI Guideline Proofs & Alignment Evidence</b>",
            self.styles["SectionHeading"],
        ))
        story.append(Paragraph(
            "Traceability record linking each correction directly to its approved guideline, grammar rule, or proof:",
            self.styles["ReportSubtitle"],
        ))
        story.append(Spacer(1, 4))

        proofs_table_data = [
            [
                Paragraph("<b>#</b>", self.styles["TableHead"]),
                Paragraph("<b>Flagged Excerpt</b>", self.styles["TableHead"]),
                Paragraph("<b>Approved Correction</b>", self.styles["TableHead"]),
                Paragraph("<b>Guideline / Proof</b>", self.styles["TableHead"]),
                Paragraph("<b>AI Reasoning & Evidence</b>", self.styles["TableHead"]),
            ]
        ]

        if findings:
            for idx, item in enumerate(findings[:8], start=1):
                orig_snippet = str(item.get("original_text") or "").strip()
                suggestion = str(item.get("suggestion") or "").strip()
                cat_label = str(item.get("category") or "grammar").title()
                rule_name = str(item.get("rule") or f"Brand {cat_label} Standard")
                explanation = str(item.get("explanation") or "").strip()

                ts_val = item.get("timestamp")
                ts_badge = f'<br/><font color="#64748B" size="7">Time: {html.escape(str(ts_val))}</font>' if ts_val else ""
                proofs_table_data.append([
                    Paragraph(f"<b>[{idx}]</b>", self.styles["TableCell"]),
                    Paragraph(f'<font color="#DC2626"><s>{html.escape(orig_snippet)}</s></font>{ts_badge}', self.styles["TableCell"]),
                    Paragraph(f'<font color="#15803D"><b>{html.escape(suggestion)}</b></font>', self.styles["TableCell"]),
                    Paragraph(f'<b>{html.escape(rule_name)}</b>', self.styles["TableCell"]),
                    Paragraph(html.escape(explanation), self.styles["TableCell"]),
                ])
        else:
            proofs_table_data.append([
                Paragraph("—", self.styles["TableCell"]),
                Paragraph("No errors", self.styles["TableCell"]),
                Paragraph("Original retained", self.styles["TableCell"]),
                Paragraph("Compliant", self.styles["TableCell"]),
                Paragraph("Text matches all approved guidelines without modification.", self.styles["TableCell"]),
            ])

        proofs_table = Table(proofs_table_data, colWidths=[24, 110, 110, 110, 186])
        proofs_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(proofs_table)

        story.append(Spacer(1, 12))

        # Section 5: Reviewer Decision & Governance Sign-off Box
        gov_box_html = (
            "<b>5. Governance Checkpoint & Reviewer Sign-off:</b><br/>"
            "Decision: &nbsp; [ &nbsp; ] <b>Approved</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; "
            "[ &nbsp; ] <b>Revisions Requested</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; "
            "[ &nbsp; ] <b>Rejected</b><br/><br/>"
            "Reviewer Signature: _________________________________ &nbsp;&nbsp;&nbsp;&nbsp; Date: ____________________<br/>"
            "<i>Note: BrandProof AI is an automated quality inspector. Final publication authority rests solely with authorized human stakeholders.</i>"
        )
        gov_table = Table([[Paragraph(gov_box_html, self.styles["ReportBody"])]], colWidths=[540])
        gov_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(gov_table)

        # Build document with custom canvas for page numbering
        doc.build(story, canvasmaker=NumberedCanvas)
        return buf.getvalue()


report_generator_service = ReportGeneratorService()
