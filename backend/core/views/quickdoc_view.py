from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils import timezone
from core.models.quickdoc_model import GeneratedDocument
from core.utils.quickdoc import generate_doc_with_assistant, create_pdf_with_template, create_pdf_for_verbale_cda, create_word_with_template, create_word_for_verbale_cda, upload_to_blob_storage

class QuickDocGenerateView(APIView):

    def post(self, request):
        format = request.data.get('format')
        language = request.data.get('language')
        instructions = request.data.get('instructions')
        if not (format and language and instructions):
            return Response({'error': 'Faltam dados.'}, status=400)

        nome_arquivo, title, data, generated_text = generate_doc_with_assistant(
            format, language, instructions)

        # print(
        #     f"Generated file: {nome_arquivo}, Date: {data}, Text: {generated_text}")

        # - pdf_path = f"{settings.MEDIA_ROOT}/documents/{nome_arquivo}.pdf"
        # - word_path = f"{settings.MEDIA_ROOT}/documents/{nome_arquivo}.docx"
            
        # Gerar PDF
        if format.lower() == "verbale cda":
            pdf_data = create_pdf_for_verbale_cda(
            generated_text, title)
        else: 
            pdf_data = create_pdf_with_template(
            generated_text, title)
        
        # Gerar Word
        if format.lower() == "verbale cda":    
            word_data = create_word_for_verbale_cda(
                generated_text, title)
        else: 
            word_data = create_word_with_template(
                generated_text, title)
            
        
        # Enviar PDF ao Blob Storage
        pdf_url = upload_to_blob_storage(pdf_data.getvalue(), f"quickdoc/{nome_arquivo}.pdf")
        word_url = upload_to_blob_storage(word_data.getvalue(), f"quickdoc/{nome_arquivo}.docx")

        # Salvar no banco
        doc = GeneratedDocument.objects.create(
            name=nome_arquivo, date=timezone.now().date(),
            doc_format=format, language=language, text=generated_text
        )
        
        doc.pdf_file.name = f"documents/{nome_arquivo}.pdf"
        doc.word_file.name = f"documents/{nome_arquivo}.docx"
        doc.save()

        return Response({
            "name": nome_arquivo,
            "date": data,
            "type": ["pdf", "word"],
            "text": generated_text,
            "urls": {
                "pdf": request.build_absolute_uri(pdf_url),
                "word": request.build_absolute_uri(word_url)
            }
        })
