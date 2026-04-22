from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class UsageTool(models.TextChoices):
    RICERCA_DOCUMENTALE = "RICERCA_DOCUMENTALE", "Ricerca documentale"
    DRAFT_DOCUMENT = "DRAFT_DOCUMENT", "Draft document"
    CHECK_COMPLIANCE = "CHECK_COMPLIANCE", "Check compliance"
    CHAT_ASSISTANT = "CHAT_ASSISTANT", "Chat assistant"
    SEGRETERIA_SOCIETARIA = "SEGRETERIA_SOCIETARIA", "Segreteria societaria"


class UsageSubTool(models.TextChoices):
    # Chat assistant sub-tools
    GPT_5_2 = "GPT-5.2", "GPT-5.2"
    PERPLEXITY = "PERPLEXITY", "Perplexity"

    # Segreteria societaria sub-tools
    DOCUMENTI_AI = "DOCUMENTI_AI", "Documenti AI"
    ASSISTENTE_LEGALE = "ASSISTENTE_LEGALE", "Assistente legale"

class UsageRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="usage_records",
    )
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usage_records",
    )
    tool = models.CharField(max_length=64, choices=UsageTool.choices)
    sub_tool = models.CharField(
        max_length=64,
        choices=UsageSubTool.choices,
        blank=True,
        null=True,
    )
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Evento di utilizzo"
        verbose_name_plural = "Eventi di utilizzo"
        indexes = [
            models.Index(fields=["tool", "occurred_at"], name="usage_tool_date_idx"),
            models.Index(fields=["user", "occurred_at"], name="usage_user_date_idx"),
        ]
        ordering = ["-occurred_at"]

    def __str__(self) -> str:  # pragma: no cover - rappresentazione semplice
        return f"{self.tool} - {self.user} - {self.quantity}"

    @property
    def month_key(self) -> str:
        return self.occurred_at.strftime("%Y-%m")
