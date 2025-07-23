import os
import tempfile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status

from core.serializers.extract_content_serializer import ExtractedContentSerializer

import pytesseract
from PIL import Image

import fitz
import docx


class ExtractContentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'Nenhum arquivo enviado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        filename = file_obj.name
        ext = os.path.splitext(filename)[-1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmpf:
            for chunk in file_obj.chunks():
                tmpf.write(chunk)
            tmp_path = tmpf.name

        content = ''
        try:
            if ext == '.txt':
                with open(tmp_path, encoding='utf-8', errors='ignore') as f:
                    content = f.read()

            elif ext == '.docx':
                doc = docx.Document(tmp_path)
                content = '\n'.join([para.text for para in doc.paragraphs])

            elif ext == '.pdf':
                doc = fitz.open(tmp_path)
                text = []
                for page in doc:
                    text.append(page.get_text())
                content = '\n'.join(text)
                doc.close()

            elif ext in ['.jpg', '.jpeg', '.png']:
                image = Image.open(tmp_path)
                content = pytesseract.image_to_string(image)

            else:
                os.unlink(tmp_path)
                return Response(
                    {'error': 'Formato de arquivo não suportado'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            content = content.strip()

        except Exception as e:
            os.unlink(tmp_path)
            return Response(
                {'error': 'Erro ao extrair conteúdo: ' + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        os.unlink(tmp_path)
        serializer = ExtractedContentSerializer(
            {'document': filename, 'content': content})
        return Response(serializer.data)
