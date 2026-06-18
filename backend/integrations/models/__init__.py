import hashlib
import re
from datetime import datetime
import unicodedata

from django.db import models
from django.utils import timezone


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256((raw_key or "").encode("utf-8")).hexdigest()


class IntegrationClient(models.Model):
    customer_code = models.CharField(max_length=128, unique=True)
    client_name = models.CharField(max_length=255)
    bucket_name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(blank=True, null=True)
    sync_status = models.CharField(max_length=32, default="idle")
    sync_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["active", "customer_code"]),
            models.Index(fields=["bucket_name"]),
        ]

    def __str__(self):
        return f"{self.client_name} ({self.customer_code})"


class IntegrationApiKey(models.Model):
    client = models.ForeignKey(
        IntegrationClient,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    key_hash = models.CharField(max_length=64, unique=True)
    active = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)
    environment = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["active", "key_hash"]),
            models.Index(fields=["client", "active"]),
        ]

    @classmethod
    def hash_key(cls, raw_key: str) -> str:
        return hash_api_key(raw_key)

    def __str__(self):
        return f"{self.client} - {self.description or self.environment or 'API key'}"


class IntegrationUsageTool(models.TextChoices):
    RICERCA_DOCUMENTALE = "RICERCA_DOCUMENTALE", "Ricerca documentale"


class IntegrationUsageRecord(models.Model):
    client = models.ForeignKey(
        IntegrationClient,
        on_delete=models.CASCADE,
        related_name="usage_records",
        null=True,
        blank=True,
    )
    api_key = models.ForeignKey(
        IntegrationApiKey,
        on_delete=models.SET_NULL,
        related_name="usage_records",
        null=True,
        blank=True,
    )
    tool = models.CharField(
        max_length=64,
        choices=IntegrationUsageTool.choices,
        default=IntegrationUsageTool.RICERCA_DOCUMENTALE,
    )
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    conversation_id = models.CharField(max_length=255, blank=True)
    auth_mode = models.CharField(max_length=64, blank=True)
    auth_identifier = models.CharField(max_length=255, blank=True)
    intent_type = models.CharField(max_length=128, blank=True)
    prompt_length = models.PositiveIntegerField(default=0)
    model_input_length = models.PositiveIntegerField(default=0)
    response_text_length = models.PositiveIntegerField(default=0)
    documents_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tool", "occurred_at"]),
            models.Index(fields=["client", "occurred_at"]),
            models.Index(fields=["api_key", "occurred_at"]),
        ]
        ordering = ["-occurred_at", "-created_at"]

    def __str__(self):
        client_label = getattr(self.client, "customer_code", "") or "legacy"
        return f"{self.tool} - {client_label} - {self.occurred_at.isoformat()}"


class DocumentIndex(models.Model):
    STATUS_PENDING = "pending"
    STATUS_READY = "ready"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_READY, "Ready"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    client = models.ForeignKey(
        IntegrationClient,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    bucket_name = models.CharField(max_length=255)
    object_key = models.TextField()
    filename = models.CharField(max_length=512)
    extension = models.CharField(max_length=32, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    s3_last_modified = models.DateTimeField(blank=True, null=True)
    last_modified = models.DateTimeField(blank=True, null=True)
    document_date = models.DateField(blank=True, null=True)
    etag = models.CharField(max_length=128, blank=True)
    year = models.CharField(max_length=4, blank=True)
    document_type = models.CharField(max_length=64, default="altro")
    document_family = models.CharField(max_length=64, default="altro")
    control_function_tags = models.CharField(max_length=128, blank=True)
    topic_tags = models.CharField(max_length=256, blank=True)
    text_preview = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)
    search_text = models.TextField(blank=True)
    extraction_status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    extraction_error = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    indexed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "object_key"],
                name="unique_document_index_client_object_key",
            )
        ]
        indexes = [
            models.Index(fields=["client", "active", "document_type"]),
            models.Index(fields=["client", "active", "document_family"]),
            models.Index(fields=["client", "active", "control_function_tags"]),
            models.Index(fields=["client", "active", "topic_tags"]),
            models.Index(fields=["client", "active", "year"]),
            models.Index(fields=["client", "active", "document_date"]),
            models.Index(fields=["client", "active", "s3_last_modified"]),
            models.Index(fields=["client", "active", "last_modified"]),
            models.Index(fields=["bucket_name"]),
        ]

    def __str__(self):
        return self.object_key

    @staticmethod
    def infer_year(object_key: str) -> str:
        value = object_key or ""

        prioritized_patterns = [
            r"(?:31|30|29|28|27|26|25|24|23|22|21|20|19|18|17|16|15|14|13|12|11|10|09|08|07|06|05|04|03|02|01)[._/-](?:12|11|10|09|08|07|06|05|04|03|02|01)[._/-](20\d{2})",
            r"(?:esercizio|bilancio|annual[-_ ]report|financial[-_ ]report)[^0-9]{0,12}(20\d{2})",
            r"(?:^|/)(20\d{2})(?:[./_-]|/|$)",
        ]
        for pattern in prioritized_patterns:
            match = re.search(pattern, value, flags=re.IGNORECASE)
            if match:
                return match.group(1)

        fallback_matches = re.findall(r"(?<!\d)(20\d{2})(?!\d)", value)
        if fallback_matches:
            return fallback_matches[0]

        return ""

    @staticmethod
    def infer_document_date(object_key: str):
        value = object_key or ""
        italian_months = {
            "gennaio": 1,
            "gen": 1,
            "febbraio": 2,
            "feb": 2,
            "marzo": 3,
            "mar": 3,
            "aprile": 4,
            "apr": 4,
            "maggio": 5,
            "mag": 5,
            "giugno": 6,
            "giu": 6,
            "luglio": 7,
            "lug": 7,
            "agosto": 8,
            "ago": 8,
            "settembre": 9,
            "sett": 9,
            "set": 9,
            "ottobre": 10,
            "ott": 10,
            "novembre": 11,
            "nov": 11,
            "dicembre": 12,
            "dic": 12,
        }
        month_pattern = "|".join(sorted(italian_months, key=len, reverse=True))
        text_date_match = re.search(
            rf"(?<!\d)(\d{{1,2}})[\s._/-]+({month_pattern})[\s._/-]+(20\d{{2}})(?!\d)",
            value,
            flags=re.IGNORECASE,
        )
        if text_date_match:
            day = int(text_date_match.group(1))
            month = italian_months[text_date_match.group(2).lower()]
            year = int(text_date_match.group(3))
            try:
                return datetime(year, month, day).date()
            except ValueError:
                pass

        date_patterns = (
            (lambda groups: f"{groups[0]}{groups[1]}{groups[2]}", "%d%m%Y", r"(?<!\d)(\d{2})(\d{2})(20\d{2})(?!\d)"),
            (lambda groups: f"{groups[0]}-{groups[1]}-{groups[2]}", "%d-%m-%Y", r"(?<!\d)(\d{2})[-_./](\d{2})[-_./](20\d{2})(?!\d)"),
            (lambda groups: f"{groups[0]}{groups[1]}{groups[2]}", "%Y%m%d", r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)"),
        )

        for builder, date_format, pattern in date_patterns:
            match = re.search(pattern, value, flags=re.IGNORECASE)
            if not match:
                continue
            try:
                return datetime.strptime(builder(match.groups()), date_format).date()
            except ValueError:
                continue

        return None

    @staticmethod
    def infer_document_type(object_key: str) -> str:
        value = (object_key or "").lower()
        type_patterns = [
            ("verbale", ["verbale", "verbali"]),
            ("convocazione", ["convocazione", "convocazioni"]),
            ("estratto", ["estratto"]),
            ("nomina", ["nomina", "nomin", "direttore generale", "amministratore delegato"]),
            ("regolamento", ["regolamento", "regolamenti"]),
            ("relazione", ["relazione", "relazioni", "rso"]),
            ("bilancio", ["bilancio", "bilanci"]),
            ("relazione_finanziaria", ["relazione finanziaria", "financial report", "annual report"]),
            ("policy", ["policy", "politica", "policies"]),
            ("procedura", ["procedura", "procedure"]),
            ("materiali", ["materiali", "documenti"]),
            ("email", [".eml"]),
        ]
        for document_type, patterns in type_patterns:
            if any(pattern in value for pattern in patterns):
                return document_type
        return "altro"

    @staticmethod
    def infer_document_family(object_key: str) -> str:
        value = (object_key or "").lower()

        if any(
            pattern in value
            for pattern in [
                "direttore generale",
                "amministratore delegato",
                " nomina ",
                "/nomina",
                "nomina/",
                "poteri ad",
                "poteri dg",
                "poteri ad e dg",
            ]
        ):
            return "nomina"

        if (
            "verbale" in value
            and (
                "cda" in value
                or "consiglio di amministrazione" in value
            )
        ):
            return "verbale_cda"

        if (
            "estratto" in value
            and (
                "cda" in value
                or "consiglio di amministrazione" in value
            )
        ):
            return "estratto_cda"

        if "bilancio" in value:
            return "bilancio"

        if any(
            pattern in value
            for pattern in [
                "relazione finanziaria",
                "financial report",
                "annual report",
            ]
        ):
            return "relazione_finanziaria"

        if (
            ("relazione" in value and "struttura organizzativa" in value)
            or re.search(r"(^|[\W_])rso([\W_]|$)", value, flags=re.IGNORECASE)
        ):
            return "relazione_struttura_organizzativa"

        if any(
            pattern in value
            for pattern in [
                "internal audit",
                "audit",
                "compliance",
                "risk management",
                "relazione ia",
                "relazione rm",
                "relazione cpl",
                "antiriciclaggio",
                "aml",
            ]
        ):
            return "report_controlli"

        if (
            "policy" in value
            and any(
                pattern in value
                for pattern in [
                    "invest",
                    "portafogli",
                    "delega",
                ]
            )
        ):
            return "policy_investimento"

        if any(pattern in value for pattern in ["materiali", "documenti"]):
            return "materiale_supporto"

        return "altro"

    @staticmethod
    def infer_control_function_tags(
        object_key: str,
        text_preview: str = "",
    ) -> str:
        value = " ".join(
            item for item in [(object_key or "").lower(), (text_preview or "").lower()] if item
        )
        tags = []

        tag_patterns = [
            ("risk", ["risk management", "risk", "rm"]),
            ("compliance", ["compliance", "cpl"]),
            ("internal_audit", ["internal audit", "audit", "ia"]),
            ("aml", ["aml", "antiriciclaggio"]),
        ]

        for tag, patterns in tag_patterns:
            if any(pattern in value for pattern in patterns):
                tags.append(tag)

        return ",".join(dict.fromkeys(tags))

    @staticmethod
    def infer_topic_tags(
        object_key: str,
        text_preview: str = "",
    ) -> str:
        object_value = (object_key or "").lower()
        preview_value = (text_preview or "").lower()
        value = " ".join(item for item in [object_value, preview_value] if item)
        tags = []

        def contains_pattern(pattern: str) -> bool:
            return re.search(pattern, value, flags=re.IGNORECASE) is not None

        def preview_without_recipient_blocks(text: str) -> str:
            if not text:
                return ""
            lines = text.splitlines()
            filtered_lines = []
            skip_block = False
            for raw_line in lines:
                line = raw_line.strip().lower()
                if not line:
                    skip_block = False
                    filtered_lines.append(raw_line)
                    continue
                if (
                    line.startswith("destinatari per competenza")
                    or line.startswith("destinatari per presa visione")
                    or line.startswith("destinatari:")
                ):
                    skip_block = True
                    continue
                if skip_block:
                    if any(
                        line.startswith(prefix)
                        for prefix in [
                            "data di completamento",
                            "data di avvio",
                            "team:",
                            "approvato da:",
                            "1.",
                            "1 ",
                            "indice",
                            "sommario",
                            "executive summary",
                            "valutazione sintetica",
                            "motivazioni:",
                            "piano degli interventi:",
                        ]
                    ):
                        skip_block = False
                    else:
                        continue
                filtered_lines.append(raw_line)
            return "\n".join(filtered_lines).lower()

        semantic_preview = preview_without_recipient_blocks(preview_value)
        semantic_value = " ".join(item for item in [object_value, semantic_preview] if item)

        governance_context = any(
            marker in semantic_value
            for marker in [
                "nomina",
                "nominato",
                "nominare",
                "poteri",
                "potere",
                "attribuit",
                "attribuzione",
                "deleghe",
                "consiglio di amministrazione",
                " cda ",
                "organi sociali",
            ]
        )
        ad_explicit = (
            "amministratore delegato" in object_value
            or "amministratore delegato" in semantic_preview
            or re.search(r"\ba\.?d\.?\b", semantic_value, flags=re.IGNORECASE) is not None
        )
        dg_explicit = (
            "direttore generale" in object_value
            or "direttore generale" in semantic_preview
            or re.search(r"\bdg\b", semantic_value, flags=re.IGNORECASE) is not None
        )

        if ad_explicit and governance_context:
            tags.append("amministratore_delegato")

        if dg_explicit and governance_context:
            tags.append("direttore_generale")

        if (
            any(
                marker in semantic_value
                for marker in [
                    "deleghe",
                    "attribuzione di poteri",
                    "attribuzione dei poteri",
                ]
            )
            or (
                "delega" in semantic_value
                and (
                    ad_explicit
                    or dg_explicit
                    or "nomina" in semantic_value
                    or "poteri" in semantic_value
                )
            )
        ):
            tags.append("deleghe")

        tag_patterns = [
            ("consob", ["consob"]),
            ("contestazioni", ["contestazione", "contestazioni"]),
            ("nomina", ["nomina", "nominato", "nominare"]),
            ("poteri", ["poteri", "potere"]),
            ("bilancio", ["bilancio"]),
            (
                "dati_finanziari",
                [
                    "stato patrimoniale",
                    "conto economico",
                    "utile",
                    "perdita",
                    "ricavi",
                    "patrimonio netto",
                    "dati di bilancio",
                    "relazione finanziaria",
                ],
            ),
            (
                "market_abuse",
                ["market abuse", "abuso di mercato"],
            ),
            (
                "struttura_organizzativa",
                [
                    "struttura organizzativa",
                    "relazione sulla struttura organizzativa",
                ],
            ),
            (
                "politica_investimento",
                [
                    "politica di investimento",
                    "politiche di investimento",
                    "policy in materia di investimenti",
                    "policy di investimento",
                    "politica di gestione",
                    "investment policy",
                    "asset allocation",
                    "linee guida di investimento",
                ],
            ),
            (
                "portafogli_delega",
                [
                    "portafogli in delega",
                    "portafogli delega",
                    "portafogli gestiti",
                    "gestioni delegate",
                    "gestione dei portafogli",
                    "gestione portafogli",
                    "gestioni patrimoniali",
                    "mandati di gestione",
                    "mandati",
                    "delegated portfolios",
                    "portfolio management",
                ],
            ),
            ("rimedi", ["rimedi", "remediation", "azioni correttive"]),
            (
                "rilievi",
                [
                    "rilievi",
                    "finding",
                    "findings",
                    "raccomandazioni",
                    "criticita",
                    "criticità",
                    "osservazioni",
                    "anomalie",
                    "non conformita",
                    "non conformità",
                    "issues",
                ],
            ),
            (
                "rimedi",
                [
                    "piano di rimedio",
                    "piani di rimedio",
                    "azioni di rimedio",
                    "piano di azione",
                    "piani di azione",
                    "mitigazioni",
                    "follow-up",
                ],
            ),
        ]

        for tag, patterns in tag_patterns:
            if any(pattern in value for pattern in patterns):
                tags.append(tag)

        if re.search(r"(^|[\W_])rso([\W_]|$)", value, flags=re.IGNORECASE):
            tags.append("struttura_organizzativa")

        return ",".join(dict.fromkeys(tags))
