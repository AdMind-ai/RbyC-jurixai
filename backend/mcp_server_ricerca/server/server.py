# Configuração básica de logging
from fastmcp import FastMCP
import boto3
import os
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

try:
    import textract
except ImportError:
    textract = None
def extract_text_from_doc(filepath: str) -> str:
    if not textract:
        return "[ERROR] textract não instalado."
    try:
        text = textract.process(filepath)
        return text.decode("utf-8", errors="replace")
    except Exception as e:
        logging.error(f"[DOC ERROR] Falha ao extrair texto do .doc: {e}", exc_info=True)
        return f"[ERRO] Não foi possível extrair texto do arquivo .doc: {e}"


BUCKET_NAME = os.getenv('S3_BUCKET', 'rbyc')

# Configure boto3 client (usa variáveis de ambiente AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION)
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

# ---------------------------
#  Nome + Instructions (IMPORTANTE)
# ---------------------------
INSTRUCTIONS = """
Servidor MCP para listagem e leitura de documentos armazenados no S3.
Ferramentas disponíveis:
- list_documents: lista arquivos no bucket
- get_document: retorna o conteúdo de um arquivo
"""

mcp = FastMCP(
    name=BUCKET_NAME,
    instructions=INSTRUCTIONS
)

# ---------------------------
#  Ferramentas MCP
# ---------------------------
@mcp.tool()
async def list_documents() -> list:
    """Lista os arquivos disponíveis no bucket S3."""
    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    return [obj["Key"] for obj in response.get("Contents", [])]



# --- dependências para extração de texto ---

import base64
import tempfile
try:
    import pypdf
except ImportError:
    pypdf = None
try:
    import docx
except ImportError:
    docx = None
try:
    import pandas as pd
except ImportError:
    pd = None
try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None
try:
    import pytesseract
except ImportError:
    pytesseract = None

def extract_text_from_pdf(filepath: str) -> str:
    if not pypdf:
        return "[ERROR] pypdf não instalado."
    try:
        reader = pypdf.PdfReader(filepath)
        texts = []
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                texts.append(page_text)
            except Exception as e:
                logging.error(f"[PDF ERROR] Falha ao extrair texto da página {i+1}: {e}", exc_info=True)
                texts.append(f"[ERRO ao extrair texto da página {i+1}]")
        result = "\n".join(texts)
        if not result.strip() and convert_from_path and pytesseract:
            # Tenta OCR
            try:
                images = convert_from_path(filepath)
                ocr_texts = []
                for idx, img in enumerate(images):
                    ocr_text = pytesseract.image_to_string(img, lang='por+eng+ita')
                    ocr_texts.append(ocr_text)
                ocr_result = "\n".join(ocr_texts)
                if ocr_result.strip():
                    return ocr_result
                else:
                    return "[ERRO] Não foi possível extrair texto deste PDF nem via OCR."
            except Exception as ocr_e:
                logging.error(f"[PDF OCR ERROR] {ocr_e}", exc_info=True)
                return f"[ERRO] Não foi possível extrair texto nem via OCR: {ocr_e}"
        elif not result.strip():
            return "[ERRO] Não foi possível extrair texto deste PDF. Pode estar protegido, corrompido ou em formato não suportado."
        return result
    except Exception as e:
        logging.error(f"[PDF ERROR] Falha geral ao abrir PDF: {e}", exc_info=True)
        return f"[ERRO] Não foi possível abrir ou ler o PDF: {e}"

def extract_text_from_docx(filepath: str) -> str:
    if not docx:
        return "[ERROR] python-docx não instalado."
    doc = docx.Document(filepath)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text_from_xlsx(filepath: str) -> str:
    if not pd:
        return "[ERROR] pandas não instalado."
    dfs = pd.read_excel(filepath, sheet_name=None)
    text = []
    for sheet, df in dfs.items():
        text.append(f"--- {sheet} ---\n" + df.astype(str).to_string(index=False))
    return "\n\n".join(text)


@mcp.tool()
async def get_document(filename: str) -> str:
    """Baixa o arquivo do S3 para um arquivo temporário, extrai texto conforme o tipo e apaga o arquivo ao final."""
    ext = os.path.splitext(filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=True, suffix=ext) as tmp:
        s3.download_fileobj(BUCKET_NAME, filename, tmp)
        tmp.flush()
        try:
            if ext in [".txt", ".md", ".csv"]:
                tmp.seek(0)
                return tmp.read().decode("utf-8", errors="replace")
            elif ext == ".pdf":
                return extract_text_from_pdf(tmp.name)
            elif ext == ".docx":
                return extract_text_from_docx(tmp.name)
            elif ext == ".doc":
                return extract_text_from_doc(tmp.name)
            elif ext == ".xlsx":
                return extract_text_from_xlsx(tmp.name)
            else:
                tmp.seek(0)
                return base64.b64encode(tmp.read()).decode("utf-8")
        except Exception as e:
            logging.error(f"[ERROR] Falha ao processar arquivo {filename}: {e}", exc_info=True)
            return f"[ERRO] Não foi possível processar o arquivo: {e}"


# ---------------------------
#  Inicialização do servidor
# ---------------------------
if __name__ == "__main__":
    logging.info("🚀 Servidor MCP iniciado em http://localhost:7000/mcp")
    mcp.run(
        host="0.0.0.0",
        port=7000,
        transport="sse"
    )
