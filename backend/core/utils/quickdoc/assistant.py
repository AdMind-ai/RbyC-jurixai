from pathlib import Path
from openai import OpenAI
import os
from datetime import datetime
import json
import logging
from django.conf import settings
from core.utils.quickdoc.upload_to_blob_storage import generate_sas_token

logging.basicConfig(level=logging.INFO)

def generate_doc_with_assistant(format, language, instructions):
    client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

    # Prompt ID já salvo no Playground
    prompt_id = "pmpt_68caada8d3208197babfa45be05ee86809583cf9bed523b8"

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

        sas_token = generate_sas_token("quickdoc/templates/template_verbale_Cda.pdf")

        input = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_url": f"https://jurixaistorage.blob.core.windows.net/jurixai-rbyc-storage/quickdoc/templates/template_verbale_Cda.pdf?{sas_token}",
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
