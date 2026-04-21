# Document Search Performance README

## Objetivo

Este documento registra a arquitetura atual da busca documental RbyC, as melhorias de performance aplicadas e os pontos de manutencao para evolucoes futuras.

O objetivo principal da evolucao foi reduzir a latencia das respostas da API de pesquisa documental, evitando leituras completas de documentos e OCR sempre que possivel.

## Estado validado

A versao atual foi validada em producao como base estavel.

Resultados observados:

- Antes das otimizacoes, algumas consultas ficavam na faixa de 50s a mais de 1min.
- Depois das otimizacoes, as chamadas passaram a ficar em torno de 20s a 30s.
- O MCP passou a usar indice e previews antes de recorrer a leitura completa de documentos.
- O uso de OCR ficou restrito a casos explicitamente necessarios.
- A infraestrutura foi ajustada para suportar melhor chamadas longas com Gunicorn em modo threaded.

## Componentes principais

### API Django

Responsavel por:

- receber chamadas da API de integracao;
- autenticar a chave de integracao;
- chamar a OpenAI Responses API com ferramentas MCP;
- gerar URLs presignadas dos documentos retornados;
- expor endpoint interno para consulta do indice documental.

Arquivos relevantes:

- `backend/integrations/views/ricerca_documentale.py`
- `backend/integrations/views/document_index.py`
- `backend/integrations/authentication.py`
- `backend/integrations/models/__init__.py`

### MCP Server

Responsavel por expor ferramentas para a OpenAI consultar documentos.

Ferramentas atuais:

- `search_documents`: busca documentos relevantes usando indice e preview.
- `list_documents`: lista documentos por metadados e filtros.
- `get_document`: consulta preview ou conteudo do documento quando necessario.

Arquivo principal:

- `backend/mcp_server_ricerca/server/server.py`

### Indice documental

O indice guarda metadados dos documentos em banco.

Campos principais:

- cliente;
- bucket;
- object key;
- nome do arquivo;
- extensao;
- tamanho;
- data de modificacao;
- ano;
- tipo documental;
- preview textual.

Modelo principal:

- `DocumentIndex`

### Previews

Os previews sao trechos pre-processados dos documentos usados para responder perguntas sem abrir o arquivo completo.

Isso reduz:

- download de arquivo do S3;
- parse de PDF/DOCX/PPTX;
- uso de OCR;
- tempo total de resposta.

Servico principal:

- `backend/integrations/services/document_preview.py`

## Fluxo atual da pesquisa documental

1. O usuario chama a API de pesquisa documental.
2. O backend valida a chave de integracao.
3. O backend chama a OpenAI com acesso ao MCP.
4. A OpenAI usa preferencialmente `search_documents`.
5. O MCP consulta o endpoint interno do indice no backend.
6. O indice retorna metadados e previews.
7. Se preview/metadados forem suficientes, a resposta e montada sem abrir documentos completos.
8. Se for necessario mais detalhe, a OpenAI pode usar `get_document`.
9. O backend gera URLs presignadas apenas para as keys retornadas.

## Endpoint interno do indice

Endpoint:

```text
/api/integrations/v1/internal/document-index/
```

Autenticacao:

```text
X-Internal-API-Key: <DOCUMENT_INDEX_API_KEY>
```

Filtros suportados:

- `customer_code`
- `query`
- `year`
- `document_type`
- `extension`
- `filename_contains`
- `path_contains`
- `limit`
- `sort_by`
- `sort_order`

Exemplo:

```bash
curl "https://rbyc.admind.ai/api/integrations/v1/internal/document-index/?customer_code=default&query=CDA&year=2024&limit=50" \
  -H "X-Internal-API-Key: <DOCUMENT_INDEX_API_KEY>"
```

## Comandos de manutencao

### Sincronizar indice documental

```bash
python manage.py sync_document_index --customer-code default
```

Em Docker:

```bash
docker exec rbyc-web python manage.py sync_document_index --customer-code default
```

### Gerar previews manualmente

```bash
python manage.py build_document_previews --customer-code default --limit 100
```

Em Docker:

```bash
docker exec rbyc-web python manage.py build_document_previews --customer-code default --limit 100
```

### Forcar regeneracao de previews

Use com cuidado, pois pode consumir mais CPU e tempo.

```bash
python manage.py build_document_previews --customer-code default --limit 100 --force
```

## Celery Beat

O ambiente atual usa Celery Beat para manter indice e previews atualizados automaticamente.

Tarefas agendadas:

- `integrations.tasks.sync_all_document_indexes_task`
- `integrations.tasks.build_missing_document_previews_task`

Variaveis de controle:

```env
DOCUMENT_INDEX_SYNC_MINUTES=15
DOCUMENT_PREVIEW_SYNC_MINUTES=10
DOCUMENT_PREVIEW_SYNC_LIMIT=100
DOCUMENT_PREVIEW_SYNC_CUSTOMER_CODE=default
```

## Variaveis de ambiente importantes

### Backend

```env
MCP_SERVER_URL=<url-do-mcp>
DOCUMENT_INDEX_API_URL=<url-interna-ou-publica-do-endpoint-de-indice>
DOCUMENT_INDEX_API_KEY=<chave-interna>
DOCUMENT_INDEX_CUSTOMER_CODE=default
INTEGRATION_API_KEY=<chave-global-atual>
DB_CONN_MAX_AGE=60
```

### MCP

```env
DOCUMENT_INDEX_API_URL=<url-do-endpoint-de-indice>
DOCUMENT_INDEX_API_KEY=<chave-interna>
MCP_CUSTOMER_CODE=default
DOCUMENT_INDEX_TIMEOUT_SECONDS=20
S3_BUCKET=rbyc
```

### Gunicorn

Configuracao validada apos upgrade de instancia:

```env
WEB_CONCURRENCY=3
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=600
```

Com essa configuracao, o container web pode atender cerca de 12 requisicoes concorrentes, considerando 3 workers com 4 threads cada.

### Banco e Celery

Configuracao recomendada para reduzir risco de excesso de conexoes no Postgres:

```env
DB_CONN_MAX_AGE=60
CELERY_WORKER_CONCURRENCY=2
```

O Django usa `CONN_MAX_AGE` para reaproveitar conexoes por um periodo curto, com `CONN_HEALTH_CHECKS` ativo para validar conexoes antes do uso.

O Celery worker deve manter concorrencia explicita e conservadora na instancia atual. Para 2 vCPUs, `CELERY_WORKER_CONCURRENCY=2` e um ponto de partida seguro.

## Infra atual

Servicos Docker:

- `rbyc-web`
- `rbyc-worker`
- `rbyc-beat`
- `rbyc-redis`

Comandos uteis:

```bash
docker ps
docker logs rbyc-web --since 5m
docker logs rbyc-worker --since 5m
docker logs rbyc-beat --since 5m
```

Recriar web apos alterar `.env`:

```bash
docker compose -f infra/docker-compose.yml up -d --force-recreate web
```

## Logs esperados

Busca usando indice:

```text
[mcp_ricerca] document_index_response status=200
```

Busca direta validada:

```text
[mcp_ricerca] search_documents completed
```

Uso de preview sem abrir arquivo completo:

```text
[mcp_ricerca] get_document completed source=preview
```

Conclusao de request no backend:

```text
[ricerca_documentale][request_id] request_completed total_duration_ms=...
```

## Pontos de atencao

### Requisicoes longas

A rota de pesquisa documental ainda e sincrona. Enquanto a OpenAI responde, uma thread do Gunicorn fica ocupada.

Com respostas entre 20s e 30s, o sistema esta adequado para uso moderado, mas deve ser monitorado em cenarios com muitos usuarios simultaneos.

### OCR

OCR deve continuar sendo ultima alternativa.

O prompt da OpenAI deve evitar OCR para:

- listagens;
- documentos recentes;
- panoramas;
- perguntas exploratorias.

### PDF protegido ou criptografado

Alguns PDFs podem falhar na geracao de preview por dependerem de algoritmos AES nao suportados sem dependencia adicional.

Erro observado:

```text
PyCryptodome is required for AES algorithm
```

Isso nao bloqueia a arquitetura. Se esse caso se tornar frequente, avaliar adicionar `pycryptodome`.

## Prompt OpenAI

O prompt deve orientar:

- usar `search_documents` primeiro para perguntas amplas/tematicas;
- nao chamar `list_documents` depois de `search_documents` apenas para confirmar;
- usar `get_document` somente quando preview/metadados nao forem suficientes;
- nao usar OCR salvo necessidade real;
- responder sempre em JSON com `response` e `keys`.

## Melhorias futuras

### Performance

- Otimizar `search_documents` para parar na primeira busca quando ja houver resultados suficientes.
- Reduzir variacoes internas da query quando a primeira chamada ao indice retorna bons resultados.
- Adicionar metricas separadas para tempo de OpenAI, MCP, indice, presign e banco.
- Avaliar streaming ou job assincrono para melhorar UX de chat.

### Multi-client por API key

Proxima evolucao planejada:

1. Identificar o cliente pela API key recebida na integracao.
2. Resolver automaticamente `customer_code`.
3. Resolver automaticamente o bucket correto.
4. Fazer a busca documental restrita ao cliente autenticado.
5. Remover dependencia operacional de um `MCP_CUSTOMER_CODE` global.

### Escala

Para mais usuarios simultaneos:

- monitorar CPU, RAM, latencia p95/p99 e erros;
- ajustar `WEB_CONCURRENCY` e `GUNICORN_THREADS` gradualmente;
- considerar instancia maior;
- considerar mais de um container web atras de load balancer;
- avaliar pool de conexoes com Postgres.

## Status

Status atual: versao validada como base de performance.

Faixa observada em producao: aproximadamente 20s a 30s por chamada de pesquisa documental.
