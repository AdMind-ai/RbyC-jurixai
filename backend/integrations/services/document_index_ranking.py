from integrations.services.document_index_search import (
    normalize_search_value,
    search_variants,
)


FIELD_SCORE_WEIGHTS = {
    "filename": 12,
    "object_key": 11,
    "document_family": 9,
    "document_type": 8,
    "topic_tags": 8,
    "control_function_tags": 7,
    "year": 6,
    "search_text": 5,
    "text_preview": 4,
    "extracted_text": 5,
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

DOCUMENT_ARTIFACT_PATTERNS = {
    "verbale": (
        "verbale",
        "verbale_cda",
        "estratto_cda",
        "consiglio di amministrazione",
        "cda",
    ),
    "convocazione": (
        "convocazione",
        "ordine del giorno",
        "odg",
    ),
    "delibera": (
        "delibera",
        "deliber",
        "approvazione",
        "approvat",
    ),
    "relazione": (
        "relazione",
        "rso",
        "report",
    ),
    "policy": (
        "policy",
        "procedura",
        "regolamento",
    ),
}


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
        "needs_latest_document": any(
            any(marker in normalized_term for normalized_term in normalized_terms)
            for marker in ("ultima", "ultimo", "ultim", "piu recente", "recent")
        ),
        "needs_approval_evidence": any(
            any(marker in normalized_term for normalized_term in normalized_terms)
            for marker in ("approvat", "approvazione", "deliberat", "delibera")
        ),
        "needs_verbale": any(
            any(marker in normalized_term for normalized_term in normalized_terms)
            for marker in ("verbale", "estratto", "consiglio di amministrazione", "cda")
        ),
        "needs_convocazione": any(
            any(marker in normalized_term for normalized_term in normalized_terms)
            for marker in ("convocazione", "ordine del giorno", "odg")
        ),
        "needs_relazione": any(
            any(marker in normalized_term for normalized_term in normalized_terms)
            for marker in ("relazione", "rso")
        ),
        "needs_policy": any(
            any(marker in normalized_term for normalized_term in normalized_terms)
            for marker in ("policy", "procedura", "regolamento")
        ),
    }


def build_document_ranking_debug(
    document,
    query_terms: list[str],
) -> dict[str, str | int]:
    query_profile = build_query_profile(query_terms)
    return {
        "filename": document.filename or "",
        "key": document.object_key or "",
        "relevance_score": score_document_match(document, query_terms, query_profile),
        "document_date": document.document_date.isoformat() if document.document_date else "",
        "s3_last_modified": (
            document.s3_last_modified.isoformat()
            if document.s3_last_modified
            else (
                document.last_modified.isoformat()
                if document.last_modified
                else ""
            )
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


def document_field_value(document, field_name: str) -> str:
    return document.__dict__.get(field_name) or ""


def document_fts_rank_value(document) -> float:
    try:
        return float(getattr(document, "fts_rank", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def score_fts_alignment(document) -> int:
    fts_rank = document_fts_rank_value(document)
    if fts_rank <= 0:
        return 0
    return min(int(round(fts_rank * 25)), 25)


def score_document_artifact_alignment(
    normalized_fields: dict[str, str],
    profile: dict[str, bool],
) -> int:
    filename = normalized_fields.get("filename", "")
    object_key = normalized_fields.get("object_key", "")
    document_family = normalized_fields.get("document_family", "")
    document_type = normalized_fields.get("document_type", "")
    combined_text = " ".join(
        value
        for value in (
            filename,
            object_key,
            document_family,
            document_type,
            normalized_fields.get("topic_tags", ""),
        )
        if value
    )

    score = 0
    if profile.get("needs_verbale"):
        if any(token in combined_text for token in DOCUMENT_ARTIFACT_PATTERNS["verbale"]):
            score += 26
        elif any(token in combined_text for token in DOCUMENT_ARTIFACT_PATTERNS["relazione"]):
            score -= 12
        elif any(token in combined_text for token in DOCUMENT_ARTIFACT_PATTERNS["policy"]):
            score -= 16

    if profile.get("needs_convocazione"):
        if any(token in combined_text for token in DOCUMENT_ARTIFACT_PATTERNS["convocazione"]):
            score += 24
        elif any(token in combined_text for token in DOCUMENT_ARTIFACT_PATTERNS["relazione"]):
            score -= 10

    if profile.get("needs_policy"):
        if any(token in combined_text for token in DOCUMENT_ARTIFACT_PATTERNS["policy"]):
            score += 20
        elif any(token in combined_text for token in DOCUMENT_ARTIFACT_PATTERNS["verbale"]):
            score -= 10

    if profile.get("needs_relazione"):
        if any(token in combined_text for token in DOCUMENT_ARTIFACT_PATTERNS["relazione"]):
            score += 10

    if profile.get("needs_approval_evidence"):
        if any(token in combined_text for token in DOCUMENT_ARTIFACT_PATTERNS["verbale"]):
            score += 12
        if any(token in combined_text for token in DOCUMENT_ARTIFACT_PATTERNS["convocazione"]):
            score += 8

    return score


def score_document_match(
    document,
    query_terms: list[str],
    query_profile: dict[str, bool] | None = None,
) -> int:
    if not query_terms:
        return 0

    normalized_fields = {
        "filename": normalize_search_value(document_field_value(document, "filename")),
        "object_key": normalize_search_value(document_field_value(document, "object_key")),
        "document_type": normalize_search_value(document_field_value(document, "document_type")),
        "document_family": normalize_search_value(document_field_value(document, "document_family")),
        "topic_tags": normalize_search_value(document_field_value(document, "topic_tags")),
        "control_function_tags": normalize_search_value(document_field_value(document, "control_function_tags")),
        "year": normalize_search_value(document_field_value(document, "year")),
        "search_text": normalize_search_value(document_field_value(document, "search_text")),
        "text_preview": normalize_search_value(document_field_value(document, "text_preview")),
        "extracted_text": normalize_search_value(document_field_value(document, "extracted_text")),
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
    score += score_fts_alignment(document)
    score += score_document_artifact_alignment(normalized_fields, effective_profile)
    score += score_governance_alignment(normalized_fields, effective_profile)
    score += score_financial_alignment(normalized_fields, effective_profile)
    return score


def sort_documents_by_relevance(
    documents: list,
    query_terms: list[str],
) -> list:
    if not query_terms:
        return documents

    query_profile = build_query_profile(query_terms)
    recency_sensitive = query_profile.get("needs_latest_document", False)

    def recency_value(document) -> str:
        return document.document_date.isoformat() if document.document_date else ""

    def relevance_value(document) -> int:
        return score_document_match(document, query_terms, query_profile)

    def last_modified_value(document) -> str:
        if document.s3_last_modified:
            return document.s3_last_modified.isoformat()
        if document.last_modified:
            return document.last_modified.isoformat()
        return ""

    return sorted(
        documents,
        key=lambda document: (
            recency_value(document) if recency_sensitive else relevance_value(document),
            relevance_value(document) if recency_sensitive else recency_value(document),
            last_modified_value(document),
            document.indexed_at.isoformat() if document.indexed_at else "",
        ),
        reverse=True,
    )
