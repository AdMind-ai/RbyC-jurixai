import uuid

from django.db import models


class ComplianceLog(models.Model):
    """
    Log degli aggiornamenti normativi inviati da Agente Vera.
    Vera invia un payload JSON con tag "LOG"; questo model lo persiste.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tipo_evento = models.CharField(max_length=100, default="aggiornamento_normativa")
    normativa = models.TextField()
    autorita = models.CharField(max_length=255, blank=True, default="")

    data_rilevazione = models.DateTimeField(null=True, blank=True)

    # Versioni: conservate come JSON libero
    versione_precedente = models.JSONField(default=dict, blank=True)
    versione_nuova = models.JSONField(default=dict, blank=True)

    riassunto_modifica = models.TextField(blank=True, default="")
    tag = models.CharField(max_length=50, default="LOG")

    # Payload raw intero, per audit
    raw_payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_rilevazione", "-created_at"]
        indexes = [
            models.Index(fields=["tag"]),
            models.Index(fields=["autorita"]),
            models.Index(fields=["data_rilevazione"]),
        ]

    def __str__(self):
        return f"[{self.autorita}] {self.normativa[:60]}"
