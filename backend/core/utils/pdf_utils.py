from io import BytesIO
import base64
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from pdfrw import PdfReader, PdfWriter, PageMerge
from copy import deepcopy

from markdown import markdown as md_to_html
import re

def build_overlay_pdf(title: str, content: str,
                      leftMargin=60, rightMargin=60,
                      topMargin=120, bottomMargin=100,
                      pagesize=A4) -> BytesIO:
    """Build a PDF overlay containing the provided title and markdown content."""
    overlay_buffer = BytesIO()

    try:
        doc = SimpleDocTemplate(
            overlay_buffer,
            pagesize=pagesize,
            leftMargin=leftMargin,
            rightMargin=rightMargin,
            topMargin=topMargin,
            bottomMargin=bottomMargin
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            alignment=1,
            fontSize=14,
            spaceAfter=20
        )
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=styles["Normal"],
            fontSize=11,
            leading=17
        )
        heading_style = ParagraphStyle(
            "HeadingStyle",
            parent=styles["Heading2"],
            fontSize=13,
            leading=18,
            spaceAfter=10
        )

        story = []

        # Add title
        story.append(Paragraph((title or '')[:100], title_style))
        story.append(Spacer(1, 12))

        # ---- CONVERSÃO MARKDOWN → HTML ----
        html = md_to_html(str(content or ''))

        # Normalize HTML tags into ReportLab-compatible format
        html = re.sub(r'<(/?)strong>', r'<\1b>', html)
        html = re.sub(r'<(/?)em>', r'<\1i>', html)
        html = re.sub(r'<code>(.*?)</code>', r'<font face="Courier">\1</font>', html, flags=re.S)

        # Convert lists to bullet points
        html = re.sub(r'<ul[^>]*>', '', html)
        html = re.sub(r'</ul>', '<br/>', html)
        html = re.sub(r'<li[^>]*>', '• ', html)
        html = re.sub(r'</li>', '<br/>', html)

        # Collapse paragraphs into <br/><br/>
        html = re.sub(r'</p>\s*<p>', '<br/><br/>', html)
        html = re.sub(r'<p[^>]*>', '', html)
        html = re.sub(r'</p>', '<br/><br/>', html)

        # Remove unsupported tags
        html = re.sub(r'<(/?)(div|span)[^>]*>', '', html)

        # Clean up images
        html = re.sub(r'<img[^>]*alt=[\"\']?([^\"\'>]+)[\"\']?[^>]*>', r' [Image: \1] ', html)
        html = re.sub(r'<img[^>]*>', '', html)

        # Convert <hr/>
        html = re.sub(r'<hr[^>]*>', '<br/><br/>', html)

        # ---- QUEBRA EM PARÁGRAFOS ----
        blocks = re.split(r'<br\s*/?>\s*<br\s*/?>', html)

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # Headings
            if re.match(r'^<h[1-6]>', block):
                text = re.sub(r'<(/?)h[1-6][^>]*>', '', block)
                story.append(Paragraph(text, heading_style))

            else:
                # Keep <br/> inside
                block = re.sub(r'<br\s*/?>', '<br/>', block)
                story.append(Paragraph(block, body_style))

            story.append(Spacer(1, 12))

        # Build PDF
        doc.build(story)
        overlay_buffer.seek(0)

    except Exception:
        # Return whatever exists
        overlay_buffer.seek(0)

    return overlay_buffer



def merge_with_letterhead(overlay_buffer: BytesIO, letterhead_base64: str) -> BytesIO:
    """
    Merge content PDF pages onto the letterhead background (base64 PDF).
    Uses a fresh copy of the letterhead page for each page (avoids accumulation).
    """
    try:
        lb = letterhead_base64 or ''
        if lb.startswith('data:'):
            lb = lb.split(',', 1)[1]

        template_bytes = base64.b64decode(lb)

        # PDFs
        content_pdf = PdfReader(fdata=overlay_buffer.getvalue())
        layout_pdf = PdfReader(fdata=template_bytes)

        writer = PdfWriter()

        # First letterhead page (used as background)
        layout_pages = getattr(layout_pdf, 'pages', None) or []
        layout_page = layout_pages[0] if len(layout_pages) > 0 else None

        if not layout_page:
            # No letterhead → return original content
            out = BytesIO(overlay_buffer.getvalue())
            out.seek(0)
            return out

        # Merge each page of content onto a *clean* layout page copy
        for p in content_pdf.pages:
            try:
                pm = PageMerge(p)
                pm.add(layout_page)
                pm.render()
                writer.addpage(p)
            except Exception:
                # If merging this page fails, add the raw content page instead
                writer.addpage(p)

        out = BytesIO()
        writer.write(out)
        out.seek(0)
        return out

    except Exception:
        # On ANY failure, fall back gracefully
        overlay_buffer.seek(0)
        return overlay_buffer

