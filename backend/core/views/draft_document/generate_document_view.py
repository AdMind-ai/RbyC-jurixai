from core.models.usage import UsageTool
from core.services.usage_tracking import UsageTrackingService
from core.models.draft_document.company_document_layout import CompanyDocumentLayout
from core.utils.common import safe_load_json
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from core.utils.openai_client import client, logger
from django.conf import settings
import json
from core.utils.encode_file import encode_file_base64
from io import BytesIO
from PyPDF2 import PdfReader
import re
from core.utils.quickdoc import upload_to_blob_storage
from core.utils.pdf_utils import build_overlay_pdf, merge_with_letterhead
from core.utils.word_utils import create_word_with_template


class DraftDocumentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        payload = request.data or {}

        doc_type = payload.get('doc_type')
        instructions = payload.get('instructions') or ''
        # Accept context files either as multipart uploads or as JSON payload
        files_from_request = request.FILES.getlist('context_files') if hasattr(request, 'FILES') else []
        context_files_payload = payload.get('context_files') or []

        # If payload provided context_files as a JSON string (FormData case), parse it
        if isinstance(context_files_payload, str):
            try:
                context_files_payload = json.loads(context_files_payload)
            except Exception:
                # leave as-is (will be handled downstream)
                pass

        context_files = files_from_request or context_files_payload

        generated_json = generate_draft_document(
            doc_type=doc_type,
            context_files=context_files,
            instructions=instructions
        )

        return Response({'generated_document': generated_json}, status=status.HTTP_200_OK)


def generate_draft_document(doc_type, context_files, instructions):
    """
    Gera documento usando o Responses API e retorna o JSON produzido pelo modelo.
    """

    try:
        # prompt_id configurado no painel OpenAI
        prompt_id = (settings.OPENAI_PROMPT_ID_DRAFT_DOCUMENT)

        # Build a single user content list (like send_message_view) containing
        # optional meta text and then one or more input_file entries.
        user_message_content = []

        meta_lines = []
        if doc_type:
            meta_lines.append(f"tipo_documento: {doc_type}")
        if instructions:
            meta_lines.append(f"istruzioni: {instructions}")
        if meta_lines:
            user_message_content.append({
                'type': 'input_text',
                'text': '\n'.join(meta_lines)
            })

        # context files: can be UploadedFile objects or dicts with name/mimeType,data
        for f in (context_files or []):
            try:
                filename = 'attachment'
                if hasattr(f, 'read'):
                    # Django UploadedFile
                    base64str = encode_file_base64(f)
                    filename = getattr(f, 'name', filename)
                    mime = getattr(f, 'content_type', 'application/pdf')
                    # validate pdf only
                    if not (isinstance(mime, str) and 'pdf' in mime.lower()):
                        raise ValidationError('Only PDF files are allowed as context files.')
                    file_data = f"data:{mime};base64,{base64str}"
                    # if image-like, use input_image as in send_message_view
                    if 'image' in mime:
                        user_message_content.append({
                            'type': 'input_image',
                            'image_url': file_data,
                        })
                    else:
                        user_message_content.append({
                            'type': 'input_file',
                            'filename': filename,
                            'file_data': file_data,
                        })
                elif isinstance(f, dict):
                    name = f.get('name') or f.get('filename') or filename
                    mime = f.get('mimeType') or f.get('type') or 'application/pdf'
                    data = f.get('data') or ''
                    # validate pdf only
                    if not (isinstance(mime, str) and 'pdf' in mime.lower()):
                        raise ValidationError('Only PDF files are allowed as context files.')
                    if isinstance(data, str) and data.startswith('data:'):
                        file_data = data
                    else:
                        file_data = f"data:{mime};base64,{data}"
                    filename = name
                    # treat as file (no image branch since only PDFs allowed)
                    user_message_content.append({
                        'type': 'input_file',
                        'filename': filename,
                        'file_data': file_data,
                    })
                else:
                    # unsupported entry — skip
                    continue
            except Exception as e:
                logger.exception('Error preparing context file: %s', e)

        # chamada ao Responses API — send a single user input with all content
        api_input = user_message_content if user_message_content else (instructions or "")
        response = client.responses.create(
            prompt={"id": prompt_id},
            input=[{
                'role': 'user',
                'content': api_input
            }],
            store=True,
            timeout=900,
        )

        print(f"Result: {response.output_text}")
        # Extrai texto do modelo
        raw_output = response.output_text 

        # Try to parse model output as JSON. If parsing fails, wrap the
        # raw text into a JSON object so frontend always receives JSON.
        generated_document = safe_load_json(raw_output)

        # Return the parsed document (dict or primitive) — the caller will
        # build the DRF Response. Avoid returning a DRF Response from this
        # helper to keep data JSON-serializable.
        return generated_document

    except Exception as e:
        logger.error(f"Error generating draft document: {e}")
        raise


class DraftDocumentFileView(APIView):
    """Generate PDF and Word from posted fields.

    Expects JSON (or form-data) with:
      - tipo_documento: string (used as filename)
      - titolo: string (title)
      - contenuto: string (body content)
      - note: string (optional)
      - company_id: int (optional) — if provided and company has letterhead_base64, it will be used as PDF background

    Returns JSON with urls to pdf and word files.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data or {}
        tipo = data.get('tipo_documento') or data.get('tipo') or data.get('name')
        titolo = data.get('titolo') or data.get('title') or ''
        contenuto = data.get('contenuto') or data.get('content') or ''
        note = data.get('note') or ''
        company_id = data.get('company_id')

        if not tipo or not titolo or not contenuto:
            return Response({'detail': 'Missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)

        # safe filename
        safe_name = re.sub(r'[^A-Za-z0-9_-]', '_', tipo)[:120]

        # Build overlay PDF (content only)
        try:
            overlay_buffer = build_overlay_pdf(titolo, contenuto)
        except Exception as e:
            logger.exception('Error building overlay PDF: %s', e)
            return Response({'detail': 'Error generating PDF overlay.'}, status=500)

        # If company has letterhead_base64, merge overlay onto its first page
        layout_pdf_bytes = None
        company = None
        if company_id:
            try:
                company = CompanyDocumentLayout.objects.filter(pk=company_id).first()
            except Exception:
                company = None

        # Merge overlay with company letterhead when available
        pdf_result = None
        try:
            if company and getattr(company, 'letterhead_base64', None):
                pdf_result = merge_with_letterhead(overlay_buffer, company.letterhead_base64)
            else:
                pdf_result = BytesIO(overlay_buffer.getvalue())
        except Exception as e:
            logger.exception('PDF assembly error: %s', e)
            return Response({'detail': 'Error assembling PDF.'}, status=500)

        # Create Word using existing helper — if company has a word template, use it
        try:
            letterhead_word_b64 = getattr(company, 'word_letterhead_base64', None) if company else None
            word_buffer = create_word_with_template(contenuto, titolo, letterhead_base64=letterhead_word_b64)
        except Exception as e:
            logger.exception('Error generating Word: %s', e)
            return Response({'detail': 'Error generating Word file.'}, status=500)

        # Upload files to blob storage
        total_pages_doc = 0
        try:
            pdf_bytes = pdf_result.getvalue()
            try:
                pdf_reader = PdfReader(BytesIO(pdf_bytes))
                total_pages_doc = len(pdf_reader.pages)
            except Exception as page_err:
                logger.warning("Unable to count PDF pages: %s", page_err)
            word_bytes = word_buffer.getvalue()
            pdf_blob_name = f"draftdocument/{safe_name}.pdf"
            word_blob_name = f"draftdocument/{safe_name}.docx"
            pdf_url = upload_to_blob_storage(pdf_bytes, pdf_blob_name)
            word_url = upload_to_blob_storage(word_bytes, word_blob_name)
        except Exception as e:
            logger.exception('Error uploading generated files: %s', e)
            return Response({'detail': 'Error uploading files.'}, status=500)

        # Report usage for generated document pages
        try:
            UsageTrackingService.record_usage_event(
                user=request.user,
                tool=UsageTool.DRAFT_DOCUMENT,
                quantity=total_pages_doc,
                company=getattr(request.user, "company", None),
                metadata={
                    "document_title": titolo,
                    "pages": total_pages_doc,
                },
            )
        except Exception as e:
            logger.exception("Error recording usage event for draft document: %s", e)


        return Response({
            'name': safe_name,
            'title': titolo,
            'urls': {
                'pdf': request.build_absolute_uri(pdf_url),
                'word': request.build_absolute_uri(word_url),
            }
        })



