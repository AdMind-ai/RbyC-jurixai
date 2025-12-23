from rest_framework.views import APIView
from rest_framework.response import Response
from integrations.authentication import APIKeyAuthentication
from integrations.permissions import HasValidAPIKey
from drf_spectacular.utils import extend_schema

@extend_schema(
    description="Health check of Integrations API"
)
class HealthCheckView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasValidAPIKey]

    @extend_schema(
        summary="Health check",
        responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
    )
    def get(self, request):
        return Response({"status": "ok"})
