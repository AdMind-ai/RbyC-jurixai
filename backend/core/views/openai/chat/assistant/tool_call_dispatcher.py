import json
from core.utils.assistants import *


def summarize_response(response_json, max_chars=250000):
    """
    Returns as many records from `.value` as fit in `max_chars` chars when serialized to JSON.
    Adds a notice if result was truncated.
    Always returns a valid JSON string.
    """
    if isinstance(response_json, dict) and "value" in response_json and isinstance(response_json["value"], list):
        total = len(response_json["value"])
        summarized = response_json.copy()
        summarized["value"] = []
        # Start with at least the other fields
        notice_added = False

        for i, item in enumerate(response_json["value"]):
            summarized["value"].append(item)
            # Tentatively add a notice if will be truncated after this
            if i < total - 1:
                temp_json = summarized.copy()
                temp_json["__notice__"] = f"Truncated to {i+1} results out of {total} total"
                serialized = json.dumps(temp_json, ensure_ascii=False)
                next_len = len(serialized)
            else:
                serialized = json.dumps(summarized, ensure_ascii=False)
                next_len = len(serialized)

            if next_len > max_chars:
                # Remove the last appended item (too big)
                summarized["value"].pop()
                summarized["__notice__"] = f"Truncated to {i} results out of {total} total"
                return json.dumps(summarized, ensure_ascii=False)

        # Not truncated, just return full as it fits
        return json.dumps(summarized, ensure_ascii=False)
    # For other types, just truncate the output
    return json.dumps(response_json, ensure_ascii=False)[:max_chars]


def dispatch_tool_call(tool, tool_outputs):
    name = tool.function.name
    args = {}
    if tool.function.arguments:
        try:
            args = json.loads(tool.function.arguments)
        except Exception:
            args = {}

    if name == "get_now_datetime":
        output = get_now_datetime()
        val = output.isoformat() if hasattr(output, "isoformat") else str(output)
        tool_outputs.append({"tool_call_id": tool.id, "output": val})

    else:
        tool_outputs.append(
            {"tool_call_id": tool.id, "output": f"The function '{name}' is not implemented."})
