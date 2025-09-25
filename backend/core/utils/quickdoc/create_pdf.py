from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import simpleSplit
from pathlib import Path
from django.conf import settings
from io import BytesIO

from pdfrw import PdfReader, PdfWriter, PageMerge

def create_pdf_with_template(text, title):
    template_path = Path(settings.STATIC_ROOT) / "quickdoc" / "template_pdf.pdf"
    width, height = A4

    # buffer do overlay
    overlay_buffer = BytesIO()
    doc = SimpleDocTemplate(overlay_buffer, pagesize=A4,
                            leftMargin=60, rightMargin=60,
                            topMargin=130, bottomMargin=100)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        alignment=1,   # centralizado
        fontSize=14,
        spaceAfter=20
    )

    body_style = styles["Normal"]
    body_style.fontSize = 11
    body_style.leading = 17  # espaçamento entre linhas

    story = []

    # título
    story.append(Paragraph(title[:100], title_style))
    story.append(Spacer(1, 12))

    # corpo do texto (mantém \n\n como parágrafo e \n como quebra de linha)
    for paragraph in text.split("\n\n"):
        story.append(Paragraph(paragraph.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 12))

    doc.build(story)

    overlay_buffer.seek(0)

    # combina overlay + template
    overlay_pdf = PdfReader(overlay_buffer)
    writer = PdfWriter()

    for overlay_page in overlay_pdf.pages:
        base = PdfReader(str(template_path)).pages[0]
        PageMerge(base).add(overlay_page).render()
        writer.addpage(base)

    result_pdf = BytesIO()
    writer.write(result_pdf)
    result_pdf.seek(0)
    return result_pdf

def create_pdf_for_verbale_cda(text, title):
    pdf_buffer = BytesIO()
    width, height = A4
    c = canvas.Canvas(pdf_buffer, pagesize=A4)

    header_height = height - 50

    # desenha header só na primeira página
    def draw_header():
        c.setFont("Times-Bold", 12)
        c.drawCentredString(width/2, header_height, "Replica SIM S.p.A.")
        c.setFont("Times-Italic", 10)
        c.drawCentredString(width/2, header_height-20, "Capitale sociale Euro 10.500.000 i.v.")
        c.drawCentredString(width/2, header_height-40, "Codice fiscale e Partita IVA: 11064390963")
        c.drawCentredString(width/2, header_height-60,
                            "Sede legale in Milano - Corso Sempione, n. 2 – 20154 Milano")

    # header só na primeira página
    draw_header()

    # título centralizado
    title_height = header_height - 100
    body_top = title_height - 30
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
            if y < 60:  # quebra de página
                c.showPage()
                # não chama draw_header aqui
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 11)
                y = height - 100  # começa mais em cima já que não tem título/header

            c.drawString(x, y, l)
            y -= line_height

        if idx + 1 < len(lines) and lines[idx + 1].strip() == "":
            y -= line_height // 2

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer