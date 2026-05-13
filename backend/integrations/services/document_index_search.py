import unicodedata


SEARCH_SYNONYMS = {
    "ad": ["amministratore delegato"],
    "amministratore delegato": ["ad"],
    "dg": ["direttore generale"],
    "direttore generale": ["dg"],
    "cda": ["consiglio di amministrazione"],
    "consiglio di amministrazione": ["cda"],
    "rso": [
        "relazione sulla struttura organizzativa",
        "struttura organizzativa",
    ],
    "relazione sulla struttura organizzativa": ["rso", "struttura organizzativa"],
    "struttura organizzativa": ["rso", "relazione sulla struttura organizzativa"],
    "nomina": ["nominato", "nominata", "nomine", "nominare"],
    "deleghe": ["delega", "delegato", "delegati", "attribuzione di poteri"],
    "delega": ["deleghe", "delegato", "attribuzione di poteri"],
    "poteri": ["potere", "attribuiti", "attribuzioni"],
    "potere": ["poteri", "attribuiti", "attribuzioni"],
    "bilancio": ["bilanci", "dati di bilancio", "relazione finanziaria"],
}


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
