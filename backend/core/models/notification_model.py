import uuid

from django.db import models
from django.utils import timezone


class NotificationType(models.TextChoices):
    COMPLIANCE_LOG = "compliance_log", "Log Compliance"
    NEWSLETTER_AUTO = "newsletter_auto", "Newsletter Automatica"
    CONSUMPTION_REPORT = "consumption_report", "Report Mensile Consumo"
    CONSUMPTION_LOW_BALANCE = "consumption_low_balance", "Saldo Wallet Basso"
    CONSUMPTION_THRESHOLD = "consumption_threshold", "Limite Mensile Raggiunto"


class Notification(models.Model):
    """
    Notifiche di sistema: log compliance, newsletter auto, aggiornamenti consumo AI.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
    )

    title = models.CharField(max_length=512)
    body = models.TextField(blank=True, default="")

    # Optional reference to a related object (e.g. SavedNewsletter id, ComplianceLog id)
    reference_id = models.CharField(max_length=64, blank=True, default="")
    # e.g. "compliance_log", "saved_newsletter"
    reference_type = models.CharField(max_length=40, blank=True, default="")

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_read"]),
            models.Index(fields=["notification_type"]),
            models.Index(fields=["created_at"]),
        ]

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def __str__(self):
        status = "✓" if self.is_read else "●"
        return f"{status} [{self.get_notification_type_display()}] {self.title[:60]}"
