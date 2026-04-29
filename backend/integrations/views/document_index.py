import logging
import unicodedata
from time import perf_counter

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.models import DocumentIndex
from integrations.services.mcp_auth import decode_mcp_access_token


logger = logging.getLogger(__name__)


SEARCH_SYNONYMS = {
    "ad": ["amministratore delegato"],
    "amministratore delegato": ["ad"],
    "dg": ["direttore generale"],
    "direttore generale": ["dg"],
    "cda": ["consiglio di amministrazione"],
    "consiglio di amministrazione": ["cda"],
    "nomina": ["nominato", "nominata", "nomine", "nominare"],
    "deleghe": ["delega", "delegato", "delegati", "attribuzione di poteri"],
    "delega": ["deleghe", "delegato", "attribuzione di poteri"],
    "poteri": ["potere", "attribuiti", "attribuzioni"],
    "potere": ["poteri", "attribuiti", "attribuzioni"],
    "bilancio": ["bilanci", "dati di bilancio", "relazione finanziaria"],
}

FIELD_SCORE_WEIGHTS = {
    "filename": 12,
    "object_key": 11,
    "document_family": 9,
    "document_type": 8,
    "topic_tags": 8,
    "control_function_tags": 7,
    "year": 6,
    "text_preview": 4,
}

GOVERNANCE_QUERY_SIGNALS = {
    "amministratore delegato",
    "ad",
    "direttore generale",
    "dg",
    "nomina",
    "poteri",
    "potere",
    "deleghe",
    "delega",
}

FINANCIAL_QUERY_SIGNALS = {
    "bilancio",
    "bilanci",
    "dati di bilancio",
    "relazione finanziaria",
    "ultimi tre esercizi",
    "esercizi",
    "stato patrimoniale",
    "conto economico",
    "ricavi",
    "patrimonio netto",
    "utile",
    "perdita",
}


def resolve_internal_document_index_customer_code(request) -> str:
    authorization = (request.headers.get("Authorization") or "").strip()
    if not authorization.lower().startswith("bearer "):
        raise AuthenticationFailed("Missing MCP bearer token.")

    token = authorization[7:].strip()
    if not token:
        raise AuthenticationFailed("Missing MCP bearer token.")

    try:
        payload = decode_mcp_access_token(token)
    except Exception as exc:
        raise AuthenticationFailed("Invalid MCP bearer token.") from exc

    customer_code = str(payload.get("customer_code") or "").strip()
    if not customer_code:
        raise AuthenticationFailed("MCP bearer token missing customer_code.")

    query_customer_code = (request.query_params.get("customer_code") or "").strip()
    if query_customer_code and query_customer_code != customer_code:
        raise AuthenticationFailed("customer_code mismatch for MCP bearer token.")

    return customer_code


def parse_csv_query_values(value: str) -> list[str]:
    return [
        item.strip()
        for item in (value or "").split(",")
        if item and item.strip()
    ]


def normalize_search_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(normalized.casefold().split())


def search_variants(value: str) -> list[str]:
    cleaned = " ".join((value or "").strip().split())
    normalized = normalize_search_value(cleaned)
    variants = []

    def add_variant(item: str) -> None:
        candidate = " ".join((item or "").strip().split())
        normalized_candidate = normalize_search_value(candidate)
        for variant in [candidate, normalized_candidate]:
            if variant and variant not in variants:
                variants.append(variant)
            if variant:
                underscored = variant.replace(" ", "_")
                if underscored and underscored not in variants:
                    variants.append(underscored)
                spaced = variant.replace("_", " ")
                if spaced and spaced not in variants:
                    variants.append(spaced)

    add_variant(cleaned)
    add_variant(normalized)

    for key in [cleaned, normalized]:
        for synonym in SEARCH_SYNONYMS.get(key, []):
            add_variant(synonym)

    for source, synonym_list in SEARCH_SYNONYMS.items():
        if source and source in normalized:
            for synonym in synonym_list:
                add_variant(synonym)

    return variants


def query_terms_for_search(query: str) -> list[str]:
    cleaned = " ".join((query or "").strip().split())
    if not cleaned:
        return []

    normalized = normalize_search_value(cleaned)
    terms = []
    raw_tokens = [token for token in cleaned.split() if token]
    normalized_tokens = [token for token in normalized.split() if token]

    for item in [cleaned, normalized]:
        if item and item not in terms:
            terms.append(item)

    for token_list in [raw_tokens, normalized_tokens]:
        for token in token_list[:6]:
            if token and token not in terms:
                terms.append(token)
        for index in range(len(token_list) - 1):
            bigram = f"{token_list[index]} {token_list[index + 1]}"
            if bigram and bigram not in terms:
                terms.append(bigram)

    for known_phrase in SEARCH_SYNONYMS:
        if " " in known_phrase and known_phrase in normalized and known_phrase not in terms:
            terms.append(known_phrase)

    return terms[:10]


def build_query_profile(query_terms: list[str]) -> dict[str, bool]:
    normalized_terms = {
        normalize_search_value(term)
        for term in query_terms
        if normalize_search_value(term)
    }
    governance = any(
        signal in normalized_terms
        for signal in GOVERNANCE_QUERY_SIGNALS
    )
    financial = any(
        signal in normalized_terms
        for signal in FINANCIAL_QUERY_SIGNALS
    )
    return {
        "governance": governance,
        "financial": financial,
        "needs_ad": (
            "amministratore delegato" in normalized_terms or "ad" in normalized_terms
        ),
        "needs_dg": (
            "direttore generale" in normalized_terms or "dg" in normalized_terms
        ),
        "needs_poteri": (
            "poteri" in normalized_terms or "potere" in normalized_terms
        ),
        "needs_deleghe": (
            "deleghe" in normalized_terms or "delega" in normalized_terms
        ),
        "needs_nomina": "nomina" in normalized_terms,
        "needs_bilancio": (
            "bilancio" in normalized_terms or "bilanci" in normalized_terms
        ),
        "needs_relazione_finanziaria": "relazione finanziaria" in normalized_terms,
        "needs_multi_year_summary": (
            "ultimi tre esercizi" in normalized_terms or "esercizi" in normalized_terms
        ),
    }


def score_governance_alignment(normalized_fields: dict[str, str], profile: dict[str, bool]) -> int:
    if not profile.get("governance"):
        return 0

    combined_text = " ".join(normalized_fields.values())
    topic_tags = normalized_fields.get("topic_tags", "")
    document_family = normalized_fields.get("document_family", "")
    filename = normalized_fields.get("filename", "")
    object_key = normalized_fields.get("object_key", "")

    score = 0
    if document_family == "nomina":
        score += 18
    elif "nomina" in document_family:
        score += 10

    if profile.get("needs_nomina") and "nomina" in topic_tags:
        score += 12

    if profile.get("needs_ad"):
        if "amministratore_delegato" in topic_tags:
            score += 28
        if "amministratore delegato" in combined_text or " ad " in f" {combined_text} ":
            score += 20
        elif "direttore_generale" not in topic_tags:
            score -= 16

    if profile.get("needs_dg"):
        if "direttore_generale" in topic_tags:
            score += 28
        if "direttore generale" in combined_text or " dg " in f" {combined_text} ":
            score += 20
        elif "amministratore_delegato" not in topic_tags:
            score -= 16

    if profile.get("needs_poteri"):
        if "poteri" in topic_tags or "poteri" in combined_text or "attribuit" in combined_text:
            score += 18
        else:
            score -= 8

    if profile.get("needs_deleghe"):
        if "deleghe" in topic_tags or "delega" in combined_text or "deleghe" in combined_text:
            score += 18
        else:
            score -= 8

    generic_nomina_only = (
        "nomina" in topic_tags
        and "amministratore_delegato" not in topic_tags
        and "direttore_generale" not in topic_tags
        and "poteri" not in topic_tags
        and "deleghe" not in topic_tags
    )
    if generic_nomina_only:
        score -= 20

    governance_noise_markers = [
        "outsourcing",
        "compliancefunzione di controllo",
        "funzione di controllo",
        "condizioni generali",
    ]
    if any(marker in filename or marker in object_key for marker in governance_noise_markers):
        score -= 25

    return score


def score_financial_alignment(normalized_fields: dict[str, str], profile: dict[str, bool]) -> int:
    if not profile.get("financial"):
        return 0

    combined_text = " ".join(normalized_fields.values())
    topic_tags = normalized_fields.get("topic_tags", "")
    document_family = normalized_fields.get("document_family", "")
    document_type = normalized_fields.get("document_type", "")
    filename = normalized_fields.get("filename", "")
    object_key = normalized_fields.get("object_key", "")
    year = normalized_fields.get("year", "")

    score = 0
    if document_family == "bilancio":
        score += 26
    elif document_family == "relazione_finanziaria":
        score += 22
    elif "bilancio" in document_family or "relazione_finanziaria" in document_family:
        score += 14

    if document_type == "bilancio":
        score += 18
    elif document_type == "relazione_finanziaria":
        score += 16

    if "bilancio" in topic_tags:
        score += 16
    if "dati_finanziari" in topic_tags:
        score += 14

    if "bilancio" in combined_text:
        score += 12
    if "relazione finanziaria" in combined_text:
        score += 10

    if profile.get("needs_multi_year_summary") and year:
        try:
            numeric_year = int(year)
        except ValueError:
            numeric_year = 0
        if numeric_year >= 2022:
            score += 12
        elif numeric_year >= 2020:
            score += 8

    if profile.get("needs_bilancio") and "bilancio" not in combined_text and "bilancio" not in topic_tags:
        score -= 10

    financial_noise_markers = [
        "verbale",
        "convocazione",
        "funzione di controllo",
        "contestazioni",
        "consob",
    ]
    if any(marker in filename or marker in object_key for marker in financial_noise_markers):
        score -= 18

    return score


def score_document_match(
    document,
    query_terms: list[str],
    query_profile: dict[str, bool] | None = None,
) -> int:
    if not query_terms:
        return 0

    normalized_fields = {
        "filename": normalize_search_value(document.filename),
        "object_key": normalize_search_value(document.object_key),
        "document_type": normalize_search_value(document.document_type),
        "document_family": normalize_search_value(document.document_family),
        "topic_tags": normalize_search_value(document.topic_tags),
        "control_function_tags": normalize_search_value(document.control_function_tags),
        "year": normalize_search_value(document.year),
        "text_preview": normalize_search_value(document.text_preview),
    }

    score = 0
    matched_terms = 0
    for raw_term in query_terms:
        term_variants = [normalize_search_value(item) for item in search_variants(raw_term)]
        term_variants = [item for item in term_variants if item]
        term_matched = False
        for field_name, field_value in normalized_fields.items():
            if not field_value:
                continue
            field_weight = FIELD_SCORE_WEIGHTS[field_name]
            for variant in term_variants:
                if variant == field_value:
                    score += field_weight + 6
                    term_matched = True
                    break
                if variant in field_value:
                    score += field_weight
                    term_matched = True
                    break
            if term_matched:
                break
        if term_matched:
            matched_terms += 1

    score += matched_terms * 5
    effective_profile = query_profile or build_query_profile(query_terms)
    score += score_governance_alignment(normalized_fields, effective_profile)
    score += score_financial_alignment(normalized_fields, effective_profile)
    return score


def sort_documents_by_relevance(
    documents: list[DocumentIndex],
    query_terms: list[str],
) -> list[DocumentIndex]:
    if not query_terms:
        return documents

    query_profile = build_query_profile(query_terms)

    return sorted(
        documents,
        key=lambda document: (
            score_document_match(document, query_terms, query_profile),
            document.last_modified.isoformat() if document.last_modified else "",
            document.indexed_at.isoformat() if document.indexed_at else "",
        ),
        reverse=True,
    )


def build_document_search_filter(term: str, include_preview: bool = False) -> Q:
    search_filter = Q()
    for variant in search_variants(term):
        search_filter |= (
            Q(filename__icontains=variant)
            | Q(object_key__icontains=variant)
            | Q(document_type__icontains=variant)
            | Q(document_family__icontains=variant)
            | Q(topic_tags__icontains=variant)
            | Q(control_function_tags__icontains=variant)
            | Q(year__icontains=variant)
        )
        if include_preview:
            search_filter |= Q(text_preview__icontains=variant)
    return search_filter


@extend_schema(exclude=True)
class InternalDocumentIndexView(APIView):
    authentication_classes = []
    permission_classes = []

    class OutputSerializer(serializers.Serializer):
        key = serializers.CharField()
        filename = serializers.CharField()
        extension = serializers.CharField(allow_blank=True)
        size_bytes = serializers.IntegerField()
        last_modified = serializers.DateTimeField(allow_null=True)
        path = serializers.CharField()
        year = serializers.CharField(allow_blank=True)
        document_type = serializers.CharField()
        document_family = serializers.CharField()
        control_function_tags = serializers.CharField(allow_blank=True)
        topic_tags = serializers.CharField(allow_blank=True)
        text_preview = serializers.CharField(allow_blank=True)

    def get(self, request):
        started_at = perf_counter()
        expected_key = getattr(settings, "DOCUMENT_INDEX_API_KEY", None)
        provided_key = request.headers.get("X-Internal-API-Key")
        if not expected_key or provided_key != expected_key:
            return Response(
                {"detail": "Unauthorized internal document index request."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            customer_code = resolve_internal_document_index_customer_code(request)
        except AuthenticationFailed as exc:
            return Response(
                {"detail": str(exc.detail)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        query = (request.query_params.get("query") or "").strip()
        year = (request.query_params.get("year") or "").strip()
        document_type = (
            request.query_params.get("document_type") or ""
        ).strip()
        document_family = (
            request.query_params.get("document_family") or ""
        ).strip()
        control_function_tags = (
            request.query_params.get("control_function_tags") or ""
        ).strip()
        topic_tags = (request.query_params.get("topic_tags") or "").strip()
        extension = (request.query_params.get("extension") or "").strip().lower()
        filename_contains = (
            request.query_params.get("filename_contains") or ""
        ).strip()
        path_contains = (request.query_params.get("path_contains") or "").strip()
        sort_by = (request.query_params.get("sort_by") or "last_modified").strip()
        sort_order = (request.query_params.get("sort_order") or "desc").strip()

        try:
            limit = int(request.query_params.get("limit") or 200)
        except (TypeError, ValueError):
            limit = 200
        limit = max(1, min(limit, 300))

        documents = DocumentIndex.objects.select_related("client").filter(
            client__customer_code=customer_code,
            client__active=True,
            active=True,
        ).only(
            "object_key",
            "filename",
            "extension",
            "size_bytes",
            "last_modified",
            "year",
            "document_type",
            "document_family",
            "control_function_tags",
            "topic_tags",
            "text_preview",
            "indexed_at",
            "client__customer_code",
            "client__active",
        )

        if year:
            documents = documents.filter(year=year)

        if document_type:
            document_type_filter = Q()
            for raw_value in parse_csv_query_values(document_type) or [document_type]:
                for variant in search_variants(raw_value):
                    document_type_filter |= Q(document_type__icontains=variant)
            documents = documents.filter(document_type_filter)

        if document_family:
            document_family_filter = Q()
            for raw_value in parse_csv_query_values(document_family) or [document_family]:
                for variant in search_variants(raw_value):
                    document_family_filter |= Q(
                        document_family__icontains=variant
                    )
            documents = documents.filter(document_family_filter)

        if control_function_tags:
            control_function_filter = Q()
            for raw_value in parse_csv_query_values(control_function_tags) or [control_function_tags]:
                for variant in search_variants(raw_value):
                    control_function_filter |= Q(
                        control_function_tags__icontains=variant
                    )
            documents = documents.filter(control_function_filter)

        if topic_tags:
            topic_filter = Q()
            for raw_value in parse_csv_query_values(topic_tags) or [topic_tags]:
                for variant in search_variants(raw_value):
                    topic_filter |= Q(topic_tags__icontains=variant)
            documents = documents.filter(topic_filter)

        if extension:
            normalized_extension = (
                extension if extension.startswith(".") else f".{extension}"
            )
            documents = documents.filter(extension=normalized_extension)

        if filename_contains:
            filename_filter = Q()
            for variant in search_variants(filename_contains):
                filename_filter |= Q(filename__icontains=variant)
            documents = documents.filter(filename_filter)

        if path_contains:
            path_filter = Q()
            for variant in search_variants(path_contains):
                path_filter |= Q(object_key__icontains=variant)
            documents = documents.filter(path_filter)

        query_terms = query_terms_for_search(query)
        if query_terms:
            strict_documents = documents
            for term in query_terms:
                strict_documents = strict_documents.filter(
                    build_document_search_filter(term)
                )

            if strict_documents.exists() or len(query_terms) == 1:
                documents = strict_documents
            else:
                broad_filter = Q()
                for term in query_terms:
                    broad_filter |= build_document_search_filter(
                        term,
                        include_preview=True,
                    )
                documents = documents.filter(broad_filter)

        order_fields = {
            "last_modified": "last_modified",
            "size": "size_bytes",
            "filename": "filename",
        }
        order_field = order_fields.get(sort_by, "last_modified")
        if sort_order != "asc":
            order_field = f"-{order_field}"

        documents = list(documents.order_by(order_field, "-indexed_at")[:limit])
        documents = sort_documents_by_relevance(documents, query_terms)
        payload = [
            {
                "key": document.object_key,
                "filename": document.filename,
                "extension": document.extension,
                "size_bytes": document.size_bytes,
                "last_modified": document.last_modified,
                "path": document.object_key,
                "year": document.year,
                "document_type": document.document_type,
                "document_family": document.document_family,
                "control_function_tags": document.control_function_tags,
                "topic_tags": document.topic_tags,
                "text_preview": document.text_preview,
            }
            for document in documents
        ]

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "[document_index] request_completed duration_ms=%s customer_code=%s returned_documents=%s limit=%s query=%s year=%s document_type=%s document_family=%s control_function_tags=%s topic_tags=%s extension=%s filename_contains=%s path_contains=%s sort_by=%s sort_order=%s",
            duration_ms,
            customer_code,
            len(payload),
            limit,
            query or "<empty>",
            year or "<empty>",
            document_type or "<empty>",
            document_family or "<empty>",
            control_function_tags or "<empty>",
            topic_tags or "<empty>",
            extension or "<empty>",
            filename_contains or "<empty>",
            path_contains or "<empty>",
            sort_by,
            sort_order,
        )
        return JsonResponse(payload, safe=False)
