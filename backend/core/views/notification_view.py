import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.notification_model import Notification
from core.serializers.notification_serializer import NotificationSerializer

logger = logging.getLogger(__name__)


class NotificationListView(APIView):
    """
    GET /api/notifications/
    Lista notifiche + unread_count.
    Supporta ?type=compliance_log|newsletter_auto|consumption_* e ?unread=true
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.all()

        filter_type = request.query_params.get("type")
        if filter_type:
            qs = qs.filter(notification_type=filter_type)

        if request.query_params.get("unread") == "true":
            qs = qs.filter(is_read=False)

        qs = qs[:100]
        serializer = NotificationSerializer(qs, many=True)
        unread_count = Notification.objects.filter(is_read=False).count()

        return Response({
            "results": serializer.data,
            "unread_count": unread_count,
        })


class NotificationReadView(APIView):
    """
    POST /api/notifications/<uuid>/read/
    Marca una notifica come letta.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response({"detail": "Non trovata."}, status=status.HTTP_404_NOT_FOUND)

        notification.mark_read()
        return Response(NotificationSerializer(notification).data)


class NotificationReadAllView(APIView):
    """
    POST /api/notifications/read-all/
    Marca tutte le notifiche come lette.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django.utils import timezone
        count = Notification.objects.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now(),
        )
        return Response({"marked_read": count})


class NotificationUnreadCountView(APIView):
    """
    GET /api/notifications/unread-count/
    Ritorna solo il conteggio non letti — usato dal sidebar badge con polling.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(is_read=False).count()
        return Response({"unread_count": count})
