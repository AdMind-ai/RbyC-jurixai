from dataclasses import dataclass

from core.services.document_retrieval.intent_classifier import (
    INTENT_APPOINTMENT_AND_POWERS,
    INTENT_CONSOB_TOPIC_MEETING_TRACKING,
    INTENT_CONTROL_FUNCTIONS_FINDINGS_AND_REMEDIES,
    INTENT_CROSS_DOCUMENT_COVERAGE,
    INTENT_DIRECTOR_GENERAL_APPOINTMENT_CHECK,
    INTENT_FINANCIAL_SUMMARY_LAST_THREE_YEARS,
    INTENT_GENERIC_DOCUMENT_SEARCH,
    INTENT_INVESTMENT_POLICIES_SUMMARY_BY_BOARD,
    INTENT_ORGANIZATIONAL_STRUCTURE_YEAR_COMPARISON,
    INTENT_RISK_MANAGEMENT_BOARD_INVOLVEMENT,
)


@dataclass(frozen=True)
class RetrievalStrategy:
    intent_type: str
    primary_tool: str = "search_documents"
    prefer_preview_only: bool = True
    max_documents_to_open: int = 2
    group_by: str = ""
    evidence_grouping: str = ""
    query_anchor_terms: tuple[str, ...] = ()
    preferred_document_families: tuple[str, ...] = ()
    preferred_topic_tags: tuple[str, ...] = ()
    preferred_control_functions: tuple[str, ...] = ()
    preferred_filename_contains: tuple[str, ...] = ()
    preferred_sort_by: str = ""
    preferred_sort_order: str = ""
    notes: str = ""
    stopping_rule: str = ""


RETRIEVAL_STRATEGIES = {
    INTENT_APPOINTMENT_AND_POWERS: RetrievalStrategy(
        intent_type=INTENT_APPOINTMENT_AND_POWERS,
        prefer_preview_only=False,
        max_documents_to_open=3,
        group_by="meeting_date",
        query_anchor_terms=("amministratore delegato", "nomina"),
        preferred_document_families=("verbale_cda", "estratto_cda", "nomina"),
        preferred_topic_tags=("nomina", "poteri", "deleghe"),
        notes="Priorizar documentos de nomeacao e atribuicao de poderes.",
        stopping_rule=(
            "Se trovi una riunione o un documento di governanza che "
            "contiene insieme nomina e attribuzione di poteri, trattalo come "
            "fonte primaria e amplia la ricerca solo per chiarire date o "
            "deleghe mancanti."
        ),
    ),
    INTENT_DIRECTOR_GENERAL_APPOINTMENT_CHECK: RetrievalStrategy(
        intent_type=INTENT_DIRECTOR_GENERAL_APPOINTMENT_CHECK,
        prefer_preview_only=True,
        max_documents_to_open=2,
        query_anchor_terms=("direttore generale",),
        preferred_document_families=("verbale_cda", "estratto_cda", "nomina"),
        preferred_topic_tags=("direttore_generale", "nomina"),
        notes="Busca objetiva por existencia de nomeacao.",
        stopping_rule=(
            "Se non trovi una nomina formale ed esplicita di Direttore "
            "Generale in una fonte societaria rilevante, non ampliare la "
            "ricerca con inferenze biografiche o riferimenti indiretti: "
            "rispondi con cautela sulla base dell'evidenza disponibile."
        ),
    ),
    INTENT_FINANCIAL_SUMMARY_LAST_THREE_YEARS: RetrievalStrategy(
        intent_type=INTENT_FINANCIAL_SUMMARY_LAST_THREE_YEARS,
        prefer_preview_only=False,
        max_documents_to_open=4,
        group_by="year",
        evidence_grouping="year",
        query_anchor_terms=("bilancio",),
        preferred_document_families=("bilancio", "relazione_finanziaria"),
        preferred_topic_tags=("bilancio", "dati_finanziari"),
        notes="Agrupar por ano e limitar leitura a documentos financeiros principais.",
        stopping_rule=(
            "Quando hai gia coperto i tre esercizi piu recenti con un "
            "documento principale per anno o con una serie comparativa "
            "sufficiente, non riaprire la ricerca con varianti generiche."
        ),
    ),
    INTENT_CONTROL_FUNCTIONS_FINDINGS_AND_REMEDIES: RetrievalStrategy(
        intent_type=INTENT_CONTROL_FUNCTIONS_FINDINGS_AND_REMEDIES,
        prefer_preview_only=False,
        max_documents_to_open=4,
        group_by="year",
        evidence_grouping="control_function",
        query_anchor_terms=("risk", "compliance", "internal audit"),
        preferred_document_families=("report_controlli", "verbale_cda"),
        preferred_topic_tags=("rilievi", "rimedi", "action_plan"),
        preferred_control_functions=("risk", "compliance", "internal_audit"),
        notes="Priorizar funcoes de controle e evidencias de remedios.",
        stopping_rule=(
            "Dopo avere identificato un documento principale pertinente per "
            "ciascuna funzione di controllo, non tornare a ricerche testuali "
            "ampie salvo mancanza reale di evidenze su rilievi o rimedi."
        ),
    ),
    INTENT_INVESTMENT_POLICIES_SUMMARY_BY_BOARD: RetrievalStrategy(
        intent_type=INTENT_INVESTMENT_POLICIES_SUMMARY_BY_BOARD,
        prefer_preview_only=False,
        max_documents_to_open=3,
        group_by="meeting_date",
        query_anchor_terms=("politica di investimento",),
        preferred_document_families=("verbale_cda", "estratto_cda", "policy"),
        preferred_topic_tags=("politica_investimento", "portafogli_delega"),
        notes="Agrupar por reuniao do CdA e priorizar deliberacoes.",
        stopping_rule=(
            "Se i verbali o estratti del CdA del 2025 mostrano gia una linea "
            "coerente sulle politiche di investimento, usa quei documenti come "
            "base e cerca altro solo per coprire delibere o eccezioni "
            "chiaramente mancanti."
        ),
    ),
    INTENT_RISK_MANAGEMENT_BOARD_INVOLVEMENT: RetrievalStrategy(
        intent_type=INTENT_RISK_MANAGEMENT_BOARD_INVOLVEMENT,
        prefer_preview_only=False,
        max_documents_to_open=3,
        group_by="meeting_date",
        query_anchor_terms=("risk management",),
        preferred_document_families=("verbale_cda", "report_controlli"),
        preferred_topic_tags=("politica_investimento",),
        preferred_control_functions=("risk",),
        notes="Buscar ocorrencias por reuniao e sinais de participacao da funcao.",
        stopping_rule=(
            "Quando hai gia trovato riunioni con evidenza diretta del "
            "coinvolgimento del Risk Management, evita nuove ricerche generiche "
            "e limita eventuali approfondimenti al conteggio o ai dettagli "
            "mancanti."
        ),
    ),
    INTENT_ORGANIZATIONAL_STRUCTURE_YEAR_COMPARISON: RetrievalStrategy(
        intent_type=INTENT_ORGANIZATIONAL_STRUCTURE_YEAR_COMPARISON,
        prefer_preview_only=False,
        max_documents_to_open=4,
        group_by="year",
        evidence_grouping="year",
        query_anchor_terms=("struttura organizzativa",),
        preferred_document_families=("relazione_struttura_organizzativa",),
        preferred_topic_tags=("struttura_organizzativa",),
        preferred_filename_contains=("rso",),
        preferred_sort_by="document_date",
        preferred_sort_order="desc",
        notes=(
            "Selecionar documentos equivalentes de anos distintos para comparacao. "
            "Per domande sulla versione piu recente, usa prima filtri strutturati "
            "su RSO/struttura organizzativa e ordina per document_date desc, "
            "poi verifica l'approvazione leggendo solo i documenti finalist."
        ),
        stopping_rule=(
            "Se hai gia identificato i documenti equivalenti del 2024 e 2025, "
            "non riaprire la fase di scoperta con nuove ricerche generiche: "
            "passa direttamente al confronto."
        ),
    ),
    INTENT_CONSOB_TOPIC_MEETING_TRACKING: RetrievalStrategy(
        intent_type=INTENT_CONSOB_TOPIC_MEETING_TRACKING,
        prefer_preview_only=False,
        max_documents_to_open=3,
        group_by="meeting_date",
        query_anchor_terms=("consob",),
        preferred_document_families=("verbale_cda", "estratto_cda"),
        preferred_topic_tags=("consob", "contestazioni"),
        notes="Agrupar por reuniao e localizar tratamento do tema Consob.",
        stopping_rule=(
            "Quando hai gia individuato riunioni del CdA che menzionano in "
            "modo esplicito contestazioni o procedimento sanzionatorio Consob, "
            "non espandere la ricerca con nuove varianti salvo dubbio reale su "
            "altre riunioni con lo stesso livello di evidenza."
        ),
    ),
    INTENT_CROSS_DOCUMENT_COVERAGE: RetrievalStrategy(
        intent_type=INTENT_CROSS_DOCUMENT_COVERAGE,
        prefer_preview_only=False,
        max_documents_to_open=6,
        group_by="document_or_meeting",
        preferred_document_families=("verbale_cda", "estratto_cda"),
        notes=(
            "Usar cobertura transversal quando a pergunta pede quando, quantas "
            "vezes, em quais documentos/reunioes/sedute ou onde um tema aparece."
        ),
        stopping_rule=(
            "Non fermarti ai primi 3-5 risultati se la domanda chiede conteggio, "
            "date, occorrenze o copertura trasversale. Costruisci prima un "
            "candidate set dei documenti o delle sedute pertinenti, deduplica "
            "copie/versioni della stessa seduta quando possibile, poi sintetizza."
        ),
    ),
    INTENT_GENERIC_DOCUMENT_SEARCH: RetrievalStrategy(
        intent_type=INTENT_GENERIC_DOCUMENT_SEARCH,
        prefer_preview_only=True,
        max_documents_to_open=2,
        notes="Fallback generico para perguntas fora do catalogo inicial.",
    ),
}


def get_retrieval_strategy(intent_type: str) -> RetrievalStrategy:
    return RETRIEVAL_STRATEGIES.get(
        intent_type,
        RETRIEVAL_STRATEGIES[INTENT_GENERIC_DOCUMENT_SEARCH],
    )
