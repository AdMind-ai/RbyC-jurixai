from dataclasses import dataclass
import unicodedata


INTENT_APPOINTMENT_AND_POWERS = "appointment_and_powers"
INTENT_DIRECTOR_GENERAL_APPOINTMENT_CHECK = "director_general_appointment_check"
INTENT_FINANCIAL_SUMMARY_LAST_THREE_YEARS = "financial_summary_last_three_years"
INTENT_CONTROL_FUNCTIONS_FINDINGS_AND_REMEDIES = (
    "control_functions_findings_and_remedies"
)
INTENT_INVESTMENT_POLICIES_SUMMARY_BY_BOARD = (
    "investment_policies_summary_by_board"
)
INTENT_RISK_MANAGEMENT_BOARD_INVOLVEMENT = "risk_management_board_involvement"
INTENT_ORGANIZATIONAL_STRUCTURE_YEAR_COMPARISON = (
    "organizational_structure_year_comparison"
)
INTENT_CONSOB_TOPIC_MEETING_TRACKING = "consob_topic_meeting_tracking"
INTENT_GENERIC_DOCUMENT_SEARCH = "generic_document_search"


@dataclass(frozen=True)
class IntentRule:
    intent_type: str
    required_signals: tuple[str, ...] = ()
    optional_signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class IntentClassification:
    intent_type: str
    confidence: str
    matched_signals: tuple[str, ...]
    normalized_input: str


INTENT_RULES = (
    IntentRule(
        intent_type=INTENT_APPOINTMENT_AND_POWERS,
        required_signals=("amministratore delegato",),
        optional_signals=("nomin", "nomina", "poteri", "deleg", "attribuit"),
    ),
    IntentRule(
        intent_type=INTENT_DIRECTOR_GENERAL_APPOINTMENT_CHECK,
        required_signals=("direttore generale",),
        optional_signals=("nomin", "nomina"),
    ),
    IntentRule(
        intent_type=INTENT_FINANCIAL_SUMMARY_LAST_THREE_YEARS,
        optional_signals=(
            "bilancio",
            "dati di bilancio",
            "ultimi tre esercizi",
            "tre esercizi",
            "sintesi",
        ),
    ),
    IntentRule(
        intent_type=INTENT_CONTROL_FUNCTIONS_FINDINGS_AND_REMEDIES,
        optional_signals=(
            "risk",
            "compliance",
            "internal audit",
            "rilievi",
            "rimedi",
            "piani di rimedi",
            "action plan",
        ),
    ),
    IntentRule(
        intent_type=INTENT_INVESTMENT_POLICIES_SUMMARY_BY_BOARD,
        optional_signals=(
            "politiche di investimento",
            "politica di investimento",
            "consiglio di amministrazione",
            "portafogli in delega",
            "deliberate",
        ),
    ),
    IntentRule(
        intent_type=INTENT_RISK_MANAGEMENT_BOARD_INVOLVEMENT,
        optional_signals=(
            "risk management",
            "riunioni",
            "consiglio di amministrazione",
            "politica di investimento",
            "quante volte",
            "coinvolt",
        ),
    ),
    IntentRule(
        intent_type=INTENT_ORGANIZATIONAL_STRUCTURE_YEAR_COMPARISON,
        optional_signals=(
            "rso",
            "struttura organizzativa",
            "relazione sulla struttura organizzativa",
            "rispetto al",
            "modificat",
            "2025",
            "2024",
            "ultima",
            "approvat",
        ),
    ),
    IntentRule(
        intent_type=INTENT_CONSOB_TOPIC_MEETING_TRACKING,
        optional_signals=(
            "consob",
            "riunioni",
            "consiglio di amministrazione",
            "in quali riunioni",
            "contestazioni",
        ),
    ),
)


def normalize_intent_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(normalized.casefold().split())


def classify_document_search_intent(user_input: str) -> IntentClassification:
    normalized_input = normalize_intent_text(user_input)

    best_rule = None
    best_score = 0
    best_signals = ()

    for rule in INTENT_RULES:
        if rule.required_signals and not all(
            signal in normalized_input for signal in rule.required_signals
        ):
            continue

        matched_signals = tuple(
            signal
            for signal in (*rule.required_signals, *rule.optional_signals)
            if signal in normalized_input
        )
        score = len(matched_signals)

        if score > best_score:
            best_rule = rule
            best_score = score
            best_signals = matched_signals

    if not best_rule or best_score == 0:
        return IntentClassification(
            intent_type=INTENT_GENERIC_DOCUMENT_SEARCH,
            confidence="low",
            matched_signals=(),
            normalized_input=normalized_input,
        )

    confidence = "high" if best_score >= 3 else "medium"
    return IntentClassification(
        intent_type=best_rule.intent_type,
        confidence=confidence,
        matched_signals=best_signals,
        normalized_input=normalized_input,
    )

