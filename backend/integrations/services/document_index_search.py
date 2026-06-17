import re
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

SEARCH_STOPWORDS = {
    "a",
    "ai",
    "al",
    "alla",
    "alle",
    "allo",
    "anche",
    "che",
    "chi",
    "come",
    "con",
    "cosa",
    "da",
    "dal",
    "dalla",
    "de",
    "dei",
    "del",
    "della",
    "delle",
    "di",
    "dove",
    "e",
    "ed",
    "gli",
    "ha",
    "hanno",
    "i",
    "il",
    "in",
    "la",
    "le",
    "lo",
    "manca",
    "nei",
    "nel",
    "nella",
    "nelle",
    "non",
    "parla",
    "parlato",
    "parlati",
    "parlata",
    "parlate",
    "per",
    "quale",
    "quali",
    "quando",
    "quante",
    "quanti",
    "risulta",
    "si",
    "sono",
    "stata",
    "stato",
    "sul",
    "sulla",
    "tra",
    "un",
    "una",
    "volta",
    "volte",
}

SEARCH_SCOPE_TERMS = {
    "cda",
    "consiglio",
    "amministrazione",
    "verbale",
    "verbali",
}

SEARCH_MODIFIER_TERMS = {
    "ultima",
    "ultimo",
    "ultime",
    "ultimi",
    "recente",
    "recenti",
}


def normalize_search_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(normalized.casefold().split())


def _tokenize_search_query(value: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", normalize_search_value(value))
        if token
    ]


def _add_query_term(terms: list[str], value: str) -> None:
    normalized = normalize_search_value(value)
    if normalized and normalized not in terms:
        terms.append(normalized)


def _is_meaningful_query_token(token: str) -> bool:
    if not token:
        return False
    if token in SEARCH_STOPWORDS:
        return False
    if token in SEARCH_SCOPE_TERMS:
        return True
    if token.isdigit():
        return len(token) == 4
    return len(token) >= 3


def is_scope_query_term(term: str) -> bool:
    normalized = normalize_search_value(term)
    if normalized in SEARCH_SCOPE_TERMS:
        return True
    return normalized in {
        "consiglio di amministrazione",
    }


def _looks_like_named_entity_pair(left: str, right: str) -> bool:
    return bool(
        left
        and right
        and (
            left.isupper()
            or right.isupper()
            or (left[:1].isupper() and right[:1].isupper())
        )
    )


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

    terms = []
    normalized_tokens = _tokenize_search_query(cleaned)
    raw_tokens = re.findall(r"[A-Za-zÀ-ÿ0-9']+", cleaned)
    meaningful_tokens = [
        token for token in normalized_tokens if _is_meaningful_query_token(token)
    ]

    quoted_phrases = [
        match.group(1).strip()
        for match in re.finditer(r'"([^"]+)"', cleaned)
        if match.group(1).strip()
    ]
    for phrase in quoted_phrases:
        _add_query_term(terms, phrase)

    for index in range(min(len(normalized_tokens), len(raw_tokens)) - 1):
        left = normalized_tokens[index]
        right = normalized_tokens[index + 1]
        if not (
            _is_meaningful_query_token(left)
            and _is_meaningful_query_token(right)
        ):
            continue
        if (
            left in SEARCH_SCOPE_TERMS
            or right in SEARCH_SCOPE_TERMS
            or left in SEARCH_MODIFIER_TERMS
            or right in SEARCH_MODIFIER_TERMS
        ):
            continue

        bigram = f"{left} {right}"
        if bigram in SEARCH_SYNONYMS or _looks_like_named_entity_pair(
            raw_tokens[index],
            raw_tokens[index + 1],
        ):
            _add_query_term(terms, bigram)

    for token in meaningful_tokens:
        _add_query_term(terms, token)

    for known_phrase in SEARCH_SYNONYMS:
        if " " in known_phrase and known_phrase in normalize_search_value(cleaned):
            _add_query_term(terms, known_phrase)

    if not terms:
        _add_query_term(terms, cleaned)

    return terms[:10]
