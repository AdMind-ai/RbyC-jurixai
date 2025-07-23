import os

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from core.serializers.translate_file_serializer import TranslateFileSerializer
from core.utils.deepl_translation import DeeplTranslation


class DeeplTranslateFileView(APIView):
    # authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = TranslateFileSerializer

    def get(self, request, format=None):
        document = self.request.query_params.get('document', '')
        file_path = os.path.join(settings.MEDIA_ROOT, 'files')

        if not document:
            return Response(
                {'detail': 'Document parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_path = os.path.join(file_path, document)

        if os.path.isfile(file_path):
            return FileResponse(
                open(file_path, 'rb'), content_type='application/octet-stream'
            )
        else:
            raise Http404('File not found')

    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        target = serializer.validated_data.get('target')
        origin = serializer.validated_data.get('origin')
        file = serializer.validated_data.get('file')
        target_supported = DeeplTranslation.TARGET.keys()

        if origin not in target_supported:
            return Response(
                {
                    'detail': f'Invalid origin language. Select from the following options: {", ".join(target_supported)}'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target not in target_supported:
            return Response(
                {
                    'detail': f'Invalid target language. Select from the following options: {", ".join(target_supported)}'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        deepl_key = os.getenv('DEEPL_KEY')
        translation = DeeplTranslation(deepl_key)
        result = translation.translate_file(file, target, origin)

        if 'error' in result:
            return Response(
                {'detail': result['error']}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {'document': result}, status=status.HTTP_200_OK
        )
