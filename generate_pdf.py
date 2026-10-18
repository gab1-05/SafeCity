#!/usr/bin/env python3
"""Generate SafeCity Contributions Report PDF from Markdown."""

import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors

# Read the markdown file
with open("CONTRIBUTIONS_REPORT.md", "r", encoding="utf-8") as f:
    md_content = f.read()


def escape_xml(text):
    """Escape special XML characters."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def md_to_html_paragraph(text):
    """Convert inline markdown to HTML-safe text for reportlab."""
    # Step 1: Protect inline code spans first (replace with placeholder)
    code_spans = []
    def save_code(match):
        code_spans.append(match.group(1))
        return f"\x00CODE{len(code_spans)-1}\x00"
    text = re.sub(r"`([^`]+)`", save_code, text)

    # Step 2: Escape XML
    text = escape_xml(text)

    # Step 3: Bold **text** -> <b>text</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Step 4: Italic *text* -> <i>text</i>
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)

    # Step 5: Restore code spans as font tags (LAST, to avoid italic/bold matching inside them)
    for idx, code in enumerate(code_spans):
        text = text.replace(f"\x00CODE{idx}\x00", f"<font face='Courier'>{code}</font>")

    return text


def build_pdf():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"],
        fontSize=22, textColor=HexColor("#1B2A3A"), spaceAfter=18, alignment=1
    )
    subtitle_style = ParagraphStyle(
        "CustomSubtitle", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#555555"), spaceAfter=16, alignment=1
    )
    h1_style = ParagraphStyle(
        "CustomH1", parent=styles["Heading1"],
        fontSize=17, textColor=HexColor("#1B6F8B"), spaceBefore=18, spaceAfter=8
    )
    h2_style = ParagraphStyle(
        "CustomH2", parent=styles["Heading2"],
        fontSize=13, textColor=HexColor("#0F2A3C"), spaceBefore=12, spaceAfter=6
    )
    h3_style = ParagraphStyle(
        "CustomH3", parent=styles["Heading3"],
        fontSize=11, textColor=HexColor("#2A5D6E"), spaceBefore=9, spaceAfter=5
    )
    body_style = ParagraphStyle(
        "CustomBody", parent=styles["Normal"],
        fontSize=9.5, leading=13, spaceAfter=5, textColor=HexColor("#1A1A1A")
    )
    bullet_style = ParagraphStyle(
        "CustomBullet", parent=body_style,
        leftIndent=18, spaceAfter=3
    )
    code_style = ParagraphStyle(
        "CustomCode", parent=body_style,
        fontSize=8.5, leading=11, textColor=HexColor("#333333"),
        backColor=HexColor("#F4F4F4"), borderColor=HexColor("#DDDDDD"),
        borderWidth=0.5, borderPadding=5, leftIndent=10
    )

    story = []
    lines = md_content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Title
        if line.startswith("# "):
            story.append(Paragraph(line[2:].strip(), title_style))
        # Subtitle (second line after title)
        elif i == 1 and line.strip() and not line.startswith("#"):
            story.append(Paragraph(line.strip(), subtitle_style))
        # H1
        elif line.startswith("## "):
            story.append(Paragraph(line[3:].strip(), h1_style))
        # H2
        elif line.startswith("### "):
            story.append(Paragraph(line[4:].strip(), h2_style))
        # H3
        elif line.startswith("#### "):
            story.append(Paragraph(line[5:].strip(), h3_style))
        # Horizontal rule
        elif line.strip() == "---":
            story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#CCCCCC"),
                                    spaceBefore=6, spaceAfter=6))
        # Empty line
        elif line.strip() == "":
            story.append(Spacer(1, 5))
        # Code block
        elif line.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_text = "<br/>".join(escape_xml(c) for c in code_lines)
            story.append(Paragraph(f"<font face='Courier'>{code_text}</font>", code_style))
            i += 1
            continue
        # Table
        elif line.startswith("|") and "|" in line[1:]:
            table_rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                table_rows.append(cells)
                i += 1
            if len(table_rows) > 1:
                header = table_rows[0]
                data = table_rows[2:]  # skip header and separator
                t = Table([header] + data, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1B6F8B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#999999")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFFFFF"), HexColor("#F0F5F8")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]))
                story.append(t)
                story.append(Spacer(1, 7))
            continue
        # List item
        elif line.startswith("- "):
            story.append(Paragraph(f"• {md_to_html_paragraph(line[2:].strip())}", bullet_style))
        # Regular text
        else:
            processed = md_to_html_paragraph(line)
            if processed.strip():
                story.append(Paragraph(processed, body_style))

        i += 1

    doc = SimpleDocTemplate(
        "SafeCity_Contributions_Report.pdf",
        pagesize=letter,
        rightMargin=0.7*inch,
        leftMargin=0.7*inch,
        topMargin=0.7*inch,
        bottomMargin=0.7*inch,
        title="SafeCity Contributions Report",
        author="SafeCity Team",
        subject="Contributor attribution report based on git history and MD files",
    )

    doc.build(story)
    print("PDF generated: SafeCity_Contributions_Report.pdf")


if __name__ == "__main__":
    build_pdf()
