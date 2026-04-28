from core.services.document_retrieval.intent_classifier import IntentClassification
from core.services.document_retrieval.retrieval_strategies import RetrievalStrategy


def build_query_hints(
    intent_classification: IntentClassification,
    retrieval_strategy: RetrievalStrategy,
) -> tuple[str, ...]:
    hints = []

    for value in intent_classification.matched_signals:
        cleaned = (value or "").strip()
        if cleaned and cleaned not in hints:
            hints.append(cleaned)

    for value in retrieval_strategy.query_anchor_terms:
        cleaned = (value or "").strip()
        if cleaned and cleaned not in hints:
            hints.append(cleaned)

    return tuple(hints[:6])

