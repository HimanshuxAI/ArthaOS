from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_pl_pdf(report: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="ArthaOS Profit & Loss Report")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("ArthaOS Profit & Loss Report", styles["Title"]),
        Paragraph("Generated from uploaded bank transactions.", styles["BodyText"]),
        Spacer(1, 18),
    ]
    rows = [
        ["Section", "Amount"],
        ["Revenue", f"INR {report['revenue']:,.2f}"],
        ["Expenses", f"INR {report['expenses']:,.2f}"],
        ["Net Profit", f"INR {report['profit']:,.2f}"],
        ["Estimated Tax", f"INR {report['tax_estimate']:,.2f}"],
    ]
    table = Table(rows, colWidths=[260, 180])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buffer.getvalue()


def build_monthly_report_pdf(report: dict, intelligence: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="ArthaOS Monthly CFO Report")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("ArthaOS Monthly CFO Report", styles["Title"]),
        Paragraph("Executive Summary", styles["Heading2"]),
        Paragraph(
            f"Revenue was INR {report['revenue']:,.2f}, expenses were INR {report['expenses']:,.2f}, "
            f"net profit was INR {report['profit']:,.2f}, and estimated tax is INR {report['tax_estimate']:,.2f}.",
            styles["BodyText"],
        ),
        Spacer(1, 14),
        Paragraph("Business Health", styles["Heading2"]),
        Paragraph(
            f"{intelligence['health_score']['score']}/100 - {intelligence['health_score']['label']}. "
            f"{intelligence['health_score']['explanation']}",
            styles["BodyText"],
        ),
        Spacer(1, 14),
        Paragraph("AI Recommendations", styles["Heading2"]),
    ]
    insight_rows = [["Insight", "Recommendation"]]
    for insight in intelligence["insights"][:8]:
        insight_rows.append([insight["title"], insight["message"]])
    table = Table(insight_rows, colWidths=[150, 330])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buffer.getvalue()
