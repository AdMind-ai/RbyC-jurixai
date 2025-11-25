from rest_framework import generics, permissions
from core.models.segreteria_societaria.deadline import Deadline
from core.serializers.segretaria_societaria.deadline_serializer import DeadlineSerializer

class DeadlineListCreateView(generics.ListCreateAPIView):
    queryset = Deadline.objects.all()
    serializer_class = DeadlineSerializer
    permission_classes = [permissions.IsAuthenticated]

class DeadlineUpdateView(generics.UpdateAPIView):

    queryset = Deadline.objects.all()
    serializer_class = DeadlineSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def patch(self, request, *args, **kwargs):
        response = self.partial_update(request, *args, **kwargs)
        return response
    