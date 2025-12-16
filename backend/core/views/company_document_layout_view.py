from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from core.models.draft_document.company_document_layout import CompanyDocumentLayout
from core.serializers.draft_document.company_document_layout_serializer import CompanyDocumentLayoutSerializer


class CompanyDocumentLayoutView(APIView):
    """Simple APIView to list and create companies (name + base64 letterhead).

    GET  -> list companies
    POST -> create a company (expects JSON with `name` and optional `letterhead_base64`)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        qs = CompanyDocumentLayout.objects.all().order_by('-created_at')
        serializer = CompanyDocumentLayoutSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = CompanyDocumentLayoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompanyDocumentLayoutDetailView(APIView):
    """APIView to retrieve or delete a single company by PK."""
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        try:
            return CompanyDocumentLayout.objects.get(pk=pk)
        except CompanyDocumentLayout.DoesNotExist:
            return None

    def get(self, request, pk, format=None):
        obj = self.get_object(pk)
        if obj is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CompanyDocumentLayoutSerializer(obj)
        return Response(serializer.data)

    def delete(self, request, pk, format=None):
        obj = self.get_object(pk)
        if obj is None:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
