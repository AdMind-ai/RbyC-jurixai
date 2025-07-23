import os

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from core.utils.deepl_translation import DeeplTranslation


class DeeplTranslateTextView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        text = request.data.get('text')
        origin = request.data.get('origin')
        target = request.data.get('target')

        if not text or not origin or not target:
            return Response({'detail': 'Missing parameter'}, status=400)

        deepl_key = os.getenv('DEEPL_KEY')
        translation = DeeplTranslation(deepl_key)
        translated_text = translation.translate_text(text, origin, target)

        return Response({'translated_text': translated_text}, status=200)
