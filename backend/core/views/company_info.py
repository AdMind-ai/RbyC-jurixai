from rest_framework.views import APIView
from rest_framework.response import Response
from core.models.company_info import CompanyInfo
from core.serializers.company_info import CompanySerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication


class CompanyInfoView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            company = CompanyInfo.objects.first()
            if not company:
                return Response({'error': 'No company found.'}, status=404)
            serializer = CompanySerializer(company)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
