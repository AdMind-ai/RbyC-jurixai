import base64
import mimetypes

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models.segreteria_societaria.company_model import Company
from core.utils.openai_client import client, logger


class OpenAIDocumentGeneratorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        payload = request.data or {}
        company_id = payload.get("company_id")
        doc_type = (payload.get("doc_type") or "").strip()
        details = (payload.get("details") or "").strip()
        context_files = payload.get("context_files") or []

        if not doc_type and not details:
            return Response(
                {"detail": "Se non selezioni un tipo di documento, devi fornire delle istruzioni nei dettagli."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        company = None
        if company_id:
            try:
                company = (
                    Company.objects.prefetch_related("officers", "shareholders")
                    .get(pk=company_id)
                )
            except Company.DoesNotExist:
                return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        prompt = self._build_prompt(doc_type=doc_type, company=company, details=details, has_context=bool(context_files))
        user_content = [{"type": "input_text", "text": prompt}]

        try:
            for file_payload in context_files:
                prepared_part = self._build_file_part(file_payload)
                if prepared_part:
                    user_content.append(prepared_part)

            letterhead_part = self._build_company_letterhead_part(company)
            if letterhead_part:
                user_content.append(letterhead_part)

            response = client.responses.create(
                model="gpt-5.2",
                input=[
                    {
                        "role": "user",
                        "content": user_content,
                    }
                ],
                reasoning={"effort": "medium"},
                store=False,
                timeout=900,
            )
        except Exception as exc:
            logger.exception("Error generating OpenAI document draft: %s", exc)
            return Response(
                {"detail": "Errore nella generazione del documento con OpenAI."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        generated_text = (response.output_text or "").strip()
        if not generated_text:
            generated_text = "Nessun testo generato."

        return Response({"generated_content": generated_text}, status=status.HTTP_200_OK)

    def _build_prompt(self, doc_type: str, company: Company | None, details: str, has_context: bool) -> str:
        company_info = (
            "DATI SOCIETARI: Non specificati. Usa placeholder [NOME SOCIETA] o segui le istruzioni fornite."
        )

        if company:
            officers = ", ".join(
                f"{officer.name} ({officer.role})" for officer in company.officers.all()
            ) or "Non specificati"
            shareholders = ", ".join(
                f"{shareholder.name} ({shareholder.quota_percentage}%)"
                for shareholder in company.shareholders.all()
            ) or "Non specificati"
            letterhead_info = ""
            if company.letterhead_info:
                letterhead_info = f"\nTESTO CARTA INTESTATA:\n{company.letterhead_info}"
            letterhead_note = ""
            if company.letterhead_file:
                letterhead_note = (
                    "\nNOTA: Ho allegato il file della carta intestata della societa. "
                    "Usa lo stile o le informazioni visive se pertinenti per formattare il documento."
                )
            company_info = f"""
DATI SOCIETARI:
Nome: {company.name}
Tipo: {company.company_type}
Sede: {company.address or "Non specificata"}
P.IVA: {company.vat_number or "Non specificata"}
Capitale Sociale: EUR {company.capital or 0}
Amministratori: {officers}
Soci: {shareholders}
{letterhead_info}
{letterhead_note}
""".strip()

        context_note = ""
        if has_context:
            context_note = (
                "NOTA: Ho allegato dei file di contesto (contratti, bozze). "
                "Usa il contenuto di questi file per redigere il documento richiesto."
            )

        return f"""
Agisci come un esperto avvocato societario italiano.
Devi redigere un documento {f'del tipo: "{doc_type}"' if doc_type else "basato sulle istruzioni fornite"}.

{company_info}

ISTRUZIONI SPECIFICHE / DETTAGLI:
{details}

{context_note}

Genera il documento usando formattazione Markdown (grassetto, elenchi puntati, titoli) per renderlo professionale e leggibile.
Usa un linguaggio legale formale e preciso.
Se i dati societari non sono presenti, usa dei placeholder chiari tipo [INSERIRE ...].
""".strip()

    def _build_file_part(self, file_payload: dict) -> dict | None:
        if not isinstance(file_payload, dict):
            return None

        mime_type = (file_payload.get("mimeType") or file_payload.get("type") or "application/octet-stream").strip()
        filename = (file_payload.get("name") or file_payload.get("filename") or "attachment").strip()
        data = file_payload.get("data") or ""
        if not data:
            return None

        if self._is_textual_file(mime_type, filename):
            decoded_text = self._decode_base64_text(data)
            if decoded_text:
                return {
                    "type": "input_text",
                    "text": f"Contenuto del file di contesto '{filename}':\n{decoded_text}",
                }

        data_url = data if isinstance(data, str) and data.startswith("data:") else f"data:{mime_type};base64,{data}"

        if mime_type.startswith("image/"):
            return {
                "type": "input_image",
                "image_url": data_url,
            }

        return {
            "type": "input_file",
            "filename": filename,
            "file_data": data_url,
        }

    def _is_textual_file(self, mime_type: str, filename: str) -> bool:
        lowered_name = filename.lower()
        return mime_type.startswith("text/") or lowered_name.endswith((".txt", ".md"))

    def _decode_base64_text(self, data: str) -> str:
        base64_payload = data
        if data.startswith("data:") and "," in data:
            base64_payload = data.split(",", 1)[1]

        try:
            decoded_bytes = base64.b64decode(base64_payload)
        except Exception:
            return ""

        for encoding in ("utf-8", "latin-1"):
            try:
                return decoded_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue

        return ""

    def _build_company_letterhead_part(self, company: Company | None) -> dict | None:
        if not company or not company.letterhead_file:
            return None

        try:
            company.letterhead_file.open("rb")
            raw_bytes = company.letterhead_file.read()
        except Exception as exc:
            logger.warning("Unable to read company letterhead file for OpenAI document generation: %s", exc)
            return None
        finally:
            try:
                company.letterhead_file.close()
            except Exception:
                pass

        if not raw_bytes:
            return None

        mime_type, _ = mimetypes.guess_type(company.letterhead_file.name)
        mime_type = mime_type or "application/octet-stream"
        base64_payload = base64.b64encode(raw_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{base64_payload}"
        filename = company.letterhead_file.name.split("/")[-1] or "letterhead"

        if mime_type.startswith("image/"):
            return {
                "type": "input_image",
                "image_url": data_url,
            }

        return {
            "type": "input_file",
            "filename": filename,
            "file_data": data_url,
        }
