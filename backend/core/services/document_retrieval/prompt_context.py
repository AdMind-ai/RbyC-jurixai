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

    if retrieval_strategy.preferred_filename_contains:
        context_lines.append(
            "preferred_filename_contains="
            + ",".join(retrieval_strategy.preferred_filename_contains)
        )

    if retrieval_strategy.preferred_sort_by:
        context_lines.append(
            f"preferred_sort_by={retrieval_strategy.preferred_sort_by}"
        )

    if retrieval_strategy.preferred_sort_order:
        context_lines.append(
            f"preferred_sort_order={retrieval_strategy.preferred_sort_order}"
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

    if presearch_candidates:
        primary_candidate = presearch_candidates[0]
        sibling_candidates = []
        primary_signature = getattr(primary_candidate, "sibling_signature", "") or ""
        if primary_signature:
            sibling_candidates = [
                candidate
                for candidate in presearch_candidates
                if (getattr(candidate, "sibling_signature", "") or "") == primary_signature
            ]
        context_lines.append(
            "presearch_candidate_set_status=available"
        )
        context_lines.append(
            "presearch_candidate_set_usage=prioritize_reading_before_open_search"
        )
        context_lines.append(
            "presearch_primary_selection_rule=most_recent_document_date"
        )
        context_lines.append(
            "presearch_primary_candidate="
            f"filename:{getattr(primary_candidate, 'filename', '')};"
            f"key:{getattr(primary_candidate, 'key', '')};"
            f"document_family:{getattr(primary_candidate, 'document_family', '')};"
            f"topic_tags:{getattr(primary_candidate, 'topic_tags', '')};"
            f"document_date:{getattr(primary_candidate, 'document_date', '')};"
            f"s3_last_modified:{getattr(primary_candidate, 's3_last_modified', '')};"
            f"preview:{getattr(primary_candidate, 'text_preview', '')}"
        )
        context_lines.append(
            "presearch_primary_excerpt="
            + (getattr(primary_candidate, "text_preview", "") or "")
        )
        if sibling_candidates:
            context_lines.append(
                f"presearch_primary_sibling_signature={primary_signature}"
            )
            context_lines.append(
                f"presearch_primary_sibling_count={len(sibling_candidates)}"
            )
            for index, sibling_candidate in enumerate(sibling_candidates[:3], start=1):
                context_lines.append(
                    "presearch_primary_sibling_"
                    f"{index}="
                    f"filename:{getattr(sibling_candidate, 'filename', '')};"
                    f"key:{getattr(sibling_candidate, 'key', '')};"
                    f"document_date:{getattr(sibling_candidate, 'document_date', '')};"
                    f"preview:{getattr(sibling_candidate, 'text_preview', '')}"
                )
        if len(presearch_candidates) > 1:
            secondary_candidate = presearch_candidates[1]
            context_lines.append(
                "presearch_secondary_candidate="
                f"filename:{getattr(secondary_candidate, 'filename', '')};"
                f"key:{getattr(secondary_candidate, 'key', '')};"
                f"document_family:{getattr(secondary_candidate, 'document_family', '')};"
                f"topic_tags:{getattr(secondary_candidate, 'topic_tags', '')};"
                f"document_date:{getattr(secondary_candidate, 'document_date', '')};"
                f"s3_last_modified:{getattr(secondary_candidate, 's3_last_modified', '')};"
                f"preview:{getattr(secondary_candidate, 'text_preview', '')}"
            )

    if related_approval_candidates:
        context_lines.append(
            "latest_explicit_approval_candidate_set_status=available"
        )
        for index, candidate in enumerate(related_approval_candidates[:2], start=1):
            context_lines.append(
                "latest_explicit_approval_candidate_"
                f"{index}="
                f"filename:{getattr(candidate, 'filename', '')};"
                f"key:{getattr(candidate, 'key', '')};"
                f"document_family:{getattr(candidate, 'document_family', '')};"
                f"topic_tags:{getattr(candidate, 'topic_tags', '')};"
                f"document_date:{getattr(candidate, 'document_date', '')};"
                f"preview:{getattr(candidate, 'text_preview', '')}"
            )

    context_block = "\n".join(context_lines)
    return (
        f"{context_block}\n\n"
        "Usa questo contesto per orientare ricerca e selezione dei documenti. "
        "Non riportare questi metadati nella risposta finale. "
        "Se il contesto fornisce filtri strutturati, usali nelle prime "
        "chiamate di ricerca per evitare esplorazioni ampie. "
        "Se sono presenti presearch_candidate, considera il "
        "presearch_primary_candidate come punto di partenza prioritario. "
        "Se e presente presearch_primary_excerpt, valutalo prima di riaprire "
        "la discovery. "
        "Per domande su ultima versione, ultimo aggiornamento o documento piu "
        "recente, usa document_date come criterio principale di recenza e "
        "s3_last_modified solo come fallback tecnico. "
        "Non sostituire il documento piu recente con documenti piu vecchi solo "
        "perche hanno una preview o una corrispondenza testuale piu facile. "
        "Se il presearch_primary_candidate non basta a chiarire un punto "
        "specifico ma esistono presearch_primary_sibling dello stesso gruppo "
        "versionale, controlla prima questi documenti fratelli prima di "
        "allargare la ricerca a documenti di altre annualita o ad altri "
        "pacchetti documentali. "
        "Apri il presearch_secondary_candidate solo se il primary candidate non "
        "basta davvero o se serve un confronto mirato. "
        "Se il documento piu recente non contiene evidenza sufficiente sulla "
        "data di approvazione, rispondi con cautela distinguendo tra versione "
        "piu recente identificata e data di approvazione non chiaramente "
        "emersa. "
        "Se la domanda chiede esplicitamente una data di approvazione e il "
        "presearch_primary_candidate e gia stato identificato ma il preview o "
        "l'excerpt non bastano, approfondisci prima quel medesimo documento con "
        "get_document(mode='full') prima di concludere che la data non emerge. "
        "Non saltare subito a documenti piu vecchi o a ricerche generiche se il "
        "documento corretto e gia stato individuato ma non ancora letto con "
        "profondita sufficiente. "
        "Se, dopo avere letto con sufficiente profondita il documento piu "
        "recente, non emerge una data di approvazione esplicita per quella "
        "stessa versione, prova allora a identificare l'ultima approvazione "
        "esplicita rintracciabile nei materiali strettamente correlati "
        "(verbali, aggiornamenti o documenti fratelli pertinenti) e distinguila "
        "con chiarezza dalla versione documentale piu recente. "
        "Se sono presenti latest_explicit_approval_candidate, usali come prima "
        "traccia per questa seconda verifica, prima di riaprire ricerche ampie. "
        "In questi casi, struttura la risposta separando: documento piu "
        "recente identificato; eventuale ultima approvazione esplicita trovata; "
        "e, se l'evidenza non prova una vera approvazione del documento, ultima "
        "evidenza deliberativa o societaria correlata disponibile. "
        "Dichiara in modo chiaro se questa evidenza si riferisce a una versione "
        "precedente, a modifiche collegate o a delibere organizzative connesse, "
        "e non presentarla come approvazione formale del documento piu recente "
        "se i materiali non lo dimostrano esplicitamente. "
        "Quando e presente un evidence_plan, seguilo per comprimere "
        "l'evidenza prima della sintesi finale.\n\n"
        f"Domanda utente:\n{cleaned_input}"
    )
