from openai import OpenAI
import os
from datetime import datetime
import json
import logging

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

    # Usa Responses API com GPT-5 + prompt_id
    response = client.responses.create(
        model="gpt-5",
        prompt = { "id": prompt_id },
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}]
            }
        ],
        store=True,
        include=[
            "reasoning.encrypted_content",
            "web_search_call.action.sources"
        ],
        timeout=600
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
