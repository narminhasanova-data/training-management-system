"""Printable A4 version of an agenda (attached to emails and downloadable from the web app)."""

from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from integrations.pdf import fonts

from ..models import Agenda
from .agenda import FILLERS, day_label, shown_days, title

HEX = {"indigo": "#6366F1", "amber": "#F59E0B", "sky": "#0EA5E9", "rose": "#F43F5E", "lime": "#84CC16"}
INK, MUTED, BAND = colors.HexColor("#1E1B4B"), colors.HexColor("#64748B"), colors.HexColor("#F1F5F9")


def filename(agenda: Agenda) -> str:
    suffix = f"week-{agenda.week}" if agenda.kind == "week" else agenda.kind
    return f"agenda-cohort-{agenda.cohort.number}-{suffix}.pdf"


def render(agenda: Agenda) -> bytes:
    regular, bold = fonts()
    styles = {
        "org": ParagraphStyle("org", fontName=bold, fontSize=8, textColor=colors.HexColor("#4338CA"), spaceAfter=2),
        "h1": ParagraphStyle("h1", fontName=bold, fontSize=18, textColor=INK, spaceAfter=2, leading=22),
        "sub": ParagraphStyle("sub", fontName=regular, fontSize=10, textColor=MUTED, spaceAfter=10),
        "h2": ParagraphStyle("h2", fontName=bold, fontSize=12, textColor=INK, spaceBefore=10, spaceAfter=4),
        "day": ParagraphStyle("day", fontName=bold, fontSize=10.5, textColor=INK, spaceBefore=8, spaceAfter=4),
        "cell": ParagraphStyle("cell", fontName=regular, fontSize=9.5, textColor=INK, leading=12),
        "time": ParagraphStyle("time", fontName=regular, fontSize=9, textColor=MUTED, leading=12),
        "course": ParagraphStyle("course", fontName=bold, fontSize=8.5, textColor=MUTED, leading=11),
    }
    story = [
        Paragraph(settings.TMS["ORG_NAME"].upper(), styles["org"]),
        Paragraph(title(agenda), styles["h1"]),
        Paragraph(agenda.cohort.name, styles["sub"]),
    ]
    for day in shown_days(agenda):
        block = []
        if day.get("heading"):
            block.append(Paragraph(day["heading"], styles["h2"]))
        block.append(Paragraph(day_label(day["date"]) or "Date to be confirmed", styles["day"]))
        data, style = (
            [],
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (1, 0), (-1, -1), 6),
            ],
        )
        for i, row in enumerate(day["rows"]):
            if not row["time"] and not row["text"]:
                continue
            track = (
                day["tracks"][row["track"]] if row["track"] is not None and row["track"] < len(day["tracks"]) else None
            )
            course = track["course"] if track else ""
            data.append(
                [
                    "",
                    Paragraph(row["time"], styles["time"]),
                    Paragraph(row["text"], styles["cell"]),
                    Paragraph(course, styles["course"]),
                ]
            )
            n = len(data) - 1
            if track:
                style.append(("BACKGROUND", (0, n), (0, n), colors.HexColor(HEX.get(track["color"], "#6366F1"))))
            if row["text"] in FILLERS:
                style.append(("BACKGROUND", (1, n), (-1, n), BAND))
            elif i % 2:
                style.append(("BACKGROUND", (1, n), (-1, n), colors.HexColor("#FAFAFF")))
        if data:
            table = Table(data, colWidths=[3 * mm, 28 * mm, 110 * mm, 36 * mm])
            table.setStyle(TableStyle(style))
            block.append(table)
        story.append(KeepTogether(block))
        story.append(Spacer(1, 4))
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=title(agenda),
        author=settings.TMS["ORG_NAME"],
    )
    doc.build(story)
    return buffer.getvalue()
