import re
from dataclasses import dataclass

from django.db.models import F

from integrations.models import DocumentIndex
from integrations.services.document_index_search import (
    query_terms_for_search,
    search_variants,
)

from core.services.document_retrieval.query_hints import build_query_hints
from core.services.document_retrieval.intent_classifier import IntentClassification
from core.services.document_retrieval.retrieval_strategies import RetrievalStrategy


@dataclass(frozen=True)
class PresearchCandidate:
    key: str
    filename: str
    document_family: str
    topic_tags: str
    document_date: str
    s3_last_modified: str
    text_preview: str
    sibling_signature: str


@dataclass(frozen=True)
class RetrievalGuidanceCandidates:
    presearch_candidates: list[PresearchCandidate]
    related_approval_candidates: list[PresearchCandidate]


def _normalize_presearch_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def should_run_presearch(
    *,
    user_input: str,
    intent_classification: IntentClassification,
    retrieval_strategy: RetrievalStrategy,
) -> bool:
    has_structured_preferences = any(
        (
            retrieval_strategy.preferred_document_families,
            retrieval_strategy.preferred_topic_tags,
            retrieval_strategy.preferred_control_functions,
            retrieval_strategy.preferred_filename_contains,
            retrieval_strategy.preferred_sort_by,
        )
    )
    if not has_structured_preferences:
        return False
    if retrieval_strategy.group_by != "year":
        return False

    normalized_input = _normalize_presearch_text(
        getattr(intent_classification, "normalized_input", "") or user_input
    )
    approval_markers = (
        "approvat",
        "approvazione",
        "delibera",
        "verbale",
        "consiglio di amministrazione",
        "cda",
    )
    if any(marker in normalized_input for marker in approval_markers):
        return False

    return True


def build_retrieval_guidance_candidates(
    *,
    user_input: str,
    intent_classification: IntentClassification,
    retrieval_strategy: RetrievalStrategy,
    customer_code: str = "",
    presearch_limit: int = 5,
    related_approval_limit: int = 2,
) -> RetrievalGuidanceCandidates:
    presearch_candidates = build_presearch_candidates(
        user_input=user_input,
        intent_classification=intent_classification,
        retrieval_strategy=retrieval_strategy,
        customer_code=customer_code,
        limit=presearch_limit,
    )
    related_approval_candidates: list[PresearchCandidate] = []
    if presearch_candidates:
        related_approval_candidates = build_related_approval_candidates(
            user_input=user_input,
            primary_candidate=presearch_candidates[0],
            customer_code=customer_code,
            limit=related_approval_limit,
        )

    return RetrievalGuidanceCandidates(
        presearch_candidates=presearch_candidates,
        related_approval_candidates=related_approval_candidates,
    )


def _document_to_presearch_candidate(document: DocumentIndex) -> PresearchCandidate:
    return PresearchCandidate(
        key=document.object_key,
        filename=document.filename or "",
        document_family=document.document_family or "",
        topic_tags=document.topic_tags or "",
        document_date=(
            document.document_date.isoformat() if document.document_date else ""
        ),
        s3_last_modified=(
            document.s3_last_modified.isoformat()
            if document.s3_last_modified
            else (
                document.last_modified.isoformat()
                if document.last_modified
                else ""
            )
        ),
        text_preview=(document.text_preview or "")[:500],
        sibling_signature=_infer_sibling_signature(
            document.filename or "",
            document.object_key or "",
            document.document_date.isoformat() if document.document_date else "",
        ),
    )


def _infer_sibling_signature(filename: str, object_key: str, document_date: str) -> str:
    value = " ".join(item for item in [filename or "", object_key or ""] if item).lower()
    rso_dated_match = re.search(r"rso[_\-\s]?(\d{8})", value, flags=re.IGNORECASE)
    if rso_dated_match:
        return f"rso_{rso_dated_match.group(1)}"

    if document_date and "rso" in value:
        return f"rso_{document_date}"

    return ""


def build_presearch_candidates(
    *,
    user_input: str,
    intent_classification: IntentClassification,
    retrieval_strategy: RetrievalStrategy,
    customer_code: str = "",
    limit: int = 5,
) -> list[PresearchCandidate]:
    if not customer_code:
        return []
    if not should_run_presearch(
        user_input=user_input,
        intent_classification=intent_classification,
        retrieval_strategy=retrieval_strategy,
    ):
        return []

    documents = DocumentIndex.objects.select_related("client").filter(
        client__customer_code=customer_code,
        client__active=True,
        active=True,
    )

    if retrieval_strategy.preferred_document_families:
        family_filter = None
        for family in retrieval_strategy.preferred_document_families:
            family_terms = search_variants(family)
            clause = None
            for term in family_terms:
                from django.db.models import Q
                q_obj = Q(document_family__icontains=term)
                clause = q_obj if clause is None else clause | q_obj
            family_filter = clause if family_filter is None else family_filter | clause
        if family_filter is not None:
            documents = documents.filter(family_filter)

    if retrieval_strategy.preferred_topic_tags:
        topic_filter = None
        for tag in retrieval_strategy.preferred_topic_tags:
            tag_terms = search_variants(tag)
            clause = None
            for term in tag_terms:
                from django.db.models import Q
                q_obj = Q(topic_tags__icontains=term)
                clause = q_obj if clause is None else clause | q_obj
            topic_filter = clause if topic_filter is None else topic_filter | clause
        if topic_filter is not None:
            documents = documents.filter(topic_filter)

    if retrieval_strategy.preferred_control_functions:
        control_filter = None
        for control in retrieval_strategy.preferred_control_functions:
            control_terms = search_variants(control)
            clause = None
            for term in control_terms:
                from django.db.models import Q
                q_obj = Q(control_function_tags__icontains=term)
                clause = q_obj if clause is None else clause | q_obj
            control_filter = (
                clause if control_filter is None else control_filter | clause
            )
        if control_filter is not None:
            documents = documents.filter(control_filter)

    if retrieval_strategy.preferred_filename_contains:
        filename_filter = None
        for token in retrieval_strategy.preferred_filename_contains:
            token_terms = search_variants(token)
            clause = None
            for term in token_terms:
                from django.db.models import Q
                q_obj = Q(filename__icontains=term) | Q(object_key__icontains=term)
                clause = q_obj if clause is None else clause | q_obj
            filename_filter = (
                clause if filename_filter is None else filename_filter | clause
            )
        if filename_filter is not None:
            documents = documents.filter(filename_filter)

    query_terms = query_terms_for_search(user_input)
    hint_terms = build_query_hints(
        intent_classification=intent_classification,
        retrieval_strategy=retrieval_strategy,
    )
    combined_terms = []
    for term in [*query_terms, *hint_terms]:
        normalized = (term or "").strip()
        if normalized and normalized not in combined_terms:
            combined_terms.append(normalized)

    if combined_terms:
        from django.db.models import Q

        broad_filter = Q()
        for term in combined_terms[:6]:
            for variant in search_variants(term):
                broad_filter |= (
                    Q(filename__icontains=variant)
                    | Q(object_key__icontains=variant)
                    | Q(text_preview__icontains=variant)
                    | Q(topic_tags__icontains=variant)
                    | Q(document_family__icontains=variant)
                )
        documents = documents.filter(broad_filter)

    sort_field = retrieval_strategy.preferred_sort_by or "document_date"
    descending = retrieval_strategy.preferred_sort_order.lower() != "asc"

    if sort_field == "document_date":
        documents = documents.order_by(
            F("document_date").desc(nulls_last=True)
            if descending
            else F("document_date").asc(nulls_last=True),
            F("s3_last_modified").desc(nulls_last=True),
            "-indexed_at",
        )
    elif sort_field == "s3_last_modified":
        documents = documents.order_by(
            F("s3_last_modified").desc(nulls_last=True)
            if descending
            else F("s3_last_modified").asc(nulls_last=True),
            F("document_date").desc(nulls_last=True),
            "-indexed_at",
        )
    else:
        order_field = sort_field
        if descending:
            order_field = f"-{order_field}"
        documents = documents.order_by(order_field, "-indexed_at")

    documents = documents[: max(1, limit)]

    return [_document_to_presearch_candidate(document) for document in documents]


def build_related_approval_candidates(
    *,
    user_input: str,
    primary_candidate: PresearchCandidate | None,
    customer_code: str = "",
    limit: int = 2,
) -> list[PresearchCandidate]:
    if not customer_code or primary_candidate is None:
        return []

    if "approv" not in (user_input or "").lower():
        return []

    documents = DocumentIndex.objects.select_related("client").filter(
        client__customer_code=customer_code,
        client__active=True,
        active=True,
        topic_tags__icontains="struttura_organizzativa",
    ).exclude(object_key=primary_candidate.key)

    from django.db.models import Q

    relation_filter = (
        Q(document_family__in=["verbale_cda", "estratto_cda"])
        | Q(filename__icontains="verbale")
        | Q(filename__icontains="aggiornamento")
        | Q(filename__icontains="rso")
        | Q(object_key__icontains="verbale")
        | Q(object_key__icontains="aggiornamento")
    )
    documents = documents.filter(relation_filter)

    query_terms = [
        "approvazione",
        "approvata",
        "consiglio di amministrazione",
        "verbale",
        "aggiornamento rso",
        "relazione sulla struttura organizzativa",
    ]
    primary_year = ""
    if primary_candidate.document_date:
        primary_year = primary_candidate.document_date[:4]
    if primary_year.isdigit():
        previous_year = str(int(primary_year) - 1)
        query_terms.extend([primary_year, previous_year])

    broad_filter = Q()
    for term in query_terms:
        for variant in search_variants(term):
            broad_filter |= (
                Q(filename__icontains=variant)
                | Q(object_key__icontains=variant)
                | Q(text_preview__icontains=variant)
                | Q(topic_tags__icontains=variant)
                | Q(document_family__icontains=variant)
            )
    documents = documents.filter(broad_filter).order_by(
        F("document_date").desc(nulls_last=True),
        F("s3_last_modified").desc(nulls_last=True),
        "-indexed_at",
    )[: max(1, limit)]

    return [_document_to_presearch_candidate(document) for document in documents]
