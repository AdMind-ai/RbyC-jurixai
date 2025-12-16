
# mcp-s3-server

## Overview
`mcp-s3-server` é um servidor FastMCP que permite listar e ler documentos armazenados em um bucket AWS S3, extraindo automaticamente o texto de arquivos em diversos formatos, inclusive PDFs escaneados (via OCR), Word, Excel, texto e outros.

## Funcionalidades
- Listagem de arquivos em um bucket S3.
- Extração de texto de arquivos `.txt`, `.md`, `.csv`, `.pdf`, `.docx`, `.doc`, `.xlsx`.
- Suporte a PDFs escaneados (OCR) em português, inglês e italiano.
- Retorno do conteúdo textual pronto para uso em IA/chatbots.

## Formatos Suportados
- **.txt, .md, .csv**: Lidos como texto UTF-8.
- **.pdf**: Tenta extrair texto nativo; se não houver, aplica OCR (Reconhecimento Óptico de Caracteres) usando Tesseract.
- **.docx**: Extração via `python-docx`.
- **.doc**: Extração via `textract` (requer dependências de sistema, já incluídas no Dockerfile).
- **.xlsx**: Extração de todas as planilhas como texto tabular.
- Outros formatos: Retornados em base64.

## Requisitos do Sistema
- Python 3.10+
- Dependências Python: ver `requirements.txt` (inclui textract, pypdf, pandas, etc.)
- Dependências de sistema (instaladas via Dockerfile):
  - tesseract-ocr, tesseract-ocr-por, tesseract-ocr-eng, tesseract-ocr-ita
  - antiword, unrtf, poppler-utils, ffmpeg, sox, swig, etc.

## Estrutura do Projeto
```
mcp-s3-server
├── server
│   └── server.py        # Implementação do servidor FastMCP
├── requirements.txt     # Dependências Python
├── Dockerfile           # Build da imagem Docker
└── README.md            # Documentação
```

## Setup Local
1. **Clone o repositório:**
   ```bash
   git clone <repository-url>
   cd mcp-s3-server
   ```
2. **(Opcional) Crie um ambiente virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```
3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure as credenciais AWS:**
   Defina as variáveis de ambiente:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION`
   - `S3_BUCKET` (opcional, padrão: 'bcand')
5. **(Linux) Instale dependências de sistema:**
   Veja o Dockerfile para a lista completa de pacotes necessários.

## Uso Local
Execute o servidor:
```bash
python mcp_s3_server/server.py
```
O servidor estará disponível em `http://localhost:8000/mcp`.

## Uso com Docker
1. **Build da imagem:**
   ```bash
   docker build -t mcp-s3-server .
   ```
2. **Execute o container:**
   ```bash
   docker run -p 8000:8000 \
     -e AWS_ACCESS_KEY_ID=<sua_key> \
     -e AWS_SECRET_ACCESS_KEY=<seu_secret> \
     -e AWS_REGION=<sua_regiao> \
     -e S3_BUCKET=<seu_bucket> \
     mcp-s3-server
   ```
O servidor estará disponível em `http://localhost:8000/mcp`.

## Como funciona a extração de texto
- O método `get_document` detecta a extensão do arquivo e aplica a extração adequada:
  - `.txt`, `.md`, `.csv`: leitura direta como texto.
  - `.pdf`: tenta extrair texto nativo; se não houver, converte páginas em imagens e aplica OCR (Tesseract) nos idiomas português, inglês e italiano.
  - `.docx`: extração via python-docx.
  - `.doc`: extração via textract (usa antiword).
  - `.xlsx`: lê todas as planilhas e retorna como texto tabular.
  - Outros: retorna base64.
- Logs detalhados de erro são enviados para o stdout/stderr e aparecem no painel de logs do Render.

## Troubleshooting
- **404 Not Found**: O arquivo não existe no bucket S3 ou o nome está incorreto.
- **.doc não extrai texto**: Verifique se as dependências de sistema estão instaladas (antiword, etc). Veja o Dockerfile.
- **PDF escaneado não retorna texto**: Confirme que tesseract-ocr e os idiomas necessários estão instalados.
- **Logs não aparecem**: O sistema usa o módulo logging para garantir que logs de erro e debug apareçam no Render.

## Ferramentas Disponíveis (MCP)
- `list_documents`: Lista arquivos no bucket S3.
- `get_document`: Retorna o conteúdo textual extraído de um arquivo do S3.

## License
MIT License.