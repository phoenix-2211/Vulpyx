"""
VULPYX – PDF Report Generator
Converts the markdown final report into a professional PDF.
Requires: reportlab  (installed via requirements.txt)
"""
import os
import re
import datetime

try:
    from reportlab.lib.pagesizes  import A4
    from reportlab.lib.styles     import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units      import cm
    from reportlab.lib            import colors
    from reportlab.platypus       import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak
    )
    from reportlab.lib.enums      import TA_CENTER, TA_LEFT
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

from core.banner import print_ok, print_warn, print_err, GRN, RED, R

# ── Brand colours ──────────────────────────────────────────────────────────────
_BLACK  = colors.HexColor("#0d0d0d")
_DARK   = colors.HexColor("#1a1a2e")
_ACCENT = colors.HexColor("#e94560")
_CYAN   = colors.HexColor("#0f3460")
_LIGHT  = colors.HexColor("#f5f5f5")
_MID    = colors.HexColor("#cccccc")
_RED    = colors.HexColor("#e74c3c")
_YEL    = colors.HexColor("#f39c12")
_GRN    = colors.HexColor("#27ae60")
_WHITE  = colors.white


def _sev_color(sev: str):
    s = sev.upper()
    if s == "CRITICAL": return _RED
    if s == "HIGH":     return colors.HexColor("#e67e22")
    if s == "MEDIUM":   return _YEL
    if s == "LOW":      return _GRN
    return _MID


# ── Build styles ───────────────────────────────────────────────────────────────
def _build_styles():
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "vx_title",
            fontSize=28, textColor=_ACCENT,
            spaceAfter=4, spaceBefore=0,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "vx_subtitle",
            fontSize=11, textColor=_MID,
            spaceAfter=20,
            fontName="Helvetica",
            alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "vx_h1",
            fontSize=16, textColor=_ACCENT,
            spaceBefore=18, spaceAfter=6,
            fontName="Helvetica-Bold",
        ),
        "h2": ParagraphStyle(
            "vx_h2",
            fontSize=13, textColor=_CYAN,
            spaceBefore=12, spaceAfter=4,
            fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "vx_body",
            fontSize=10, textColor=_BLACK,
            spaceAfter=6, leading=15,
            fontName="Helvetica",
        ),
        "code": ParagraphStyle(
            "vx_code",
            fontSize=9, textColor=colors.HexColor("#2c3e50"),
            spaceAfter=6, leading=14,
            fontName="Courier",
            backColor=_LIGHT,
            leftIndent=10, rightIndent=10,
            borderPadding=(4, 4, 4, 4),
        ),
        "bullet": ParagraphStyle(
            "vx_bullet",
            fontSize=10, textColor=_BLACK,
            spaceAfter=3, leading=14,
            fontName="Helvetica",
            leftIndent=15,
            bulletIndent=5,
        ),
        "label": ParagraphStyle(
            "vx_label",
            fontSize=9, textColor=_MID,
            fontName="Helvetica",
        ),
    }
    return styles


# ── Parse markdown into reportlab flowables ────────────────────────────────────
def _md_to_flowables(md_text: str, styles: dict) -> list:
    flowables = []
    lines     = md_text.splitlines()
    i         = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # Heading 1
        if line.startswith("# "):
            flowables.append(Paragraph(line[2:].strip(), styles["h1"]))
            flowables.append(HRFlowable(width="100%", thickness=1,
                                         color=_ACCENT, spaceAfter=6))

        # Heading 2/3
        elif line.startswith("## ") or line.startswith("### "):
            text = line.lstrip("#").strip()
            flowables.append(Paragraph(text, styles["h2"]))

        # Horizontal rule
        elif line.startswith("---"):
            flowables.append(HRFlowable(width="100%", thickness=0.5,
                                         color=_MID, spaceAfter=8, spaceBefore=8))

        # Table (markdown | col | col |)
        elif line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            flowables.append(_md_table(table_lines, styles))
            continue

        # Bullet
        elif line.startswith("- ") or line.startswith("* "):
            text = line[2:].strip()
            flowables.append(Paragraph(f"• {text}", styles["bullet"]))

        # Numbered list
        elif re.match(r"^\d+\. ", line):
            text = re.sub(r"^\d+\. ", "", line).strip()
            flowables.append(Paragraph(f"• {text}", styles["bullet"]))

        # Code block
        elif line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_text = "\n".join(code_lines)
            flowables.append(Paragraph(code_text.replace("\n", "<br/>"),
                                        styles["code"]))

        # Bold text (**text**)
        elif line.strip():
            text = line
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
            text = re.sub(r"\*(.+?)\*",     r"<i>\1</i>", text)
            text = re.sub(r"`(.+?)`",       r"<font name='Courier'>\1</font>", text)
            flowables.append(Paragraph(text, styles["body"]))

        else:
            flowables.append(Spacer(1, 6))

        i += 1

    return flowables


def _md_table(lines: list[str], styles: dict):
    rows = []
    for line in lines:
        if re.match(r"\|[-:| ]+\|", line):
            continue   # skip separator row
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)

    if not rows:
        return Spacer(1, 4)

    # Style
    col_count = max(len(r) for r in rows)
    col_width = (A4[0] - 4*cm) / col_count

    table_data = []
    for r in rows:
        # Pad / trim
        row = r[:col_count] + [""] * (col_count - len(r))
        table_data.append([Paragraph(str(c), styles["body"]) for c in row])

    t = Table(table_data, colWidths=[col_width]*col_count)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  _DARK),
        ("TEXTCOLOR",   (0,0), (-1,0),  _WHITE),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [_LIGHT, _WHITE]),
        ("GRID",        (0,0), (-1,-1), 0.4, _MID),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
    ]))
    return t


# ── Cover page ─────────────────────────────────────────────────────────────────
def _cover_page(project: str, target: str, styles: dict) -> list:
    now = datetime.datetime.now().strftime("%B %d, %Y  %H:%M")
    return [
        Spacer(1, 3*cm),
        Paragraph("VULPYX", styles["title"]),
        Paragraph("AI-Powered Penetration Test Report", styles["subtitle"]),
        Spacer(1, 1*cm),
        HRFlowable(width="60%", thickness=2, color=_ACCENT,
                   hAlign="CENTER", spaceAfter=20),
        Spacer(1, 0.5*cm),
        Paragraph(f"Project: {project}", styles["h2"]),
        Paragraph(f"Target:  {target}",  styles["h2"]),
        Paragraph(f"Date:    {now}",      styles["body"]),
        Spacer(1, 2*cm),
        Paragraph(
            "CONFIDENTIAL — For authorized use only. "
            "This report was generated by VULPYX in a controlled lab environment.",
            ParagraphStyle("vx_disc", fontSize=8, textColor=_MID,
                           fontName="Helvetica", alignment=TA_CENTER)
        ),
        PageBreak(),
    ]


# ── Public: generate PDF ───────────────────────────────────────────────────────
def generate_pdf(md_text: str, pdf_path: str,
                 project: str = "Engagement",
                 target:  str = "Target") -> bool:
    if not REPORTLAB_OK:
        print_warn("reportlab not installed — PDF generation skipped.")
        print_warn("Run:  pip3 install reportlab --break-system-packages")
        return False

    try:
        styles = _build_styles()
        doc    = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2*cm,  bottomMargin=2*cm,
            title=f"VULPYX Report — {project}",
            author="VULPYX AI Pentesting Assistant",
        )

        story = []
        story += _cover_page(project, target, styles)
        story += _md_to_flowables(md_text, styles)

        doc.build(story)
        print_ok(f"PDF report saved: {pdf_path}")
        return True

    except Exception as e:
        print_err(f"PDF generation failed: {e}")
        return False
