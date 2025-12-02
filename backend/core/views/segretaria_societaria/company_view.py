from rest_framework import generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models.segreteria_societaria.company_model import Company
from core.serializers.segretaria_societaria.company_serializer import CompanySerializer
from django.http import FileResponse, Http404
import mimetypes
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from pdfrw import PdfReader, PdfWriter, PageMerge
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from markdown import markdown as md_to_html
import re


class CompanyListCreateView(generics.ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]


class CompanyUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'
    parser_classes = [MultiPartParser, FormParser, JSONParser]


class CompanyLetterheadProxyView(APIView):
    """Proxy endpoint that returns the raw letterhead file binary for a company.

    Query params:
      - name: company name (case-insensitive exact match)
      - id: company id (optional)

    Returns: FileResponse streaming the stored file. Requires authentication.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        name = request.query_params.get('name')
        cid = request.query_params.get('id')

        try:
            if cid:
                company = Company.objects.get(pk=cid)
            elif name:
                company = Company.objects.get(name__iexact=name)
            else:
                return Response({'detail': 'Query parameter "name" or "id" is required.'}, status=status.HTTP_400_BAD_REQUEST)
        except Company.DoesNotExist:
            return Response({'detail': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not company.letterhead_file:
            return Response({'detail': 'Letterhead file not found for this company.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Ensure the file is opened via Django storage (works with local and remote storages)
            company.letterhead_file.open('rb')
            fileobj = company.letterhead_file
            # Try to infer mime type
            mime_type, _ = mimetypes.guess_type(fileobj.name)
            content_type = mime_type or 'application/octet-stream'
            response = FileResponse(fileobj, content_type=content_type)
            # Inline display (not attachment)
            response['Content-Disposition'] = f'inline; filename="{fileobj.name.split("/")[-1]}"'
            return response
        except Exception as e:
            # If storage backend cannot open file directly, return 500
            return Response({'detail': f'Error opening file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateDocumentPDFView(APIView):
    """Generate a PDF by placing the provided markdown/HTML content between header/footer
    defined in the stored company letterhead PDF. The endpoint accepts JSON:
      { company_id: int (optional), markdown: string }

    If the company has a `letterhead_file` PDF, the view will use its first page as
    a background for all generated content pages; otherwise it will generate a plain
    PDF with the content.
    Returns: application/pdf
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        company_id = request.data.get('company_id')
        markdown_text = request.data.get('markdown') or request.data.get('content') or ''

        company = None
        layout_pdf_bytes = None
        if company_id:
            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                return Response({'detail': 'Company not found.'}, status=status.HTTP_404_NOT_FOUND)

        if company and company.letterhead_file:
            try:
                company.letterhead_file.open('rb')
                layout_pdf_bytes = company.letterhead_file.read()
            except Exception:
                layout_pdf_bytes = None

        # Create content PDF from markdown_text using ReportLab Platypus
        content_buffer = io.BytesIO()
        page_width, page_height = A4

        # Margins: keep left as before, increase right margin slightly
        left_margin = 48
        right_margin = 72  # increased right margin only
        # Reserve header/footer space
        top_offset = 120
        bottom_offset = 100

        doc = SimpleDocTemplate(
            content_buffer,
            pagesize=A4,
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_offset,
            bottomMargin=bottom_offset,
        )

        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            name='Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=14,
        )
        heading_style = ParagraphStyle(
            name='Heading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            spaceAfter=6,
        )

        # Convert markdown to HTML, then perform lightweight transformations so ReportLab Paragraph
        # can render basic inline tags (<b>, <i>, <font>) and line breaks. Convert lists to bullets.
        html = md_to_html(str(markdown_text or ''))

        # Normalize tags: markdown lib uses <strong>/<em>/<code>, map to reportlab-friendly tags
        html = re.sub(r'<(/?)strong>', r'<\1b>', html)
        html = re.sub(r'<(/?)em>', r'<\1i>', html)
        html = re.sub(r'<code>(.*?)</code>', r'<font face="Courier">\1</font>', html, flags=re.S)

        # Convert unordered lists into bullet lines: replace <li> with bullet + closing li with <br/>
        html = re.sub(r'<ul[^>]*>', '', html)
        html = re.sub(r'</ul>', '<br/>', html)
        html = re.sub(r'<li[^>]*>', '• ', html)
        html = re.sub(r'</li>', '<br/>', html)

        # Replace paragraphs with line breaks to allow Paragraph to render blocks
        html = re.sub(r'</p>\s*<p>', '<br/><br/>', html)
        html = re.sub(r'<p[^>]*>', '', html)
        html = re.sub(r'</p>', '<br/><br/>', html)

        # Remove any remaining block-level tags we don't support
        html = re.sub(r'<(/?)(div|span)[^>]*>', '', html)
        # Sanitize <img> tags: prefer alt text as placeholder, remove remaining images
        html = re.sub(r'<img[^>]*alt=[\"\"]?([^\"\'>]+)[\"\"]?[^>]*>', r' [Image: \1] ', html, flags=re.IGNORECASE)
        html = re.sub(r'<img[^>]*>', '', html, flags=re.IGNORECASE)
        # Convert horizontal rules to spacing
        html = re.sub(r'<hr[^>]*>', '<br/><br/>', html, flags=re.IGNORECASE)

        story = []

        # Split into lines by double breaks to create paragraphs
        blocks = re.split(r'<br\s*/?>\s*<br\s*/?>', html)
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            # If block starts with a heading tag, use heading style
            if re.match(r'^<h[1-6]>', block):
                # strip heading tags
                text = re.sub(r'<(/?)h[1-6][^>]*>', '', block)
                story.append(Paragraph(text, heading_style))
            else:
                # Replace remaining single <br/> with <br/> for Paragraph
                block = re.sub(r'<br\s*/?>', '<br/>', block)
                story.append(Paragraph(block, body_style))
            story.append(Spacer(1, 6))

        try:
            doc.build(story)
            content_pdf_bytes = content_buffer.getvalue()
        except Exception:
            # Fallback to very simple plain-text rendering if Platypus build fails
            content_buffer = io.BytesIO()
            c = canvas.Canvas(content_buffer, pagesize=(page_width, page_height))
            usable_width = page_width - left_margin - right_margin
            y = page_height - top_offset
            for paragraph in str(markdown_text).split('\n\n'):
                text = paragraph.replace('\n', ' ')
                wrapped = simpleSplit(text, 'Helvetica', 11, usable_width)
                for wline in wrapped:
                    if y < bottom_offset + 14:
                        c.showPage()
                        y = page_height - top_offset
                    c.drawString(left_margin, y, wline)
                    y -= 14
                y -= 8
            c.save()
            content_pdf_bytes = content_buffer.getvalue()


        # If we have a layout PDF, try to merge content pages onto the layout background.
        # If merging fails for any reason, fall back to returning the content-only PDF
        # instead of raising a 500 to the client.
        if layout_pdf_bytes:
            try:
                layout_pdf = PdfReader(fdata=layout_pdf_bytes)
                content_pdf = PdfReader(fdata=content_pdf_bytes)

                out_writer = PdfWriter()

                # Ensure we have at least one layout page
                layout_pages = getattr(layout_pdf, 'pages', None) or []
                layout_page = layout_pages[0] if len(layout_pages) > 0 else None

                if not layout_page:
                    # Nothing to merge; return content PDF
                    return FileResponse(io.BytesIO(content_pdf_bytes), content_type='application/pdf')

                # For each content page, merge it over a fresh copy of the layout page.
                # Use PageMerge on the content page and add the layout as a background.
                for p in content_pdf.pages:
                    try:
                        pm = PageMerge(p)
                        pm.add(layout_page)
                        pm.render()
                        out_writer.addpage(p)
                    except Exception:
                        # If merging this page fails, add the raw content page instead
                        out_writer.addpage(p)

                output_buffer = io.BytesIO()
                out_writer.write(output_buffer)
                output_buffer.seek(0)
                return FileResponse(output_buffer, content_type='application/pdf')
            except Exception as e:
                # Log the error and return the content-only PDF as fallback
                import logging
                logging.exception('Error while merging layout PDF; returning content-only PDF')
                return FileResponse(io.BytesIO(content_pdf_bytes), content_type='application/pdf')

        # Otherwise return the content PDF directly
        return FileResponse(io.BytesIO(content_pdf_bytes), content_type='application/pdf')
