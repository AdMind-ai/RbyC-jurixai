from core.services.document_retrieval.intent_classifier import (
    IntentClassification,
)
from core.services.document_retrieval.evidence_builder import (
    build_evidence_plan,
)
from core.services.document_retrieval.query_hints import build_query_hints
from core.services.document_retrieval.retrieval_strategies import (
    RetrievalStrategy,
)


def build_document_search_input(
    user_input: str,
    intent_classification: IntentClassification,
    retrieval_strategy: RetrievalStrategy,
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

    if retrieval_strategy.group_by:
        context_lines.append(f"group_by={retrieval_strategy.group_by}")

    if retrieval_strategy.evidence_grouping:
        context_lines.append(
            f"evidence_grouping={retrieval_strategy.evidence_grouping}"
        )

    if query_hints:
        context_lines.append(
            "suggested_query_terms=" + ",".join(query_hints)
        )

    if retrieval_strategy.preferred_document_families:
        context_lines.append(
            "preferred_document_families="
            + ",".join(retrieval_strategy.preferred_document_families)
        )

    if retrieval_strategy.preferred_topic_tags:
        context_lines.append(
            "preferred_topic_tags="
            + ",".join(retrieval_strategy.preferred_topic_tags)
        )

    if retrieval_strategy.preferred_control_functions:
        context_lines.append(
            "preferred_control_functions="
            + ",".join(retrieval_strategy.preferred_control_functions)
        )

    if retrieval_strategy.notes:
        context_lines.append(f"retrieval_notes={retrieval_strategy.notes}")

    if retrieval_strategy.stopping_rule:
        context_lines.append(
            f"stopping_rule={retrieval_strategy.stopping_rule}"
        )

    if intent_classification.matched_signals:
        context_lines.append(
            "matched_signals=" + ",".join(intent_classification.matched_signals)
        )

    if evidence_plan:
        context_lines.append(f"evidence_plan={evidence_plan}")

    context_block = "\n".join(context_lines)
    return (
        f"{context_block}\n\n"
        "Usa questo contesto solo per orientare la strategia di ricerca e la "
        "selezione dei documenti. Non riportare questi metadati nella risposta "
        "finale all'utente. Se la domanda ricade in un intent noto, privilegia "
        "i termini suggeriti e i tipi di documenti preferiti nelle prime "
        "chiamate di ricerca, evitando esplorazioni inutilmente ampie. "
        "Quando gli strumenti lo consentono, usa i metadati preferiti come "
        "filtri espliciti di ricerca, soprattutto per document_family, "
        "control_function_tags e topic_tags. "
        "Se hai gia identificato il corretto perimetro documentale tramite "
        "filtri strutturati o documenti primari chiaramente pertinenti, non "
        "riaprire la fase di scoperta con nuove ricerche generiche senza un "
        "vuoto informativo concreto. "
        "Quando e presente un evidence_plan, seguilo per comprimere "
        "l'evidenza prima della sintesi finale.\n\n"
        f"Domanda utente:\n{cleaned_input}"
    )
