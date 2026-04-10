from pathlib import Path
from openai import OpenAI
import os
from datetime import datetime
import json
import logging
from django.conf import settings
from core.utils.storage import get_storage_url

logging.basicConfig(level=logging.INFO)

def generate_doc_with_assistant(format, language, instructions):
    client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

    # Prompt ID já salvo no Playground
    prompt_id = settings.OPENAI_PROMPT_ID_QUICKDOC

    # Reforça no input do usuário
    user_prompt = (
        f"Document format: {format}.\n"
        f"Language: {language}.\n"
        f"Instructions: {instructions}\n"
        "Please reply ONLY in json as per the guidelines."
    )
    
    print(f"User prompt: {user_prompt}")
    
    input = [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_prompt}]
        }
    ]
    
    if format.lower() == "verbale cda":
        template_url = settings.QUICKDOC_VERBALE_CDA_TEMPLATE_URL
        if not template_url and settings.QUICKDOC_VERBALE_CDA_TEMPLATE_KEY:
            template_url = get_storage_url(settings.QUICKDOC_VERBALE_CDA_TEMPLATE_KEY)

        if not template_url:
            logging.warning(
                "QuickDoc verbale CDA template URL/key not configured. Proceeding without template attachment."
            )
        else:
            input = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "file_url": template_url,
                        },
                        {"type": "input_text", "text": user_prompt}
                    ]
                }
            ]

    # Usa Responses API com GPT-5 + prompt_id
    response = client.responses.create(
        model="gpt-5",
        prompt = { "id": prompt_id },
        input=input,
        store=True,
        timeout=900
    )

    response_content = response.output_text

    # Extrai o JSON da resposta
    start = response_content.find('{')
    end = response_content.rfind('}') + 1
    struct_json = response_content[start:end]

    try:
        doc_info = json.loads(struct_json)

        filename = doc_info.get("filename", f"{format}_{datetime.now().strftime('%Y-%m-%d')}")
        title = doc_info.get("title", "")
        body = doc_info.get("body", "")
        date_str = doc_info.get("date", datetime.now().strftime('%Y-%m-%d'))

        return filename, title, date_str, body
    except Exception as e:
        logging.error(f"[Chat GPT-5] Error parsing response JSON: {e}")
        logging.error(f"JSON Received: {struct_json}")
        return f"{format}_{datetime.now().strftime('%Y-%m-%d')}", datetime.now().strftime('%Y-%m-%d'), response_content
