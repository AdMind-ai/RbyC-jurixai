from django.core.management.base import BaseCommand, CommandError

from integrations.models import IntegrationClient
from integrations.services.document_index_sync import sync_client_document_index


class Command(BaseCommand):
    help = "Sync S3 document metadata into DocumentIndex for integration clients."

    def add_arguments(self, parser):
        parser.add_argument(
            "--client-id",
            type=int,
            help="Sync only one IntegrationClient id.",
        )
        parser.add_argument(
            "--customer-code",
            type=str,
            help="Sync only one IntegrationClient customer_code.",
        )
        parser.add_argument(
            "--deactivate-missing",
            action="store_true",
            help="Mark documents not found in S3 as inactive (default behavior).",
        )
        parser.add_argument(
            "--keep-missing-active",
            action="store_true",
            help="Do not deactivate indexed documents missing from S3 during sync.",
        )

    def handle(self, *args, **options):
        clients = IntegrationClient.objects.filter(active=True)
        if options.get("client_id"):
            clients = clients.filter(id=options["client_id"])
        if options.get("customer_code"):
            clients = clients.filter(customer_code=options["customer_code"])

        if not clients.exists():
            raise CommandError("No active integration clients found for sync.")

        for client in clients:
            result = sync_client_document_index(
                client=client,
                deactivate_missing=not options["keep_missing_active"],
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Synced client=%s created=%s updated=%s deactivated=%s elapsed=%.2fs"
                    % (
                        result.customer_code,
                        result.created_count,
                        result.updated_count,
                        result.deactivated_count,
                        result.elapsed_seconds,
                    )
                )
            )
