from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models


class VeraProvider(models.TextChoices):
    OPENAI    = "openai",    "OpenAI"
    ANTHROPIC = "anthropic", "Anthropic"


class VeraUsageRecord(models.Model):
    """
    Traccia il consumo giornaliero di Agente Vera per provider (OpenAI / Anthropic).
    Un record = un giorno + un provider + un modello specifico.
    Il backend può inviare più record per lo stesso giorno (es. chiamate a modelli diversi)
    oppure aggiornarne uno esistente tramite upsert.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    date     = models.DateField(db_index=True, help_text="Data UTC del consumo")
    provider = models.CharField(max_length=32, choices=VeraProvider.choices, db_index=True)
    model    = models.CharField(max_length=128, blank=True, default="", help_text="Nome modello (es. gpt-4o, claude-3-5-sonnet)")

    input_tokens  = models.BigIntegerField(default=0)
    output_tokens = models.BigIntegerField(default=0)
    total_tokens  = models.BigIntegerField(default=0)
    request_count = models.IntegerField(default=1)

    # Costo calcolato in EUR (opzionale — verrà riempito dal backend con le chiavi)
    cost_eur = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True,
        help_text="Costo stimato in EUR, calcolato lato backend"
    )

    raw_payload = models.JSONField(default=dict, blank=True, help_text="Payload grezzo ricevuto")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Consumo Vera"
        verbose_name_plural = "Consumi Vera"
        ordering = ["-date", "provider"]
        indexes = [
            models.Index(fields=["date", "provider"]),
            models.Index(fields=["provider", "date"]),
        ]
        # Unicità per (data, provider, modello) — permette upsert deterministico
        constraints = [
            models.UniqueConstraint(
                fields=["date", "provider", "model"],
                name="vera_usage_unique_day_provider_model"
            )
        ]

    def __str__(self) -> str:
        return f"[{self.provider}] {self.date} — {self.total_tokens} tok"
