from openai import OpenAI
import os
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO)


def generate_doc_with_assistant(format, language, instructions):
    client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
    assistant_id = "asst_a7DcahiXc3hHdwtF8fQZyCSf"

    # Input message reforçando tipo/idioma
    user_prompt = (
        f"Document format: {format}.\n"
        f"Language: {language}.\n"
        f"Instructions: {instructions}\n"
        "Please reply ONLY in json as per the guidelines."
    )

    assistant = client.beta.assistants.retrieve(
        assistant_id=assistant_id
    )

    # 1. Cria um thread
    thread = client.beta.threads.create()
    # 2. Roda o assistant
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions=user_prompt
    )

    # 3. Espera finalizar
    import time
    while True:
        if run.status in ["completed", "failed", "cancelled", "expired"]:
            break
        time.sleep(1)

    if run.status != "completed":
        raise Exception(f"Assistant run failed: {run.status}")

    # 4. Busca resposta
    messages = client.beta.threads.messages.list(
        thread_id=thread.id
    )
    logging.info(f"[OpenAI Assistant]:\n{messages}")

    # Procura o JSON no conteúdo
    response_content = messages.data[-1].content[0].text.value if messages.data else ""

    start = response_content.find('{')
    end = response_content.rfind('}')+1
    struct_json = response_content[start:end]
    try:
        doc_info = json.loads(struct_json)
        filename = doc_info.get(
            "filename", f"{format}_{datetime.now().strftime('%Y-%m-%d')}")
        title = doc_info.get("title", "")
        body = doc_info.get("body", "")

        # Extração de data dentro da body (opcional, example only)
        import re
        date_match = re.search(r"Date[:\-]?\s*([^\n]+)", body)
        if date_match:
            date_str = date_match.group(1).strip()
        else:
            date_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        # Você pode retornar o title também, se quiser
        return filename, title, date_str, body
    except Exception as e:
        logging.error(f"[OpenAI Assistant] Error parsing response JSON: {e}")
        logging.error(f"JSON Received: {struct_json}")
        return f"{format}_{datetime.now().strftime('%Y-%m-%d')}", datetime.now().strftime('%Y-%m-%d'), response_content
