import uuid

from django.db import models


class NewsletterType(models.TextChoices):
    NEWSLETTER = "newsletter", "Newsletter"
    PILL = "pill", "PILL Formativo"


class NewsletterSource(models.TextChoices):
    MANUAL = "manual", "Manuale"
    AUTO = "auto", "Automatica"


class SavedNewsletter(models.Model):
    """
    Newsletter o PILL Formativo salvati — sia creati manualmente dall'utente
    che generati automaticamente da Agente Vera il giorno 25 di ogni mese.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=512)
    content = models.TextField()

    newsletter_type = models.CharField(
        max_length=20,
        choices=NewsletterType.choices,
        default=NewsletterType.NEWSLETTER,
    )
    source = models.CharField(
        max_length=10,
        choices=NewsletterSource.choices,
        default=NewsletterSource.MANUAL,
    )

    # Populated when source=auto (Vera ingest)
    generated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source"]),
            models.Index(fields=["newsletter_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"[{self.get_source_display()}] {self.title[:60]}"
