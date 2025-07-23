from docx import Document
from docx.shared import Inches, Pt, RGBColor
from django.conf import settings
from pathlib import Path
from docx.oxml.ns import qn
from io import BytesIO

def create_word_with_header_footer(text, title):
    doc = Document()
    section = doc.sections[0]

    # Margens
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)
    section.top_margin = Inches(0.4)
    section.bottom_margin = Inches(0.5)

    section.header_distance = Inches(0.1)
    section.footer_distance = Inches(0.1)

    # HEADER: logo centralizado
    header = section.header
    head_table = header.add_table(rows=1, cols=1, width=section.page_width)
    head_cell = head_table.cell(0, 0)
    head_para = head_cell.paragraphs[0]
    head_para.alignment = 1  # Centro
    logo_path = Path(settings.STATIC_ROOT) / 'quickdoc' / 'logo-admind.png'
    if logo_path.exists():
        head_para.add_run().add_picture(str(logo_path), width=Inches(2))

    # Título
    doc.add_heading(title, level=1)

    # Corpo do doc
    for line in text.split('\n'):
        doc.add_paragraph(line.strip())

    # FOOTER: 3 linhas, centralizado, roxo
    footer = section.footer
    for i in range(3):
        para = footer.add_paragraph()
        para.alignment = 1  # centro
        run = para.add_run()
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(125, 46, 255)  # Hex: #7D2EFF

        if i == 0:
            run.font.bold = True
            run.text = "AdMind Srl"
        elif i == 1:
            run.text = "www.admind.ai – admind@admind.ai"
        elif i == 2:
            run.text = "Sede legale e operativa: Via Mazzini 9, 20123 Milano – C.F. e P.IVA 12694200960"

    word_buffer = BytesIO()
    doc.save(word_buffer)
    word_buffer.seek(0) 
    
    return word_buffer
