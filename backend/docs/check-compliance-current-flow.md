# Check Compliance - fluxo atual

Este documento registra o funcionamento atual da nova funcionalidade de Check Compliance. Ele serve como referencia de manutencao para entender o contexto de negocio, arquitetura tecnica, integracao com Vera/Hermes, uso de S3, persistencia de conversas e pontos importantes para evolucao futura.

## Visao geral

O Check Compliance foi reformulado para deixar de ser um fluxo estatico de analise e passar a funcionar como uma chat com o agente Vera/Hermes.

O usuario pode:

- conversar com a Vera em uma interface de chat;
- anexar documentos na conversa;
- salvar e reabrir conversas;
- continuar uma conversa salva preservando a mesma sessao da Vera;
- gerenciar a base normativa usada pela Vera por meio da tela de documentos.

A Vera nao recebe arquivos binarios diretamente pela API. Quando o usuario anexa documentos, o backend salva os arquivos no S3 e envia para a Vera apenas referencias textuais contendo bucket, chave S3 e metadados do arquivo.

## Componentes principais

### Frontend

- `frontend/src/pages/CheckComplianceChat.tsx`
  - Tela da chat.
  - Envia mensagens para Vera via backend.
  - Faz upload de anexos antes de enviar a mensagem.
  - Renderiza respostas em Markdown.
  - Lista, salva, reabre e exclui conversas salvas.
  - Usa `vera_session_id` para continuar a mesma sessao da Vera.

- `frontend/src/pages/CheckComplianceDocuments.tsx`
  - Tela de gerenciamento dos documentos da base normativa.
  - Lista documentos do bucket de conhecimento.
  - Faz upload de documentos para `documents/`.
  - Permite download por URL assinada.
  - Permite exclusao definitiva mediante confirmacao.
  - Permite visualizar e restaurar documentos no `trash/`.

- `frontend/src/services/checkComplianceChatService.ts`
  - Chama a API de chat.
  - Faz streaming da resposta SSE.
  - Faz upload dos anexos da conversa.

- `frontend/src/services/checkComplianceConversationService.ts`
  - Service dedicado para persistencia das conversas de Check Compliance.
  - Nao usa o service generico de chats (`chatSessionService`).

- `frontend/src/services/checkComplianceDocumentsService.ts`
  - Service da tela de gerenciamento documental.

### Backend

- `backend/core/views/check_compliance_chat_view.py`
  - Endpoint da chat Vera.
  - Endpoint de upload de anexos.
  - Endpoints de conversas salvas de Check Compliance.
  - Monta o payload textual enviado para Vera quando existem documentos.

- `backend/core/views/check_compliance_documents_view.py`
  - Endpoints de listagem, upload, download, exclusao e restauracao de documentos da base normativa.

- `backend/core/services/vera_compliance_service.py`
  - Cliente da Vera API.
  - Usa API compativel com OpenAI SDK apontando para `VERA_API_BASE_URL`.
  - Suporta chamada normal e streaming.

- `backend/core/models/check_compliance_chat_models.py`
  - Models dedicados para Check Compliance:
    - `CheckComplianceConversation`
    - `CheckComplianceMessage`
    - `CheckComplianceAttachment`

## Buckets S3

### Bucket da base normativa

Nome atual:

```text
rbyc-compliance-knowledge-prod
```

Uso:

- armazenar documentos regulatorios/normativos;
- ser consultado pela Vera como base de conhecimento;
- ser gerenciado pela tela de documentos do app.

Prefixos relevantes:

```text
documents/
trash/documents/
```

Observacoes:

- o backend usa `COMPLIANCE_DOCUMENTS_BUCKET_NAME`;
- o client S3 desse fluxo usa `COMPLIANCE_DOCUMENTS_BUCKET_REGION`;
- atualmente o bucket esta em `eu-central-1`;
- a Vera deve ter permissao somente leitura neste bucket.

### Bucket da chat

Nome atual:

```text
rbyc-compliance-chat
```

Uso:

- armazenar documentos anexados por usuarios na chat;
- permitir que Vera leia esses documentos por referencia S3.

Prefixo atual de upload:

```text
documents/chat-uploads/
```

Formato da chave gerada pelo backend:

```text
documents/chat-uploads/{user_id}/{session_id}/{uuid}-{filename}
```

Observacoes:

- o backend usa `COMPLIANCE_CHAT_BUCKET_NAME`;
- o prefixo pode ser alterado por `COMPLIANCE_CHAT_UPLOAD_PREFIX`;
- a Vera precisa ter permissao de leitura para este prefixo;
- caso futuramente Vera gere documentos, deve ser definido um prefixo dedicado, por exemplo `documents/generated/`, com permissao de escrita restrita.

## Variaveis de ambiente relevantes

### Vera API

```env
VERA_API_BASE_URL=https://vera-api.admind.ai/v1
VERA_API_SERVER_KEY=<secret>
VERA_API_MODEL=vera-compliance
VERA_DEFAULT_ORGANIZATION_ID=<opcional>
VERA_DEFAULT_CLIENT_ID=<opcional>
VERA_DEFAULT_MATTER_ID=<opcional>
```

### S3 base normativa

```env
COMPLIANCE_DOCUMENTS_BUCKET_NAME=rbyc-compliance-knowledge-prod
COMPLIANCE_DOCUMENTS_BUCKET_REGION=eu-central-1
```

### S3 chat

```env
COMPLIANCE_CHAT_BUCKET_NAME=rbyc-compliance-chat
COMPLIANCE_CHAT_UPLOAD_PREFIX=documents/chat-uploads/
COMPLIANCE_CHAT_MAX_UPLOAD_SIZE=209715200
```

`COMPLIANCE_CHAT_MAX_UPLOAD_SIZE=209715200` equivale a 200 MB.

### AWS

```env
AWS_ACCESS_KEY_ID=<backend-access-key>
AWS_SECRET_ACCESS_KEY=<backend-secret-key>
AWS_S3_REGION_NAME=<regiao-padrao-do-backend>
```

Atencao: `AWS_S3_REGION_NAME` e usado no fluxo de uploads da chat. O gerenciamento da base normativa usa `COMPLIANCE_DOCUMENTS_BUCKET_REGION` para evitar erro de URL assinada quando o bucket normativo estiver em regiao diferente.

## Fluxo da chat

### 1. Usuario envia mensagem sem anexos

1. Frontend chama `POST /api/check-compliance/chat/`.
2. Backend monta a `X-Hermes-Session-Key`.
3. Backend chama Vera.
4. Resposta retorna por streaming SSE.
5. Frontend renderiza o texto em Markdown.

### 2. Usuario envia mensagem com anexos

1. Usuario seleciona arquivos na chat.
2. Frontend chama `POST /api/check-compliance/chat/attachments/`.
3. Backend valida os arquivos.
4. Backend faz upload para `rbyc-compliance-chat`.
5. Backend retorna referencias S3 dos documentos.
6. Frontend chama `POST /api/check-compliance/chat/` com a mensagem e as referencias.
7. Backend transforma a mensagem em um payload JSON textual para Vera.
8. Vera usa IAM proprio para ler os documentos no S3.
9. Vera responde ao usuario.

Exemplo conceitual do conteudo enviado para Vera quando ha documentos:

```json
{
  "question": "Analizza il documento allegato",
  "documents": [
    {
      "bucket": "rbyc-compliance-chat",
      "s3_key": "documents/chat-uploads/1/session/file.pdf",
      "filename": "file.pdf",
      "content_type": "application/pdf",
      "size": 12345
    }
  ],
  "instructions": "Use the S3 document references as the source documents for this compliance analysis..."
}
```

## Sessao Vera/Hermes

A Vera usa o header:

```text
X-Hermes-Session-Key
```

Formato:

```text
vera:<organization_id>:<client_id>:<matter_id>:<user_id>
```

No fluxo atual, o frontend gera um `sessionId` para a conversa. O backend usa esse valor para montar o `matter_id` quando nenhum `matter_id` explicito e enviado:

```text
check-compliance-{session_id}
```

Isso permite isolar e retomar contexto entre mensagens.

Quando uma conversa e salva, o `sessionId` e persistido como:

```text
CheckComplianceConversation.vera_session_id
```

Ao reabrir uma conversa salva, o frontend restaura esse `vera_session_id` e passa novamente como `session_id` nas proximas chamadas. Assim, a Vera continua a mesma sessao.

## Persistencia de conversas

A persistencia da Check Compliance foi segregada da chat geral.

Models:

- `CheckComplianceConversation`
  - conversa salva;
  - guarda `vera_session_id`;
  - pertence ao usuario;
  - possui titulo e timestamps.

- `CheckComplianceMessage`
  - mensagens da conversa;
  - role `user` ou `assistant`;
  - conteudo textual;
  - `provider_payload` para metadados da mensagem, como arquivos exibidos e referencias S3.

- `CheckComplianceAttachment`
  - anexos vinculados a conversa e opcionalmente a mensagem;
  - guarda bucket, `s3_key`, filename, content type, tamanho e version id.

Endpoints:

```text
GET    /api/check-compliance/chat/conversations/
POST   /api/check-compliance/chat/conversations/
GET    /api/check-compliance/chat/conversations/<conversation_id>/
DELETE /api/check-compliance/chat/conversations/<conversation_id>/
```

O frontend atualiza automaticamente uma conversa salva depois que uma nova resposta da Vera chega.

## Gerenciamento de documentos normativos

A tela de documentos gerencia o bucket normativo.

Endpoints:

```text
GET  /api/check-compliance/documents/
POST /api/check-compliance/documents/upload/
POST /api/check-compliance/documents/download/
POST /api/check-compliance/documents/delete/
POST /api/check-compliance/documents/permanent-delete/
POST /api/check-compliance/documents/restore/
```

Comportamento importante:

- listagem padrao considera `documents/`;
- lixeira usa `trash/documents/`;
- upload precisa estar dentro de `documents/`;
- download retorna URL assinada com validade de 300 segundos;
- exclusao definitiva remove o objeto do S3;
- mover para trash copia o objeto para `trash/` e remove o original.

## Renderizacao da resposta

A resposta da Vera pode vir com Markdown.

O frontend renderiza:

- quebras de linha;
- negrito;
- italico;
- listas;
- links;
- tabelas simples;
- blocos de codigo;
- emojis.

Durante o streaming, enquanto a resposta ainda esta vazia, a interface mostra `Scrivendo` com indicador animado.

## Permissoes AWS esperadas

### Backend

O backend precisa:

- fazer upload no bucket da chat;
- listar, baixar, mover/restaurar e excluir documentos no bucket normativo;
- gerar URLs assinadas para download.

### Vera/Hermes

A Vera deve ter acesso somente leitura aos documentos que precisa analisar:

- `s3:GetBucketLocation`;
- `s3:ListBucket`;
- `s3:GetObject`;
- `s3:GetObjectVersion`, se versionamento for usado.

Buckets/prefixos esperados:

```text
rbyc-compliance-knowledge-prod/documents/*
rbyc-compliance-chat/documents/chat-uploads/*
```

Se os objetos forem criptografados com KMS, tambem sera necessario liberar `kms:Decrypt` para o role usado pela Vera.

## Validacoes de arquivo

Extensoes aceitas na chat:

```text
.csv, .doc, .docx, .html, .json, .md, .ods, .odt, .pdf,
.ppt, .pptx, .rtf, .txt, .xls, .xlsx, .xml
```

Extensoes bloqueadas:

```text
.bat, .cmd, .com, .dll, .exe, .jar, .js, .msi, .ps1, .scr, .sh, .vbs
```

Arquivos sem extensao sao rejeitados.

## Pontos de manutencao

Ao mexer nessa funcionalidade, verificar:

1. Se o bucket correto esta configurado na `.env`.
2. Se a regiao do bucket normativo continua coerente com `COMPLIANCE_DOCUMENTS_BUCKET_REGION`.
3. Se a Vera possui permissao de leitura no bucket/prefixo usado.
4. Se o frontend esta reaproveitando o mesmo `vera_session_id` ao reabrir conversas.
5. Se novos tipos de arquivo precisam ser adicionados nas listas de extensoes.
6. Se documentos gerados pela Vera precisarao de bucket/prefixo e permissao de escrita especifica.

## Testes recomendados

Backend:

```bash
python manage.py test core
```

Frontend:

```bash
npm run build
```

Teste manual principal:

1. Abrir a chat de Check Compliance.
2. Anexar um PDF pequeno.
3. Enviar uma pergunta pedindo confirmacao de leitura do documento.
4. Confirmar que o arquivo foi salvo em `rbyc-compliance-chat/documents/chat-uploads/`.
5. Confirmar que Vera consegue ler o documento.
6. Salvar a conversa.
7. Reabrir a conversa salva.
8. Enviar uma pergunta de continuidade.
9. Confirmar que a Vera mantem contexto da sessao.

## Pontos futuros

Possiveis evolucoes:

- prefixo dedicado para documentos gerados pela Vera;
- exibicao/download de documentos gerados na resposta;
- auditoria detalhada de acessos e anexos;
- versionamento e recuperacao de anexos da chat;
- relatorios estruturados por conversa;
- associacao de conversa a cliente/matter real do app, substituindo o `matter_id` provisoriamente baseado no `sessionId`.
