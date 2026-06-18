from core.services.document_retrieval.intent_classifier import (
    INTENT_APPOINTMENT_AND_POWERS,
    INTENT_CONSOB_TOPIC_MEETING_TRACKING,
    INTENT_CONTROL_FUNCTIONS_FINDINGS_AND_REMEDIES,
    INTENT_CROSS_DOCUMENT_COVERAGE,
    INTENT_DIRECTOR_GENERAL_APPOINTMENT_CHECK,
    INTENT_FINANCIAL_SUMMARY_LAST_THREE_YEARS,
    INTENT_INVESTMENT_POLICIES_SUMMARY_BY_BOARD,
    INTENT_ORGANIZATIONAL_STRUCTURE_YEAR_COMPARISON,
    INTENT_RISK_MANAGEMENT_BOARD_INVOLVEMENT,
    IntentClassification,
)
from core.services.document_retrieval.retrieval_strategies import (
    RetrievalStrategy,
)


def build_evidence_plan(
    intent_classification: IntentClassification,
    retrieval_strategy: RetrievalStrategy,
) -> str:
    if (
        intent_classification.intent_type
        == INTENT_APPOINTMENT_AND_POWERS
    ):
        return (
            "Prima di sintetizzare, compatta l'evidenza intorno all'evento di "
            "nomina. Individua prima la riunione o il documento di governance "
            "in cui l'Amministratore Delegato viene nominato in modo esplicito "
            "e, nella stessa fonte o in una fonte strettamente collegata, "
            "verifica quali poteri gli sono attribuiti. Distingui chiaramente "
            "tra nomina, conferma di incarico, deleghe operative e semplici "
            "richiami successivi al ruolo gia esistente. Privilegia sempre "
            "come fonte primaria un verbale, estratto o altro documento "
            "societario di governance rispetto a CV, autodichiarazioni o "
            "documenti personali, che possono essere usati solo come contesto "
            "secondario. Non usare documenti biografici come base principale "
            "per datare la nomina se esiste una fonte societaria esplicita. "
            "Non frammentare la risposta su piu riunioni se una fonte primaria "
            "contiene gia sia la nomina sia i poteri essenziali. Solo dopo "
            "aver identificato la fonte primaria, produci la sintesi finale."
        )

    if (
        intent_classification.intent_type
        == INTENT_DIRECTOR_GENERAL_APPOINTMENT_CHECK
    ):
        return (
            "Prima di sintetizzare, cerca evidenza documentale esplicita di "
            "nomina di un Direttore Generale. Distingui tra: nomina formale, "
            "semplice menzione del ruolo, attribuzione ad interim di compiti "
            "operativi, o assenza di evidenza. Se non trovi una nomina chiara, "
            "rispondi con cautela e non trasformare riferimenti indiretti o "
            "funzioni temporanee in una nomina formale. Se trovi una nomina, "
            "indica la riunione o il documento principale in cui emerge."
        )

    if (
        intent_classification.intent_type
        == INTENT_FINANCIAL_SUMMARY_LAST_THREE_YEARS
    ):
        return (
            "Prima di sintetizzare, compatta l'evidenza per esercizio. "
            "Individua prima i tre esercizi cronologicamente piu recenti "
            "disponibili nei materiali consultabili e privilegia quelli, "
            "senza fermarti a una serie storica piu vecchia solo perche "
            "piu compatta in un singolo documento. Seleziona al massimo un "
            "documento principale per anno e usa solo eventuali documenti "
            "aggiuntivi se indispensabili a colmare un vuoto informativo "
            "concreto. Se un bilancio piu recente contiene dati comparativi "
            "su anni precedenti, usalo come supporto ma verifica comunque "
            "che l'esercizio piu recente disponibile sia coperto. Costruisci "
            "prima una vista per anno con pochi dati chiave per ciascun "
            "esercizio e solo dopo produci la sintesi finale."
        )

    if (
        intent_classification.intent_type
        == INTENT_CONTROL_FUNCTIONS_FINDINGS_AND_REMEDIES
    ):
        return (
            "Prima di sintetizzare, compatta l'evidenza per funzione di "
            "controllo. Costruisci separatamente i blocchi Compliance, Risk "
            "Management e Internal Audit. Seleziona al massimo un documento "
            "principale per funzione e usa documenti aggiuntivi solo se "
            "necessari a chiarire rilievi o rimedi non coperti dal documento "
            "principale. Privilegia preview ed excerpt e ricorri alla lettura "
            "full solo se nel materiale gia aperto manca davvero uno di questi "
            "tre elementi per una specifica funzione: rilievi principali, "
            "stato delle criticita, oppure piani di rimedio o azioni "
            "correttive proposte. Se un verbale richiama o sintetizza in modo "
            "sufficiente una relazione di controllo, non aprire il documento "
            "completo solo per conferme ridondanti. Non superare un documento "
            "principale per funzione se quel documento gia copre i tre "
            "elementi richiesti. Evita di espandere la ricerca verso documenti "
            "tematicamente correlati, come piani industriali, ICARAP, "
            "remunerazioni o verbali di comitati, salvo che il documento "
            "principale della funzione rimandi in modo necessario a quei "
            "materiali per colmare un vuoto informativo concreto. Per ciascuna "
            "funzione, estrai in modo sintetico: rilievi principali, stato "
            "delle criticita e piani di rimedio o azioni correttive proposte. "
            "Solo dopo aver costruito i tre blocchi, produci la sintesi finale "
            "trasversale del 2025."
        )

    if (
        intent_classification.intent_type
        == INTENT_CONSOB_TOPIC_MEETING_TRACKING
    ):
        return (
            "Prima di sintetizzare, compatta l'evidenza per riunione del CdA. "
            "Individua tutte le riunioni in cui il tema Consob appare in modo "
            "esplicito, anche se in fasi diverse dello stesso procedimento "
            "come informativa iniziale, contestazione, avvio del procedimento "
            "sanzionatorio o valutazione di impegni. Non limitarti solo alla "
            "riunione con la delibera o il passaggio piu formale se esistono "
            "riunioni precedenti che trattano chiaramente lo stesso tema. "
            "Escludi riferimenti a Banca d'Italia o ad altre autorita, salvo "
            "usarli solo come contrasto esplicito per chiarire che non "
            "rientrano nella risposta. Per ogni riunione rilevante, estrai "
            "in modo sintetico la data e il motivo per cui il tema Consob e "
            "trattato. Solo dopo aver costruito l'elenco delle riunioni "
            "rilevanti, produci la sintesi finale."
        )

    if (
        intent_classification.intent_type
        == INTENT_INVESTMENT_POLICIES_SUMMARY_BY_BOARD
    ):
        return (
            "Prima di sintetizzare, compatta l'evidenza per riunione del CdA "
            "nel periodo richiesto dalla domanda o, se non specificato, nel "
            "periodo dominante e piu coerente che emerge dai materiali "
            "consultati. Individua solo le riunioni in cui emerge una "
            "deliberazione, conferma, revisione o discussione sostanziale "
            "della politica di investimento o della asset allocation sui "
            "portafogli in delega. Distingui chiaramente tra: continuita "
            "delle investment guidelines, aggiustamenti puntuali su singoli "
            "prodotti o fondi, e vere modifiche di policy o asset allocation. "
            "Non trasformare aggiornamenti generici sull'andamento della "
            "gestione in cambi di politica se i documenti indicano continuita. "
            "Per ogni riunione rilevante, estrai in modo sintetico: data, "
            "decisione o orientamento espresso dal CdA, e nesso con i "
            "portafogli in delega. Solo dopo aver costruito l'elenco delle "
            "riunioni rilevanti, produci la sintesi finale del 2025."
        )

    if (
        intent_classification.intent_type
        == INTENT_ORGANIZATIONAL_STRUCTURE_YEAR_COMPARISON
    ):
        return (
            "Prima di sintetizzare, compatta l'evidenza per anno e confronta "
            "solo documenti equivalenti o chiaramente comparabili tra loro. "
            "Privilegia un documento principale per il 2025 e uno per il 2024, "
            "entrambi relativi alla struttura organizzativa o al suo "
            "aggiornamento, e usa eventuali documenti aggiuntivi solo per "
            "chiarire differenze concrete non coperte dai documenti principali. "
            "Distingui chiaramente tra: modifiche sostanziali di contenuto, "
            "aggiornamenti formali o organizzativi minori, e semplice "
            "continuita della struttura. Non descrivere come modifica reale "
            "una differenza che nei materiali consultati appare solo lessicale "
            "o redazionale. Per ciascun anno, estrai in modo sintetico i punti "
            "chiave della struttura o degli aggiornamenti rilevanti. Solo dopo "
            "aver costruito i due blocchi annuali, produci il confronto finale."
        )

    if (
        intent_classification.intent_type
        == INTENT_RISK_MANAGEMENT_BOARD_INVOLVEMENT
    ):
        return (
            "Prima di sintetizzare, compatta l'evidenza per riunione del CdA. "
            "Salvo indicazione contraria nella domanda, privilegia le riunioni "
            "del periodo piu coerente e piu recente che emerge dai materiali "
            "trovati, evitando di mescolare anni diversi senza una necessita "
            "documentale concreta. "
            "Individua solo le riunioni in cui emerge evidenza diretta del "
            "coinvolgimento della funzione di Risk Management sulla politica "
            "di investimento, ad esempio tramite pareri, analisi, report, "
            "valutazioni del rischio, contributi alla asset allocation o "
            "richiami espliciti al report di Risk Management sulla gestione. "
            "Non contare menzioni generiche della funzione se non sono "
            "collegate alla politica di investimento o ai portafogli in "
            "delega, e non contare la sola presenza della funzione o il solo "
            "rinvio a materiali allegati se non emerge che abbia svolto o "
            "presentato un contributo analitico concreto nella riunione. "
            "Conta una riunione solo quando il nesso tra Risk Management, "
            "analisi svolta e politica di investimento risulta esplicito o "
            "direttamente inferibile dai passaggi consultati senza salti "
            "interpretativi. "
            "Se l'evidenza e solo indiziaria o indiretta, segnalala "
            "separatamente ma non includerla nel conteggio finale. "
            "Per ogni riunione rilevante, estrai in modo sintetico: "
            "data, tipo di coinvolgimento e nesso con la politica di "
            "investimento. Solo dopo aver costruito l'elenco delle riunioni "
            "rilevanti, produci il conteggio finale e la sintesi conclusiva."
        )

    if (
        intent_classification.intent_type
        == INTENT_CROSS_DOCUMENT_COVERAGE
    ):
        return (
            "Prima di sintetizzare, tratta la domanda come copertura "
            "trasversale. Usa i risultati di search_documents come candidate "
            "set iniziale dei documenti o delle sedute pertinenti, non come "
            "semplice lista da ridurre ai primi elementi. Raggruppa per "
            "documento o, quando emergono date di riunione, per seduta; "
            "deduplica copie, bozze o versioni della stessa seduta quando "
            "possibile. Per ogni candidato rilevante, conserva data, tipo di "
            "evidenza e motivo della pertinenza. Distingui chiaramente tra "
            "semplice occorrenza testuale e trattazione esplicita del tema. "
            "Solo dopo aver costruito questa vista trasversale, produci il "
            "conteggio, l'elenco di date o la sintesi richiesta."
        )

    return ""
