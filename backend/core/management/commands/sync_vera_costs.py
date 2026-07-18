"""
Management command: sync_vera_costs
====================================
Busca os custos diários de Agente Vera na OpenAI e Anthropic
e grava em VeraUsageRecord.

Exemplos de uso:
  # Hoje
  python manage.py sync_vera_costs

  # Data específica
  python manage.py sync_vera_costs --date 2026-07-15

  # Intervalo (últimos 7 dias)
  python manage.py sync_vera_costs --start 2026-07-10 --end 2026-07-17

  # Só OpenAI ou só Anthropic
  python manage.py sync_vera_costs --provider openai
  python manage.py sync_vera_costs --provider anthropic

Ideal para executar via cron diariamente:
  0 6 * * * cd /app && python manage.py sync_vera_costs >> /var/log/vera_sync.log 2>&1
"""
import json
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from core.services.vera_cost_sync_service import VeraCostSyncService


class Command(BaseCommand):
    help = "Sincroniza custos diários do Agente Vera (OpenAI + Anthropic) para VeraUsageRecord."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Data a sincronizar no formato YYYY-MM-DD (padrão: hoje).",
        )
        parser.add_argument(
            "--start",
            type=str,
            default=None,
            help="Início do intervalo YYYY-MM-DD (usar com --end).",
        )
        parser.add_argument(
            "--end",
            type=str,
            default=None,
            help="Fim do intervalo YYYY-MM-DD (usar com --start).",
        )
        parser.add_argument(
            "--provider",
            type=str,
            choices=["openai", "anthropic", "all"],
            default="all",
            help="Provider a sincronizar (padrão: all).",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Sincronizar os últimos N dias (alternativa a --start/--end).",
        )

    def handle(self, *args, **options):
        provider = options["provider"]

        # Determina o intervalo de datas
        if options["days"]:
            end_date   = date.today()
            start_date = end_date - timedelta(days=options["days"] - 1)
        elif options["start"] and options["end"]:
            try:
                start_date = date.fromisoformat(options["start"])
                end_date   = date.fromisoformat(options["end"])
            except ValueError as exc:
                raise CommandError(f"Data inválida: {exc}") from exc
        elif options["date"]:
            try:
                start_date = end_date = date.fromisoformat(options["date"])
            except ValueError as exc:
                raise CommandError(f"Data inválida: {exc}") from exc
        else:
            start_date = end_date = date.today()

        if start_date > end_date:
            raise CommandError("--start deve ser anterior ou igual a --end.")

        self.stdout.write(
            self.style.NOTICE(
                f"Sincronizando Vera costs [{start_date} → {end_date}] provider={provider}"
            )
        )

        if provider == "all":
            result = VeraCostSyncService.sync_range(start_date, end_date, force=True)
        elif provider == "openai":
            result = {"openai": VeraCostSyncService._sync_openai_range(start_date, end_date)}
        else:
            result = {
                "anthropic": VeraCostSyncService._sync_anthropic_range(start_date, end_date)
            }

        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=False, default=str))

        self.stdout.write(self.style.SUCCESS("✓ Sync concluído."))
