import json
import re


def safe_load_json(raw_output: str):
    raw_output = raw_output.strip()

    # tenta carregar diretamente
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        pass

    # remove blocos de código Markdown ``` ou ```json
    raw_output = re.sub(r"^```[a-zA-Z]*\n?", "", raw_output)
    raw_output = re.sub(r"\n?```$", "", raw_output)
    raw_output = raw_output.strip()

    # substitui aspas simples por duplas (apenas se necessário)
    raw_output = raw_output.replace("'", '"')

    # remove quebras de linha extras
    raw_output = re.sub(r"\n", "", raw_output)

    # tenta novamente
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError as e:
        # se ainda falhar, loga e retorna lista vazia
        print(f"Failed to parse JSON output: {e}\nRaw output: {raw_output}")
        return []
