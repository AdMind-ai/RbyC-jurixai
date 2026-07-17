"""
VeraCostSyncService
===================
Busca os custos diários do Agente Vera na OpenAI e na Anthropic
e grava em VeraUsageRecord (upsert por date + provider + model).

Configuração necessária em settings / variáveis de ambiente
-----------------------------------------------------------
OpenAI (custos Vera):
  VERA_OPENAI_ADMIN_KEY      — Admin key com acesso à Usage API da organização
                               (pode ser igual a OPENAI_ADMIN_KEY se for o mesmo org)
  VERA_OPENAI_PROJECT_ID     — Project ID do projecto Vera na OpenAI
                               (deixar vazio para pegar todos os projetos da org)

Anthropic (custos Vera):
  VERA_ANTHROPIC_API_KEY     — API Key com permissão de leitura de usage
  VERA_ANTHROPIC_WORKSPACE_ID — Workspace ID (opcional, filtra por workspace)

Se uma key não estiver configurada, o provider correspondente é ignorado
e um log de aviso é emitido.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import requests
from django.conf import settings

from core.models.vera_usage_model import VeraUsageRecord

logger = logging.getLogger(__name__)

OPENAI_COSTS_URL  = "https://api.openai.com/v1/organization/costs"
ANTHROPIC_USAGE_URL = "https://api.anthropic.com/v1/usage"
ANTHROPIC_API_VERSION = "2023-06-01"


class VeraCostSyncService:
    """Sincroniza custos diários da Vera (OpenAI + Anthropic) para VeraUsageRecord."""

    # ─── Settings helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _vera_openai_admin_key() -> Optional[str]:
        return (
            getattr(settings, "VERA_OPENAI_ADMIN_KEY", None)
            or getattr(settings, "OPENAI_ADMIN_KEY", None)
        )

    @staticmethod
    def _vera_openai_project_id() -> Optional[str]:
        return (
            getattr(settings, "VERA_OPENAI_PROJECT_ID", None)
            or getattr(settings, "OPENAI_PROJECT_ID", None)
        )

    @staticmethod
    def _vera_anthropic_api_key() -> Optional[str]:
        return getattr(settings, "VERA_ANTHROPIC_API_KEY", None)

    @staticmethod
    def _vera_anthropic_workspace_id() -> Optional[str]:
        return getattr(settings, "VERA_ANTHROPIC_WORKSPACE_ID", None)

    # ─── Public API ───────────────────────────────────────────────────────────

    @classmethod
    def sync_day(cls, target_date: date) -> dict:
        """
        Sincroniza custos de um único dia. Retorna um dict com o resumo:
        {"openai": {...}, "anthropic": {...}}
        """
        result = {}
        result["openai"]    = cls._sync_openai_day(target_date)
        result["anthropic"] = cls._sync_anthropic_day(target_date)
        return result

    @classmethod
    def sync_range(cls, start: date, end: date) -> list[dict]:
        """
        Sincroniza todos os dias em [start, end] inclusive.
        Retorna lista de resultados por dia.
        """
        results = []
        current = start
        while current <= end:
            results.append({"date": current.isoformat(), **cls.sync_day(current)})
            current += timedelta(days=1)
        return results

    # ─── OpenAI ───────────────────────────────────────────────────────────────

    @classmethod
    def _sync_openai_day(cls, target_date: date) -> dict:
        admin_key  = cls._vera_openai_admin_key()
        project_id = cls._vera_openai_project_id()

        if not admin_key:
            logger.warning("VERA_OPENAI_ADMIN_KEY não configurada — OpenAI ignorado.")
            return {"status": "not_configured"}

        # A OpenAI Costs API aceita timestamps Unix (início e fim do dia UTC)
        import datetime as dt
        start_dt = dt.datetime.combine(target_date, dt.time.min, tzinfo=dt.timezone.utc)
        end_dt   = dt.datetime.combine(target_date + timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)

        params = [
            ("start_time", int(start_dt.timestamp())),
            ("end_time",   int(end_dt.timestamp())),
            ("bucket_width", "1d"),
            ("limit", 180),
            ("group_by[]", "project_id"),
            ("group_by[]", "line_item"),
        ]
        if project_id:
            params.append(("project_ids[]", project_id))

        try:
            all_buckets = cls._fetch_all_pages(
                url=OPENAI_COSTS_URL,
                headers={"Authorization": f"Bearer {admin_key}"},
                params=params,
            )
        except Exception as exc:
            logger.exception("Erro ao buscar custos OpenAI para Vera (%s): %s", target_date, exc)
            return {"status": "error", "error": str(exc)}

        # Agrupa por modelo (line_item)
        model_totals: dict[str, dict] = {}
        for bucket in all_buckets:
            for result in bucket.get("results", []):
                if project_id and result.get("project_id") not in (None, project_id):
                    continue
                model = result.get("line_item") or ""
                amount_obj = result.get("amount") or {}
                value = amount_obj.get("value")
                if value is None:
                    continue
                cost = Decimal(str(value)).quantize(Decimal("0.000001"), ROUND_HALF_UP)
                if model not in model_totals:
                    model_totals[model] = {"cost_usd": Decimal("0"), "currency": "USD"}
                model_totals[model]["cost_usd"] += cost
                model_totals[model]["currency"] = (amount_obj.get("currency") or "USD").upper()

        # Converte USD → EUR (taxa fixa configurável; padrão 1:1 se não definido)
        usd_to_eur = Decimal(str(getattr(settings, "BILLING_USD_TO_EUR_RATE", "1")))

        saved = []
        for model, data in model_totals.items():
            cost_eur = (data["cost_usd"] * usd_to_eur).quantize(Decimal("0.000001"), ROUND_HALF_UP)
            cls._upsert_record(
                target_date=target_date,
                provider="openai",
                model=model,
                cost_eur=cost_eur,
                raw_payload={"currency": data["currency"], "cost_raw": str(data["cost_usd"])},
            )
            saved.append({"model": model, "cost_eur": float(cost_eur)})

        logger.info("OpenAI Vera sync %s: %d modelos gravados", target_date, len(saved))
        return {"status": "ok", "models": saved}

    # ─── Anthropic ────────────────────────────────────────────────────────────

    @classmethod
    def _sync_anthropic_day(cls, target_date: date) -> dict:
        api_key      = cls._vera_anthropic_api_key()
        workspace_id = cls._vera_anthropic_workspace_id()

        if not api_key:
            logger.warning("VERA_ANTHROPIC_API_KEY não configurada — Anthropic ignorado.")
            return {"status": "not_configured"}

        headers = {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }
        params = {
            "start_date": target_date.isoformat(),
            "end_date":   (target_date + timedelta(days=1)).isoformat(),
        }
        if workspace_id:
            params["workspace_id"] = workspace_id

        try:
            resp = requests.get(
                ANTHROPIC_USAGE_URL,
                headers=headers,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            logger.exception("Erro ao buscar custos Anthropic para Vera (%s): %s", target_date, exc)
            return {"status": "error", "error": str(exc)}

        # Payload esperado: {"data": [{"model": "...", "input_tokens": N, "output_tokens": N, "cost": {"amount": X, "currency": "USD"}}]}
        # (estrutura baseada na Anthropic Admin API; ajustar se a resposta real for diferente)
        usd_to_eur = Decimal(str(getattr(settings, "BILLING_USD_TO_EUR_RATE", "1")))
        saved = []

        entries = payload.get("data") or payload.get("usage") or []
        for entry in entries:
            model         = entry.get("model") or entry.get("model_id") or ""
            input_tokens  = int(entry.get("input_tokens", 0))
            output_tokens = int(entry.get("output_tokens", 0))
            total_tokens  = input_tokens + output_tokens

            cost_obj = entry.get("cost") or {}
            raw_cost = cost_obj.get("amount") or entry.get("cost_usd") or entry.get("total_cost") or 0
            currency = (cost_obj.get("currency") or "USD").upper()
            cost_raw = Decimal(str(raw_cost)).quantize(Decimal("0.000001"), ROUND_HALF_UP)
            cost_eur = (cost_raw * usd_to_eur).quantize(Decimal("0.000001"), ROUND_HALF_UP) if currency == "USD" else cost_raw

            cls._upsert_record(
                target_date=target_date,
                provider="anthropic",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_eur=cost_eur,
                raw_payload=entry,
            )
            saved.append({"model": model, "cost_eur": float(cost_eur), "tokens": total_tokens})

        logger.info("Anthropic Vera sync %s: %d modelos gravados", target_date, len(saved))
        return {"status": "ok", "models": saved}

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _fetch_all_pages(url: str, headers: dict, params: list) -> list:
        """Busca todas as páginas de uma API paginada (OpenAI style)."""
        all_buckets = []
        next_page   = None
        while True:
            page_params = list(params)
            if next_page:
                page_params.append(("page", next_page))
            resp = requests.get(url, headers=headers, params=page_params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            all_buckets.extend(data.get("data", []))
            next_page = data.get("next_page")
            if not data.get("has_more") or not next_page:
                return all_buckets

    @staticmethod
    def _upsert_record(
        target_date: date,
        provider: str,
        model: str,
        cost_eur: Optional[Decimal] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        raw_payload: Optional[dict] = None,
    ) -> VeraUsageRecord:
        obj, created = VeraUsageRecord.objects.get_or_create(
            date=target_date,
            provider=provider,
            model=model,
            defaults={
                "input_tokens":  input_tokens,
                "output_tokens": output_tokens,
                "total_tokens":  total_tokens,
                "request_count": 0,
                "cost_eur":      cost_eur,
                "raw_payload":   raw_payload or {},
            },
        )
        if not created:
            # Sobrescreve (os valores vêm sempre da API do provider — fonte de verdade)
            obj.input_tokens  = input_tokens
            obj.output_tokens = output_tokens
            obj.total_tokens  = total_tokens
            obj.cost_eur      = cost_eur
            obj.raw_payload   = raw_payload or {}
            obj.save(update_fields=[
                "input_tokens", "output_tokens", "total_tokens",
                "cost_eur", "raw_payload", "updated_at",
            ])
        return obj
