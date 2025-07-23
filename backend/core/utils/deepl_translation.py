import os
import tempfile
from datetime import datetime

import deepl
from django.conf import settings


class DeeplTranslation:

    GLOSSARIES = {
        'IT_PT': '9f605aa7-564c-4033-9996-36186296f4e0',
        'ES_DE': 'b534176d-1566-4fad-8fdf-8bb054c5d5f8',
        'EN_ES': '47aa2dc8-a89b-4539-8299-e4ebba243333',
        'PT_EN': '8ed2b4fd-d3de-44c8-adda-25419c267479',
        'FR_EN': '21f9dc32-8502-4a0a-9355-4b2be09ffd0b',
        'FR_DE': 'c4edd1b9-c956-485e-b646-d9daba1a0058',
        'DE_ES': '9b166181-9bb5-4648-8a63-7855a4383d3f',
        'PT_FR': '645132cf-4663-4dbd-bb70-2e99565f5e15',
        'ES_PT': '495959ae-5efc-4ceb-a43f-4e494765f06f',
        'PT_DE': 'fddb496b-b1c7-419c-83a7-713d653e3829',
        'PT_IT': 'b12d6678-c34c-480a-a7f4-021e1c6ba094',
        'ES_FR': '45647322-bea5-446b-9a41-c207f19e01ac',
        'DE_IT': '84272e7c-f2aa-47e4-8c7c-0659ec1603ce',
        'PT_ES': '7cf15bbc-b737-442d-a94b-0d6d19e0202c',
        'IT_ES': '0716d270-456b-4971-809d-6ad8983132bf',
        'EN_FR': '101bc67d-3157-441b-af6e-4baa75d16170',
        'EN_DE': 'e2dd21ef-7c60-45e1-af0c-c8b8936f6c48',
        'EN_PT': '08ba7ae5-2053-4cf4-b0fb-1550132244c1',
        'FR_ES': 'c3af223c-b056-49ef-801a-176c60621708',
        'ES_EN': '74af2646-064c-4e3d-b66e-b73eaa765d17',
        'FR_PT': 'a6a3c4bc-4ecb-443c-af2e-867e7ff9ca17',
        'IT_FR': '84c6a917-e6bb-41fd-afa0-f86de8c39c30',
        'DE_FR': 'efc85855-4382-4129-b44b-639dcee92bb8',
        'IT_DE': 'b8ab828b-5444-4688-98ab-6c9bdeaa90ce',
        'FR_IT': 'e7790fcb-f54c-4088-a810-d4f2a2378c81',
        'DE_EN': 'cbc05ff9-93f3-4128-8735-13fd6ff46e34',
        'DE_PT': 'b09ad318-235b-415f-ba72-b81d60e683e9',
        'ES_IT': 'acb52976-7aed-48e4-bf27-98ac49d44270',
        'EN_IT': '2a249815-68d5-46ca-a110-a59bf24a3945',
        'IT_EN': '633a0dfb-4ac7-4fbf-9c63-0ab3d24d9393'
    }

    TARGET = {
        'english': 'EN-US',
        'french': 'FR',
        'german': 'DE',
        'greek': 'EL',
        'italian': 'IT',
        'portuguese': 'PT-BR',
        'spanish': 'ES',
    }

    def __init__(self, deepl_key):
        self.key = deepl_key

    def translate_file(self, file, target, origin):

        file_b = file.read()
        translator = deepl.Translator(self.key)
        filename_without_extension, extension = os.path.splitext(file.name)
        file_path = os.path.join(settings.MEDIA_ROOT, 'files')
        os.makedirs(file_path, exist_ok=True)

        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=extension, dir=file_path
        )

        target_lang = self.TARGET.get(target)
        source_lang = self.TARGET.get(origin)

        try:
            if source_lang != 'EL' and target_lang != 'EL':
                glossary = self.GLOSSARIES[
                    f'{source_lang[:2]}_{target_lang[:2]}'
                ]
                translator.translate_document(
                    file_b,
                    temp_file,
                    filename=file.name,
                    target_lang=target_lang,
                    source_lang=source_lang[:2],
                    glossary=glossary,
                )
            else:
                translator.translate_document(
                    file_b,
                    temp_file,
                    filename=file.name,
                    target_lang=target_lang,
                    source_lang=source_lang[:2],
                )

            temp_file.close()

            formatted_date = datetime.now().strftime("%Y-%m-%d-%H%M%S%f")
            clean_filename = filename_without_extension.replace(
                "_tradotto", "")
            new_filename = f"{clean_filename}_{formatted_date}_tradotto{extension}"

            final_path = os.path.join(file_path, new_filename)
            if os.path.exists(final_path):
                os.remove(final_path)

            os.rename(temp_file.name, final_path)

            return new_filename

        except deepl.DocumentTranslationException as error:
            doc_id = error.document_handle.id
            doc_key = error.document_handle.key
            print(
                f'Error after uploading ${error}, id: ${doc_id} key: ${doc_key}'
            )
        except deepl.DeepLException as error:
            print(error)

        return os.path.basename(temp_file.name)

    def translate_text(self, text, origin, target):
        translator = deepl.Translator(self.key)

        target_lang = self.TARGET.get(target.lower())
        source_lang = self.TARGET.get(origin.lower())

        if not target_lang or not source_lang:
            return {"error": "Invalid language."}

        try:
            if source_lang != 'EL' and target_lang != 'EL':
                glossary_key = f'{source_lang[:2]}_{target_lang[:2]}'
                glossary_id = self.GLOSSARIES.get(glossary_key)

                if glossary_id:
                    result = translator.translate_text(
                        text,
                        source_lang=source_lang[:2],
                        target_lang=target_lang,
                        glossary=glossary_id
                    )
                else:
                    result = translator.translate_text(
                        text,
                        source_lang=source_lang[:2],
                        target_lang=target_lang
                    )
            else:
                result = translator.translate_text(
                    text,
                    source_lang=source_lang[:2],
                    target_lang=target_lang
                )

            return result.text

        except deepl.DeepLException as error:
            return {"error": str(error)}
