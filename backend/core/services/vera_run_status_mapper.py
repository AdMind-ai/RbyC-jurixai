from __future__ import annotations

from typing import Optional


TOOL_STATUS_MESSAGES = {
    "read_file": "Analizzando i documenti",
    "search_files": "Analizzando i documenti",
    "vision_analyze": "Analizzando i documenti",
    "execute_code": "Consultando il file",
    "web_search": "Verificando le fonti",
    "delegate_task": "Preparando la bozza",
}

DEFAULT_STATUS_MESSAGE = "Elaborazione in corso"


def map_vera_tool_event_to_status(event: dict) -> Optional[str]:
    if event.get("event") != "tool.started":
        return None

    tool_name = str(event.get("tool") or "").strip()
    return TOOL_STATUS_MESSAGES.get(tool_name, DEFAULT_STATUS_MESSAGE)
