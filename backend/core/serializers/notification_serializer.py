from rest_framework import serializers
from core.models.notification_model import Notification


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(
        source="get_notification_type_display", read_only=True
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "notification_type_display",
            "title",
            "body",
            "reference_id",
            "reference_type",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields
