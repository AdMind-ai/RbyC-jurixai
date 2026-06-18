import unicodedata

from integrations.models import DocumentIndex
from integrations.services.document_index_search import (
    is_scope_query_term,
    normalize_search_value,
    search_variants,
)


def _fold_text_with_positions(value: str) -> tuple[str, list[int]]:
    folded_chars = []
    positions = []
    for index, char in enumerate(value or ""):
        normalized = unicodedata.normalize("NFKD", char)
        for folded_char in normalized:
            if unicodedata.combining(folded_char):
                continue
            folded_chars.append(folded_char.casefold())
            positions.append(index)
    return "".join(folded_chars), positions


def _find_best_match(text: str, query_terms: list[str]) -> tuple[int, int] | None:
    folded_text, positions = _fold_text_with_positions(text)
    if not folded_text or not positions:
        return None

    candidate_terms = [
        term for term in query_terms if term and not is_scope_query_term(term)
    ] or [term for term in query_terms if term]
    variants = []
    for term in candidate_terms:
        for variant in search_variants(term):
            normalized_variant = normalize_search_value(variant)
            if normalized_variant and normalized_variant not in variants:
                variants.append(normalized_variant)
    variants.sort(key=len, reverse=True)

    for variant in variants:
        folded_variant = _fold_text_with_positions(variant)[0]
        if not folded_variant:
            continue
        match_index = folded_text.find(folded_variant)
        if match_index < 0:
            continue
        start = positions[match_index]
        end_position_index = min(match_index + len(folded_variant) - 1, len(positions) - 1)
        end = positions[end_position_index] + 1
        return start, end
    return None


def _excerpt_around_match(
    text: str,
    match: tuple[int, int],
    *,
    max_chars: int,
) -> str:
    start, end = match
    context_chars = max(80, (max_chars - (end - start)) // 2)
    excerpt_start = max(0, start - context_chars)
    excerpt_end = min(len(text), end + context_chars)

    while excerpt_start > 0 and text[excerpt_start - 1].isalnum():
        excerpt_start -= 1
    while excerpt_end < len(text) and text[excerpt_end:excerpt_end + 1].isalnum():
        excerpt_end += 1

    excerpt = " ".join(text[excerpt_start:excerpt_end].split())
    if excerpt_start > 0:
        excerpt = f"...{excerpt}"
    if excerpt_end < len(text):
        excerpt = f"{excerpt}..."
    return excerpt[:max_chars].strip()


def build_document_matched_excerpt(
    document: DocumentIndex,
    query_terms: list[str],
    *,
    max_chars: int = 900,
) -> str:
    if not query_terms:
        return ""

    sources = [
        getattr(document, "extracted_text", "") or "",
        document.text_preview or "",
        getattr(document, "search_text", "") or "",
    ]
    for source_text in sources:
        match = _find_best_match(source_text, query_terms)
        if match:
            return _excerpt_around_match(
                source_text,
                match,
                max_chars=max_chars,
            )
    return ""
