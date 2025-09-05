from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import simpleSplit
from pathlib import Path
from django.conf import settings
from io import BytesIO


def create_pdf_with_header_footer(text, title):
    logo_path = Path(settings.STATIC_ROOT) / "quickdoc" / "logo-rbyc.jpg"
    pdf_buffer = BytesIO(); 
    
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4

    header_height = height - 125
    title_height = header_height - 5
    body_top = title_height - 30

    def draw_header():
        if logo_path.exists():
            c.drawImage(str(logo_path), (width-100)/2, header_height,
                        width=97, mask='auto', preserveAspectRatio=True)

    def draw_footer():
        c.setFont("Helvetica-Bold", 9)
        # c.setFillColor(colors.HexColor("#7030A0"))
        c.drawCentredString(width/2, 37, "RbyC s.r.l.")
        c.setFont("Helvetica", 8)
        c.drawCentredString(width/2, 27, "www.rbyc.eu")
        c.drawCentredString(width/2, 17,
                            "Sede legale e operativa: Piazza Giuseppe Missori 2, 20122 Milano – C.F. e P.IVA 09233650960")

    draw_header()
    draw_footer()
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, title_height, title[:100])

    max_width = width - 80
    c.setFont("Helvetica", 11)
    x = 40
    y = body_top
    line_height = 17

    lines = text.split('\n')
    for idx, line in enumerate(lines):
        if line.strip() == "":
            y -= line_height // 2
            continue

        splitted = simpleSplit(line.strip(), "Helvetica", 11, max_width)
        for l in splitted:
            if y < 60:  # checa antes de imprimir
                c.showPage()
                draw_header()
                draw_footer()
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 11)
                y = body_top

            c.drawString(x, y, l)
            y -= line_height

        # Espaço extra após parágrafo
        if idx + 1 < len(lines) and lines[idx + 1].strip() == "":
            y -= line_height // 2

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer