from django.core.management.base import BaseCommand

from integrations.services.document_preview import (
    build_document_previews_in_batches,
    build_missing_document_previews,
)


class Command(BaseCommand):
    help = "Build text previews for indexed integration documents."

    def add_arguments(self, parser):
        parser.add_argument(
            "--customer-code",
            type=str,
            default="",
            help="Build previews only for one IntegrationClient customer_code.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of documents to process.",
        )
        parser.add_argument(
            "--filename-contains",
            type=str,
            default="",
            help="Process only documents whose filename contains this value.",
        )
        parser.add_argument(
            "--path-contains",
            type=str,
            default="",
            help="Process only documents whose object key contains this value.",
        )
        parser.add_argument(
            "--document-type",
            type=str,
            default="",
            help="Process only documents with this inferred document_type.",
        )
        parser.add_argument(
            "--year",
            type=str,
            default="",
            help="Process only documents for this inferred year.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rebuild previews even when extraction_status is ready.",
        )
        parser.add_argument(
            "--all-batches",
            action="store_true",
            help="Process consecutive batches until the filtered document set is exhausted.",
        )
        parser.add_argument(
            "--max-batches",
            type=int,
            default=0,
            help="Optional cap for --all-batches. Use 0 for no cap.",
        )

    def handle(self, *args, **options):
        if options["all_batches"]:
            result = build_document_previews_in_batches(
                customer_code=options["customer_code"],
                filename_contains=options["filename_contains"],
                path_contains=options["path_contains"],
                document_type=options["document_type"],
                year=options["year"],
                batch_size=options["limit"],
                force=options["force"],
                max_batches=max(0, options["max_batches"]),
            )
        else:
            result = build_missing_document_previews(
                customer_code=options["customer_code"],
                filename_contains=options["filename_contains"],
                path_contains=options["path_contains"],
                document_type=options["document_type"],
                year=options["year"],
                limit=options["limit"],
                force=options["force"],
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Built document previews processed=%s skipped=%s failed=%s batches=%s attempted=%s"
                % (
                    result.processed_count,
                    result.skipped_count,
                    result.failed_count,
                    result.batch_count,
                    len(result.attempted_ids),
                )
            )
        )
