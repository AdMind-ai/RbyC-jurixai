import json
from urllib.parse import urlencode

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rest_framework.test import APIRequestFactory

from integrations.models import IntegrationClient
from integrations.services.mcp_auth import build_mcp_access_token
from integrations.views.document_index import InternalDocumentIndexView


SCENARIO_SUITES = {
    "canary": [
        {
            "name": "direttore_generale_nomina",
            "query": "direttore generale nomin nomina",
            "document_family": "verbale_cda,estratto_cda,nomina",
            "topic_tags": "direttore_generale,nomina",
        },
        {
            "name": "amministratore_delegato_poteri",
            "query": "amministratore delegato nomin nomina poteri deleg",
            "document_family": "verbale_cda,estratto_cda,nomina",
            "topic_tags": "nomina,poteri,deleghe",
        },
        {
            "name": "bilancio_ultimi_tre_esercizi",
            "query": "bilancio dati di bilancio ultimi tre esercizi sintesi",
            "document_family": "bilancio,relazione_finanziaria",
            "topic_tags": "bilancio,dati_finanziari",
        },
    ],
    "governance": [
        {
            "name": "ad_nomina_poteri",
            "query": "amministratore delegato nomin nomina poteri deleg",
            "document_family": "verbale_cda,estratto_cda,nomina",
            "topic_tags": "nomina,poteri,deleghe",
        },
        {
            "name": "dg_nomina",
            "query": "direttore generale nomin nomina",
            "document_family": "verbale_cda,estratto_cda,nomina",
            "topic_tags": "direttore_generale,nomina",
        },
    ],
    "controls": [
        {
            "name": "rilievi_rimedi_2025",
            "query": "rilievi rimedi risk compliance internal audit",
            "year": "2025",
            "document_family": "report_controlli",
            "control_function_tags": "risk,compliance,internal_audit",
            "topic_tags": "rilievi,rimedi",
        },
        {
            "name": "politica_investimento_2025",
            "query": "politica investimento portafogli delega",
            "year": "2025",
            "document_family": "policy_investimento,verbale_cda,estratto_cda",
            "topic_tags": "politica_investimento,portafogli_delega",
        },
        {
            "name": "risk_management_coinvolgimento_2025",
            "query": "risk management politica investimento cda",
            "year": "2025",
            "document_family": "verbale_cda,estratto_cda,report_controlli",
            "control_function_tags": "risk",
            "topic_tags": "politica_investimento",
        },
    ],
    "comparisons": [
        {
            "name": "struttura_organizzativa_2025_vs_2024",
            "query": "struttura organizzativa modifica confronto",
            "document_family": "relazione_struttura_organizzativa",
            "topic_tags": "struttura_organizzativa",
        },
        {
            "name": "consob_contestazioni_cda",
            "query": "consob contestazioni cda",
            "document_family": "verbale_cda,estratto_cda",
            "topic_tags": "consob,contestazioni",
        },
    ],
}
SCENARIO_SUITES["full"] = (
    SCENARIO_SUITES["governance"]
    + [SCENARIO_SUITES["canary"][2]]
    + SCENARIO_SUITES["controls"]
    + SCENARIO_SUITES["comparisons"]
)


class Command(BaseCommand):
    help = "Probe the internal document index directly, without going through the MCP/OpenAI flow."

    def add_arguments(self, parser):
        parser.add_argument(
            "--customer-code",
            type=str,
            required=True,
            help="IntegrationClient customer_code to probe.",
        )
        parser.add_argument(
            "--suite",
            type=str,
            choices=sorted(SCENARIO_SUITES.keys()),
            default="canary",
            help="Predefined probe suite. Defaults to canary (3 cheap checks).",
        )
        parser.add_argument(
            "--query",
            type=str,
            default="",
            help="Run a single custom probe query instead of a predefined suite.",
        )
        parser.add_argument("--year", type=str, default="")
        parser.add_argument("--document-type", type=str, default="")
        parser.add_argument("--document-family", type=str, default="")
        parser.add_argument("--control-function-tags", type=str, default="")
        parser.add_argument("--topic-tags", type=str, default="")
        parser.add_argument("--filename-contains", type=str, default="")
        parser.add_argument("--path-contains", type=str, default="")
        parser.add_argument("--extension", type=str, default="")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument(
            "--show-results",
            action="store_true",
            help="Print top returned documents for each probe.",
        )

    def handle(self, *args, **options):
        client = IntegrationClient.objects.filter(
            customer_code=options["customer_code"],
            active=True,
        ).first()
        if not client:
            raise CommandError("No active IntegrationClient found for this customer_code.")

        api_key = getattr(settings, "DOCUMENT_INDEX_API_KEY", "")
        if not api_key:
            raise CommandError("DOCUMENT_INDEX_API_KEY is not configured.")

        token = build_mcp_access_token(client)
        probes = self._build_probes(options)

        self.stdout.write(
            self.style.NOTICE(
                "Running document index probe customer_code=%s suite=%s probes=%s"
                % (client.customer_code, options["suite"], len(probes))
            )
        )

        successes = 0
        for probe in probes:
            status_code, documents = self._run_probe(
                token=token,
                api_key=api_key,
                params=probe,
            )
            returned = len(documents)
            if status_code == 200 and returned > 0:
                successes += 1

            self.stdout.write(
                "%s status=%s returned=%s query=%s"
                % (
                    probe["name"],
                    status_code,
                    returned,
                    probe.get("query") or "<empty>",
                )
            )

            if options["show_results"] and documents:
                for index, document in enumerate(documents[:3], start=1):
                    self.stdout.write(
                        "  %s. %s | family=%s | topics=%s | year=%s"
                        % (
                            index,
                            document.get("filename", "<no filename>"),
                            document.get("document_family", "<empty>"),
                            document.get("topic_tags", "<empty>"),
                            document.get("year", "<empty>"),
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Probe summary matched=%s/%s"
                % (successes, len(probes))
            )
        )

    def _build_probes(self, options):
        if options["query"]:
            return [
                {
                    "name": "custom",
                    "query": options["query"],
                    "year": options["year"],
                    "document_type": options["document_type"],
                    "document_family": options["document_family"],
                    "control_function_tags": options["control_function_tags"],
                    "topic_tags": options["topic_tags"],
                    "filename_contains": options["filename_contains"],
                    "path_contains": options["path_contains"],
                    "extension": options["extension"],
                    "limit": options["limit"],
                }
            ]

        probes = []
        for scenario in SCENARIO_SUITES[options["suite"]]:
            merged = dict(scenario)
            merged["limit"] = options["limit"]
            probes.append(merged)
        return probes

    def _run_probe(self, token: str, api_key: str, params: dict):
        factory = APIRequestFactory()
        request_params = {
            key: value
            for key, value in params.items()
            if key != "name" and value not in ("", None)
        }
        path = "/api/integrations/v1/internal/document-index/"
        querystring = urlencode(request_params)
        request = factory.get(
            f"{path}?{querystring}" if querystring else path,
            data=request_params,
            HTTP_X_INTERNAL_API_KEY=api_key,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        response = InternalDocumentIndexView.as_view()(request)
        if hasattr(response, "render"):
            response.render()

        try:
            documents = json.loads(response.content.decode("utf-8"))
        except Exception:
            documents = []
        return response.status_code, documents
