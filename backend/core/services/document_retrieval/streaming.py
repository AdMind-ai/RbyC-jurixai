import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from django.conf import settings

from core.utils.openai_client import client


logger = logging.getLogger(__name__)


PHASE_INTENT_DETECTION = "intent_detection"
PHASE_PLANNING = "planning"
PHASE_SEARCHING = "searching"
PHASE_READING = "reading"
PHASE_COMPACTING_EVIDENCE = "compacting_evidence"
PHASE_SYNTHESIZING = "synthesizing"
PHASE_COMPLETED = "completed"
PHASE_ERROR = "error"

STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


INTENT_LABELS = {
    "control_functions_findings_and_remedies": (
        "rilievi delle funzioni di controllo e relativi piani di rimedio"
    ),
    "organizational_structure_year_comparison": (
        "confronto della struttura organizzativa tra esercizi diversi"
    ),
    "director_general_appointment_check": (
        "verifica della nomina del Direttore Generale"
    ),
    "financial_statements_multi_year_summary": (
        "sintesi dei dati di bilancio su piu esercizi"
    ),
}


@dataclass
class DocumentSearchExecutionEvent:
    request_id: str
    phase: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_type: str = "execution_event"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def as_payload(self) -> dict[str, Any]:
        return asdict(self)


def build_execution_event(
    *,
    request_id: str,
    phase: str,
    status: str,
    payload: dict[str, Any] | None = None,
) -> DocumentSearchExecutionEvent:
    return DocumentSearchExecutionEvent(
        request_id=request_id,
        phase=phase,
        status=status,
        payload=payload or {},
    )


def encode_sse_event(event_name: str, data: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def iter_text_deltas(text: str, chunk_size: int = 180) -> list[str]:
    normalized_text = text or ""
    if not normalized_text:
        return []
    return [
        normalized_text[index : index + chunk_size]
        for index in range(0, len(normalized_text), chunk_size)
    ]


def humanize_intent_label(intent_type: str) -> str:
    if not intent_type:
        return "ricerca documentale"

    if intent_type in INTENT_LABELS:
        return INTENT_LABELS[intent_type]

    return intent_type.replace("_", " ")


class DocumentSearchNarrationService:
    """
    Small narrator layer for the streaming UX.

    It can use a lightweight model when configured, and falls back to
    deterministic contextual phrasing if the narration call fails.
    """

    def __init__(self):
        self.model = getattr(
            settings,
            "DOCUMENT_SEARCH_STREAM_NARRATION_MODEL",
            "",
        )
        self.use_model = getattr(
            settings,
            "DOCUMENT_SEARCH_STREAM_NARRATION_USE_MODEL",
            False,
        )

    def build_narration_event(
        self,
        *,
        request_id: str,
        user_prompt: str,
        execution_event: DocumentSearchExecutionEvent,
        previous_events: list[DocumentSearchExecutionEvent] | None = None,
    ) -> dict[str, Any]:
        text = self._generate_text(
            user_prompt=user_prompt,
            execution_event=execution_event,
            previous_events=previous_events or [],
        )
        logger.info(
            "[document_search_stream] narration_event_built request_id=%s phase=%s status=%s use_model=%s text_length=%s",
            request_id,
            execution_event.phase,
            execution_event.status,
            bool(self.use_model and self.model),
            len(text or ""),
        )
        return {
            "type": "narration_event",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text": text,
            "phase": execution_event.phase,
        }

    def _generate_text(
        self,
        *,
        user_prompt: str,
        execution_event: DocumentSearchExecutionEvent,
        previous_events: list[DocumentSearchExecutionEvent],
    ) -> str:
        try:
            return self._generate_text_with_model(
                user_prompt=user_prompt,
                execution_event=execution_event,
                previous_events=previous_events,
            )
        except ValueError:
            return self._fallback_text(
                user_prompt=user_prompt,
                execution_event=execution_event,
                previous_events=previous_events,
            )
        except Exception:
            logger.exception(
                "[document_search_stream] narration_generation_failed phase=%s",
                execution_event.phase,
            )
            return self._fallback_text(
                user_prompt=user_prompt,
                execution_event=execution_event,
                previous_events=previous_events,
            )

    def _generate_text_with_model(
        self,
        *,
        user_prompt: str,
        execution_event: DocumentSearchExecutionEvent,
        previous_events: list[DocumentSearchExecutionEvent],
    ) -> str:
        if not self.use_model or not self.model:
            raise ValueError("Narration model not configured")

        previous_summary = [
            {
                "phase": event.phase,
                "status": event.status,
                "payload": event.payload,
            }
            for event in previous_events[-2:]
        ]
        response = client.responses.create(
            model=self.model,
            input=(
                "Sei un narratore di avanzamento per una ricerca documentale. "
                "Scrivi una singola frase breve, naturale e contestuale in italiano. "
                "Non rispondere alla domanda finale dell'utente. "
                "Non descrivere log tecnici o tool in modo grezzo. "
                "Aggiorna solo sullo stato attuale del lavoro.\n\n"
                f"Domanda utente: {user_prompt}\n"
                f"Fase corrente: {execution_event.phase}\n"
                f"Stato: {execution_event.status}\n"
                f"Payload: {json.dumps(execution_event.payload, ensure_ascii=False)}\n"
                f"Eventi precedenti: {json.dumps(previous_summary, ensure_ascii=False)}"
            ),
            max_output_tokens=80,
            reasoning={"effort": "low"},
            timeout=30,
        )
        text = (getattr(response, "output_text", "") or "").strip()
        if not text:
            raise ValueError("Empty narration output")
        logger.info(
            "[document_search_stream] narration_generated_with_model phase=%s model=%s text_length=%s",
            execution_event.phase,
            self.model,
            len(text),
        )
        return " ".join(text.split())

    def _fallback_text(
        self,
        *,
        user_prompt: str,
        execution_event: DocumentSearchExecutionEvent,
        previous_events: list[DocumentSearchExecutionEvent] | None = None,
    ) -> str:
        previous_events = previous_events or []
        phase = execution_event.phase
        payload = execution_event.payload or {}
        intent = next(
            (
                event.payload.get("intent_type")
                for event in previous_events
                if event.phase == PHASE_INTENT_DETECTION and event.payload.get("intent_type")
            ),
            payload.get("intent_type") or "ricerca documentale",
        )
        readable_intent = humanize_intent_label(str(intent))
        focus = next(
            (
                event.payload.get("focus")
                for event in reversed(previous_events + [execution_event])
                if event.payload.get("focus")
            ),
            "",
        )
        focus_sentence = (
            f" con attenzione a {focus}" if isinstance(focus, str) and focus else ""
        )
        completed_phases = {event.phase for event in previous_events}

        if phase == PHASE_INTENT_DETECTION:
            text = (
                f"Sto inquadrando la richiesta per capire il perimetro piu adatto "
                f"al tema '{readable_intent}'."
            )
        elif phase == PHASE_PLANNING:
            text = (
                "Ho definito il perimetro della ricerca e sto scegliendo le fonti "
                "piu promettenti da confrontare."
            )
        elif phase == PHASE_SEARCHING:
            if PHASE_PLANNING in completed_phases:
                text = (
                    "Ho gia impostato il percorso di lavoro e ora sto cercando i "
                    f"documenti principali{focus_sentence} per costruire una risposta "
                    "solida e ben ancorata alle fonti."
                )
            else:
                text = (
                    f"Sto cercando i documenti piu rilevanti{focus_sentence} per capire "
                    "quali fonti usero come base della risposta."
                )
        elif phase == PHASE_READING:
            role = payload.get("document_role") or "fonte principale"
            family = payload.get("document_family") or "documento"

            role_map = {
                "supporting_source": "fonte di supporto",
                "primary_source": "fonte principale",
            }
            family_map = {
                "mixed": "documenti selezionati",
            }

            readable_role = role_map.get(str(role), str(role).replace("_", " "))
            readable_family = family_map.get(
                str(family), str(family).replace("_", " ")
            )
            text = (
                "Ho individuato le fonti piu promettenti e ora sto leggendo "
                f"una {readable_role} della famiglia '{readable_family}' per verificare rilievi, "
                "criticita e rimedi senza introdurre ridondanze."
            )
        elif phase == PHASE_COMPACTING_EVIDENCE:
            text = (
                "Ho raccolto i materiali principali e sto compattando i punti "
                "davvero utili, cosi la risposta finale resti chiara e senza "
                "ripetizioni superflue."
            )
        elif phase == PHASE_SYNTHESIZING:
            text = (
                "Le evidenze sono ormai consolidate; sto trasformando il confronto "
                "tra documenti e rilievi in una risposta ordinata, leggibile e fedele "
                "alle fonti."
            )
        elif phase == PHASE_COMPLETED:
            text = "La risposta e pronta."
        elif phase == PHASE_ERROR:
            text = "Si e verificato un problema durante la ricerca documentale."
        else:
            text = f"Sto lavorando sulla richiesta: {user_prompt[:80]}."

        logger.info(
            "[document_search_stream] narration_generated_with_fallback phase=%s text_length=%s",
            phase,
            len(text),
        )
        return text
