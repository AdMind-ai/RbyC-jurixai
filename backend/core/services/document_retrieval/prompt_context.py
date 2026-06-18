from core.services.document_retrieval.intent_classifier import (
    INTENT_CROSS_DOCUMENT_COVERAGE,
    IntentClassification,
)
from core.services.document_retrieval.evidence_builder import (
    build_evidence_plan,
)
from core.services.document_retrieval.query_hints import build_query_hints
from core.services.document_retrieval.retrieval_strategies import (
    RetrievalStrategy,
)


def _should_relax_structured_preferences(
    intent_classification: IntentClassification,
) -> bool:
    if intent_classification.intent_type == INTENT_CROSS_DOCUMENT_COVERAGE:
        return False
    normalized_input = getattr(intent_classification, "normalized_input", "") or ""
    approval_markers = ("approvat", "approvazione", "delibera", "verbale", "consiglio di amministrazione", "cda")
    return any(marker in normalized_input for marker in approval_markers)


def _should_use_compact_prompt_context(
    intent_classification: IntentClassification,
) -> bool:
    if intent_classification.intent_type == INTENT_CROSS_DOCUMENT_COVERAGE:
        return False
    return _should_relax_structured_preferences(intent_classification)


def build_document_search_input(
    user_input: str,
    intent_classification: IntentClassification,
    retrieval_strategy: RetrievalStrategy,
    presearch_candidates: list | None = None,
    related_approval_candidates: list | None = None,
) -> str:
    cleaned_input = (user_input or "").strip()

    if not cleaned_input:
        return ""

    if intent_classification.intent_type == "generic_document_search":
        return cleaned_input

    query_hints = build_query_hints(
        intent_classification=intent_classification,
        retrieval_strategy=retrieval_strategy,
    )
    evidence_plan = build_evidence_plan(
        intent_classification=intent_classification,
        retrieval_strategy=retrieval_strategy,
    )
    relax_structured_preferences = _should_relax_structured_preferences(
        intent_classification
    )
    use_compact_prompt_context = _should_use_compact_prompt_context(
        intent_classification
    )

    context_lines = [
        "Contesto operativo interno per la ricerca documentale.",
        f"intent_type={intent_classification.intent_type}",
        f"intent_confidence={intent_classification.confidence}",
        f"primary_tool={retrieval_strategy.primary_tool}",
        (
            "prefer_preview_only="
            f"{str(retrieval_strategy.prefer_preview_only).lower()}"
        ),
        f"max_documents_to_open={retrieval_strategy.max_documents_to_open}",
    ]

    if retrieval_strategy.group_by and not use_compact_prompt_context:
        context_lines.append(f"group_by={retrieval_strategy.group_by}")

    if retrieval_strategy.evidence_grouping and not use_compact_prompt_context:
        context_lines.append(
            f"evidence_grouping={retrieval_strategy.evidence_grouping}"
        )

    if query_hints:
        if use_compact_prompt_context:
            query_hints = query_hints[:3]
        context_lines.append(
            "suggested_query_terms=" + ",".join(query_hints)
        )

    if retrieval_strategy.preferred_document_families and not relax_structured_preferences:
        context_lines.append(
            "preferred_document_families="
            + ",".join(retrieval_strategy.preferred_document_families)
        )

    if retrieval_strategy.preferred_topic_tags and not relax_structured_preferences:
        context_lines.append(
            "preferred_topic_tags="
            + ",".join(retrieval_strategy.preferred_topic_tags)
        )

    if retrieval_strategy.preferred_control_functions and not relax_structured_preferences:
        context_lines.append(
            "preferred_control_functions="
            + ",".join(retrieval_strategy.preferred_control_functions)
        )

    if retrieval_strategy.preferred_sort_by:
        context_lines.append(
            f"preferred_sort_by={retrieval_strategy.preferred_sort_by}"
        )

    if retrieval_strategy.preferred_sort_order:
        context_lines.append(
            f"preferred_sort_order={retrieval_strategy.preferred_sort_order}"
        )

    if retrieval_strategy.notes and not use_compact_prompt_context:
        context_lines.append(f"retrieval_notes={retrieval_strategy.notes}")

    if retrieval_strategy.stopping_rule and not use_compact_prompt_context:
        context_lines.append(
            f"stopping_rule={retrieval_strategy.stopping_rule}"
        )

    if intent_classification.matched_signals and not use_compact_prompt_context:
        context_lines.append(
            "matched_signals=" + ",".join(intent_classification.matched_signals)
        )

    if evidence_plan and not use_compact_prompt_context:
        context_lines.append(f"evidence_plan={evidence_plan}")

    if presearch_candidates:
        context_lines.append("presearch_available=true")
        context_lines.append(
            f"presearch_candidate_count={len(presearch_candidates)}"
        )

    context_block = "\n".join(context_lines)
    guidance_text = (
        "Usa questo contesto come orientamento leggero per la ricerca. "
        "Non riportare questi metadati nella risposta finale. "
        "Parti normalmente da search_documents prima di scegliere un documento da aprire. "
        "Usa eventuali filtri strutturati come preferenze iniziali, non come vincoli rigidi. "
        "Usa get_document(mode='full') solo dopo avere identificato pochi candidati forti. "
    )
    if use_compact_prompt_context:
        guidance_text += (
            "Se la domanda riguarda approvazioni, delibere, verbali o organi societari, "
            "evita catene di ricerche esplorative: fai prima una ricerca mirata sul documento base o sul verbale piu probabile, "
            "poi apri solo i 1-2 candidati migliori e sintetizza. "
            "Distingui con chiarezza tra documento piu recente, approvazione esplicita ed evidenza societaria correlata."
        )
    else:
        guidance_text += (
            "Se la domanda riguarda approvazioni, delibere, verbali o organi societari, "
            "non limitarti automaticamente al documento base piu recente: verifica anche verbali, "
            "convocazioni o altri documenti deliberativi correlati quando necessario. "
            "Per domande su ultima versione o documento piu recente, usa document_date come criterio principale di recenza "
            "e distingui con chiarezza tra documento piu recente, approvazione esplicita e evidenza societaria correlata. "
            "Quando e presente un evidence_plan, seguilo per comprimere l'evidenza prima della sintesi finale."
        )
    if intent_classification.intent_type == INTENT_CROSS_DOCUMENT_COVERAGE:
        guidance_text += (
            " Per domande di copertura trasversale, come quando, quante volte, "
            "in quali documenti o dove si parla di un tema, non ridurre la "
            "risposta ai soli 3-5 risultati piu rilevanti: usa i risultati "
            "come candidate set, deduplica documenti o sedute equivalenti e "
            "distingui occorrenze testuali da trattazioni esplicite."
        )
    return (
        f"{context_block}\n\n"
        f"{guidance_text}\n\n"
        f"Domanda utente:\n{cleaned_input}"
    )
