"""Fonts for generated PDFs: a Unicode TrueType font when one is available (DejaVu ships in the
Docker image), otherwise ReportLab's built-in Helvetica."""

import os
from functools import cache

from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
]


@cache
def fonts() -> tuple[str, str]:
    """(regular, bold) font names registered with ReportLab."""
    custom = settings.TMS["PDF_FONT_PATH"]
    pairs = ([(custom, custom)] if custom else []) + CANDIDATES
    for regular, bold in pairs:
        if os.path.exists(regular) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont("TMS-Regular", regular))
            pdfmetrics.registerFont(TTFont("TMS-Bold", bold))
            return "TMS-Regular", "TMS-Bold"
    return "Helvetica", "Helvetica-Bold"
