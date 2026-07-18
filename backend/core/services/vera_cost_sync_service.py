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
  VERA_ANTHROPIC_API_KEY     — Admin API key da Anthropic (formato sk-ant-admin...)
                               Obtida em console.anthropic.com → Settings → Admin API keys
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
from django.core.cache import cache

from core.models.vera_usage_model import VeraUsageRecord

logger = logging.getLogger(__name__)

OPENAI_COSTS_URL  = "https://api.openai.com/v1/organization/costs"
# Anthropic Admin API — requer Admin key (sk-ant-admin...)
# Docs: https://docs.anthropic.com/en/api/admin-api
ANTHROPIC_COST_URL = "https://api.anthropic.com/v1/organizations/cost_report"
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
    def sync_range(cls, start: date, end: date, *, force: bool = False) -> dict:
        """
        Sincroniza todos os dias em [start, end] inclusive.
        Usa chamadas por intervalo para evitar rate limit dos providers.
        """
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "openai": cls._sync_provider_range(
                provider="openai",
                start=start,
                end=end,
                force=force,
                sync_fn=cls._sync_openai_range,
            ),
            "anthropic": cls._sync_provider_range(
                provider="anthropic",
                start=start,
                end=end,
                force=force,
                sync_fn=cls._sync_anthropic_range,
            ),
        }

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
                if project_id and result.get("project_id") != project_id:
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

        saved = []
        for model, data in model_totals.items():
            cost_eur = data["cost_usd"].quantize(Decimal("0.000001"), ROUND_HALF_UP)
            cls._upsert_record(
                target_date=target_date,
                provider="openai",
                model=model,
                cost_eur=cost_eur,
                raw_payload={"currency": data["currency"], "cost_raw": str(data["cost_usd"])},
            )
            saved.append({"model": model, "cost_eur": float(cost_eur)})

        cls._delete_stale_records(
            target_date=target_date,
            provider="openai",
            valid_models=set(model_totals.keys()),
        )

        logger.info("OpenAI Vera sync %s: %d modelos gravados", target_date, len(saved))
        return {"status": "ok", "models": saved}

    @classmethod
    def _sync_openai_range(cls, start: date, end: date) -> dict:
        admin_key = cls._vera_openai_admin_key()
        project_id = cls._vera_openai_project_id()

        if not admin_key:
            logger.warning("VERA_OPENAI_ADMIN_KEY nao configurada - OpenAI ignorado.")
            return {"status": "not_configured"}

        import datetime as dt

        start_dt = dt.datetime.combine(start, dt.time.min, tzinfo=dt.timezone.utc)
        end_dt = dt.datetime.combine(end + timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)

        params = [
            ("start_time", int(start_dt.timestamp())),
            ("end_time", int(end_dt.timestamp())),
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
            logger.exception("Erro ao buscar custos OpenAI para Vera (%s/%s): %s", start, end, exc)
            return {"status": "error", "error": str(exc)}

        rows = []

        for bucket in all_buckets:
            bucket_start = bucket.get("start_time")
            if bucket_start is None:
                continue
            bucket_date = dt.datetime.fromtimestamp(int(bucket_start), tz=dt.timezone.utc).date()
            if bucket_date < start or bucket_date > end:
                continue

            model_totals: dict[str, dict] = {}
            for result in bucket.get("results", []):
                if project_id and result.get("project_id") != project_id:
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

            for model, data in model_totals.items():
                cost_eur = data["cost_usd"].quantize(Decimal("0.000001"), ROUND_HALF_UP)
                rows.append(
                    {
                        "date": bucket_date,
                        "provider": "openai",
                        "model": model,
                        "cost_eur": cost_eur,
                        "raw_payload": {
                            "currency": data["currency"],
                            "cost_raw": str(data["cost_usd"]),
                        },
                    }
                )

        cls._replace_provider_range(start=start, end=end, provider="openai", rows=rows)
        logger.info("OpenAI Vera sync %s/%s: %d linhas gravadas", start, end, len(rows))
        return {"status": "ok", "rows": len(rows)}

    # ─── Anthropic ────────────────────────────────────────────────────────────

    @classmethod
    def _sync_anthropic_day(cls, target_date: date) -> dict:
        api_key      = cls._vera_anthropic_api_key()
        workspace_id = cls._vera_anthropic_workspace_id()

        if not api_key:
            logger.warning("VERA_ANTHROPIC_API_KEY não configurada — Anthropic ignorado.")
            return {"status": "not_configured"}

        # A Anthropic Cost Report API requer uma Admin API key (sk-ant-admin...)
        # obtida em console.anthropic.com → Settings → Admin API keys
        if not api_key.startswith("sk-ant-admin"):
            logger.warning(
                "VERA_ANTHROPIC_API_KEY não parece ser uma Admin key (esperado sk-ant-admin...). "
                "A Cost Report API requer uma Admin key — Anthropic ignorado."
            )
            return {"status": "not_admin_key"}

        # A cost_report API só devolve dias completos — ending_at não pode ser futuro.
        # Se target_date for hoje ou futuro, ignoramos (dados não finalizados).
        last_available_date = cls._anthropic_last_available_date()
        if target_date > last_available_date:
            logger.info(
                "Anthropic cost_report: %s ainda nao esta finalizado, ignorado.",
                target_date,
            )
            return {"status": "skipped_future"}

        # Endpoint: GET /v1/organizations/cost_report
        # Intervalo: [target_date 00:00Z, target_date+1 00:00Z)
        headers = {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }
        params = [
            ("starting_at", f"{target_date.isoformat()}T00:00:00Z"),
            ("ending_at", f"{(target_date + timedelta(days=1)).isoformat()}T00:00:00Z"),
            ("bucket_width", "1d"),
            ("limit", 10),
        ]
        if workspace_id:
            params.append(("group_by[]", "workspace_id"))

        try:
            resp = requests.get(
                ANTHROPIC_COST_URL,
                headers=headers,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            payload = resp.json()
        except requests.HTTPError as exc:
            rate_limit_payload = cls._anthropic_rate_limit_payload(exc.response)
            if rate_limit_payload:
                logger.warning(
                    "Anthropic rate limit while syncing Vera costs (%s): %s",
                    target_date,
                    rate_limit_payload,
                )
                return rate_limit_payload
            logger.exception("Erro ao buscar custos Anthropic para Vera (%s): %s", target_date, exc)
            return {"status": "error", "error": str(exc)}
        except Exception as exc:
            logger.exception("Erro ao buscar custos Anthropic para Vera (%s): %s", target_date, exc)
            return {"status": "error", "error": str(exc)}

        # Resposta real: {"data": [{"starting_at": "...", "results": [
        #   {"currency": "USD", "amount": "123.45", "model": null, ...}
        # ]}]}
        # A cost_report agrega o total da organização (sem breakdown por modelo).
        saved = []

        for bucket in payload.get("data") or []:
            for entry in bucket.get("results") or []:
                if workspace_id and entry.get("workspace_id") != workspace_id:
                    continue
                # model pode ser null — guardamos como "[total]"
                model    = entry.get("model") or "[total]"
                currency = (entry.get("currency") or "USD").upper()
                raw_cost = Decimal(str(entry.get("amount") or "0"))
                cost_eur = cls._normalize_anthropic_amount(raw_cost, currency)

                # cost_report não devolve contagens de tokens
                cls._upsert_record(
                    target_date=target_date,
                    provider="anthropic",
                    model=model,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    cost_eur=cost_eur,
                    raw_payload=entry,
                )
                saved.append({"model": model, "cost_eur": float(cost_eur)})

        cls._delete_stale_records(
            target_date=target_date,
            provider="anthropic",
            valid_models={entry["model"] for entry in saved},
        )

        logger.info("Anthropic Vera sync %s: %d modelos gravados", target_date, len(saved))
        return {"status": "ok", "models": saved}

    @classmethod
    def _sync_anthropic_range(cls, start: date, end: date) -> dict:
        api_key = cls._vera_anthropic_api_key()
        workspace_id = cls._vera_anthropic_workspace_id()

        if not api_key:
            logger.warning("VERA_ANTHROPIC_API_KEY nao configurada - Anthropic ignorado.")
            return {"status": "not_configured"}

        if not api_key.startswith("sk-ant-admin"):
            logger.warning(
                "VERA_ANTHROPIC_API_KEY nao parece ser uma Admin key. Anthropic ignorado."
            )
            return {"status": "not_admin_key"}

        final_end = min(end, cls._anthropic_last_available_date())
        if final_end < start:
            return {"status": "skipped_future"}

        headers = {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }
        params = [
            ("starting_at", f"{start.isoformat()}T00:00:00Z"),
            ("ending_at", f"{(final_end + timedelta(days=1)).isoformat()}T00:00:00Z"),
            ("bucket_width", "1d"),
            ("limit", cls.anthropic_cost_report_limit()),
        ]
        if workspace_id:
            params.append(("group_by[]", "workspace_id"))

        try:
            payload = cls._fetch_anthropic_cost_report(headers=headers, params=params)
        except requests.HTTPError as exc:
            rate_limit_payload = cls._anthropic_rate_limit_payload(exc.response)
            if rate_limit_payload:
                logger.warning(
                    "Anthropic rate limit while syncing Vera costs (%s/%s): %s",
                    start,
                    final_end,
                    rate_limit_payload,
                )
                return rate_limit_payload
            logger.exception("Erro ao buscar custos Anthropic para Vera (%s/%s): %s", start, final_end, exc)
            return {"status": "error", "error": str(exc)}
        except Exception as exc:
            logger.exception("Erro ao buscar custos Anthropic para Vera (%s/%s): %s", start, final_end, exc)
            return {"status": "error", "error": str(exc)}

        rows = []

        for bucket in payload.get("data") or []:
            bucket_start = bucket.get("starting_at") or bucket.get("start_time")
            if not bucket_start:
                continue
            bucket_date = date.fromisoformat(str(bucket_start)[:10])
            if bucket_date < start or bucket_date > final_end:
                continue

            for entry in bucket.get("results") or []:
                if workspace_id and entry.get("workspace_id") != workspace_id:
                    continue
                model = entry.get("model") or "[total]"
                currency = (entry.get("currency") or "USD").upper()
                raw_value = entry.get("amount") or entry.get("cost") or "0"
                raw_cost = Decimal(str(raw_value))
                cost_eur = cls._normalize_anthropic_amount(raw_cost, currency)
                rows.append(
                    {
                        "date": bucket_date,
                        "provider": "anthropic",
                        "model": model,
                        "cost_eur": cost_eur,
                        "raw_payload": entry,
                    }
                )

        cls._replace_provider_range(start=start, end=final_end, provider="anthropic", rows=rows)
        logger.info("Anthropic Vera sync %s/%s: %d linhas gravadas", start, final_end, len(rows))
        return {"status": "ok", "rows": len(rows)}

    @classmethod
    def _sync_provider_range(cls, *, provider: str, start: date, end: date, force: bool, sync_fn):
        cache_key = cls._sync_cache_key(provider, start, end)
        cooldown_key = cls._sync_cooldown_key(provider)
        lock_key = cls._sync_lock_key(provider)

        if not force:
            cached = cache.get(cache_key)
            if cached:
                return {**cached, "cached": True}

        cooldown = cache.get(cooldown_key)
        if cooldown and not force:
            return {
                "status": "skipped_cooldown",
                "error": cooldown,
                "cached": True,
            }

        lock_ttl = min(cls.cache_seconds(), 120)
        if not cache.add(lock_key, "1", timeout=lock_ttl):
            return {"status": "skipped_in_progress", "cached": True}

        try:
            result = sync_fn(start, end)
            status = result.get("status")
            if status == "ok":
                cache.set(cache_key, result, timeout=cls.cache_seconds())
            elif status in {"error", "rate_limited"}:
                cache.set(
                    cooldown_key,
                    result.get("error") or "Provider sync failed.",
                    timeout=cls.error_cooldown_seconds(),
                )
            return result
        finally:
            cache.delete(lock_key)

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

    @staticmethod
    def _delete_stale_records(target_date: date, provider: str, valid_models: set[str]) -> None:
        queryset = VeraUsageRecord.objects.filter(date=target_date, provider=provider)
        if valid_models:
            queryset = queryset.exclude(model__in=valid_models)
        queryset.delete()

    @classmethod
    def _replace_provider_range(
        cls,
        *,
        start: date,
        end: date,
        provider: str,
        rows: list[dict],
    ) -> None:
        VeraUsageRecord.objects.filter(
            date__gte=start,
            date__lte=end,
            provider=provider,
        ).delete()
        for row in rows:
            cls._upsert_record(
                target_date=row["date"],
                provider=row["provider"],
                model=row["model"],
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost_eur=row["cost_eur"],
                raw_payload=row.get("raw_payload") or {},
            )

    @staticmethod
    def cache_seconds() -> int:
        return int(getattr(settings, "VERA_COST_SYNC_CACHE_SECONDS", 900))

    @staticmethod
    def error_cooldown_seconds() -> int:
        return int(getattr(settings, "VERA_COST_SYNC_ERROR_COOLDOWN_SECONDS", 900))

    @staticmethod
    def anthropic_report_lag_days() -> int:
        return max(0, int(getattr(settings, "VERA_ANTHROPIC_COST_REPORT_LAG_DAYS", 0)))

    @staticmethod
    def anthropic_cost_report_limit() -> int:
        configured = int(getattr(settings, "VERA_ANTHROPIC_COST_REPORT_LIMIT", 31))
        return max(1, min(configured, 31))

    @classmethod
    def _anthropic_last_available_date(cls) -> date:
        return date.today() - timedelta(days=cls.anthropic_report_lag_days())

    @staticmethod
    def _fetch_anthropic_cost_report(headers: dict, params: list) -> dict:
        all_buckets = []
        next_page = None
        while True:
            page_params = list(params)
            if next_page:
                page_params.append(("page", next_page))
            resp = requests.get(
                ANTHROPIC_COST_URL,
                headers=headers,
                params=page_params,
                timeout=30,
            )
            resp.raise_for_status()
            payload = resp.json()
            all_buckets.extend(payload.get("data") or [])
            next_page = payload.get("next_page")
            if not payload.get("has_more") or not next_page:
                return {
                    **payload,
                    "data": all_buckets,
                }

    @staticmethod
    def _normalize_anthropic_amount(amount: Decimal, currency: str) -> Decimal:
        # Anthropic cost_report returns monetary amounts in minor units.
        # For USD, "123.45" means $1.23.
        if currency.upper() == "USD":
            amount = amount / Decimal("100")
        return amount.quantize(Decimal("0.000001"), ROUND_HALF_UP)

    @staticmethod
    def _anthropic_rate_limit_payload(response) -> Optional[dict]:
        if response is None or response.status_code != 429:
            return None

        rate_limit_headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() == "retry-after" or key.lower().startswith("anthropic-ratelimit-")
        }
        return {
            "status": "rate_limited",
            "error": "Anthropic cost_report rate limit exceeded.",
            "retry_after": response.headers.get("Retry-After"),
            "rate_limit_headers": rate_limit_headers,
        }

    @staticmethod
    def _sync_cache_key(provider: str, start: date, end: date) -> str:
        return f"vera-cost-sync:{provider}:{start.isoformat()}:{end.isoformat()}"

    @staticmethod
    def _sync_cooldown_key(provider: str) -> str:
        return f"vera-cost-sync:{provider}:cooldown"

    @staticmethod
    def _sync_lock_key(provider: str) -> str:
        return f"vera-cost-sync:{provider}:lock"
