# Check Compliance S3 Documents Plan

## Contexto

O fluxo atual do Check Compliance sera substituido por uma nova experiencia baseada em chat/agente. O agente Hermes sera externo e provavelmente sera plugado na tela de chat em uma etapa posterior.

Antes da integracao com o agente, a prioridade e criar uma funcionalidade para gerenciar os documentos usados como base documental no S3.

## Objetivo

Criar uma nova area de Check Compliance com duas opcoes:

- Chat
- Documentos

A tela de Chat sera criada inicialmente como placeholder, sem integracao real com Hermes.

A tela de Documentos sera funcional e permitira gerenciar arquivos do bucket S3.

## Branch

Branch criada para esta tarefa:

```bash
feature/check-compliance-s3-documents
```

## Decisoes Fechadas

- Bucket S3: `rbyc-compliance-knowledge-prod`.
- A tela deve mostrar apenas o prefixo `documents/`.
- `raw/`, `indexes/` e outros prefixos tecnicos nao serao expostos no frontend.
- Upload deve aceitar arquivos documentais comuns, nao apenas PDF.
- A aplicacao deve manter validacoes para evitar arquivos perigosos, nomes invalidos e operacoes fora dos prefixos permitidos.
- Delete nao deve apagar definitivamente na primeira versao.
- Ao remover, o arquivo deve ser movido para `trash/`.
- O frontend deve permitir visualizar a lixeira e restaurar arquivos removidos.
- O nome original enviado pelo usuario deve ser preservado sempre que possivel.
- O sistema deve sanitizar apenas o necessario para impedir path traversal, barras indevidas e caracteres problematicos.
- A regra final de permissao para remover/restaurar documentos sera definida depois.
- O fluxo antigo do Check Compliance deixara de ser exposto no frontend, mas o backend antigo pode permanecer inicialmente para reduzir risco.

## Estrutura S3 Esperada

```text
rbyc-compliance-knowledge-prod/
  documents/
    regulatory/
      banca-ditalia/
      consob/
      eur-lex/
      normattiva-gazzetta/
      esma/
      eba/
      ivass/
      assogestioni/
      fonte-da-definire/

  trash/
    documents/
      regulatory/
        banca-ditalia/
        consob/
        eur-lex/
        normattiva-gazzetta/
        esma/
        eba/
        ivass/
        assogestioni/
        fonte-da-definire/
```

## Tipos De Arquivo

O S3 aceita qualquer objeto, mas a aplicacao deve restringir arquivos perigosos.

Extensoes documentais inicialmente aceitas:

```text
pdf, doc, docx, xls, xlsx, csv, txt, md, json, html, xml, rtf, odt, ods, ppt, pptx
```

Extensoes inicialmente bloqueadas:

```text
exe, bat, cmd, sh, ps1, msi, dll, js, vbs, jar, scr, com
```

Essa lista pode ser ajustada conforme necessidade de negocio.

## Backend

Criar endpoints para gerenciamento dos documentos no S3:

- Listar documentos em `documents/`.
- Gerar upload seguro para um prefixo permitido.
- Mover documento de `documents/...` para `trash/documents/...`.
- Listar documentos da lixeira.
- Restaurar documento de `trash/documents/...` para `documents/...`.

Cuidados obrigatorios:

- Nunca permitir chaves fora de `documents/` e `trash/documents/`.
- Validar e sanitizar nomes de arquivo.
- Bloquear path traversal, por exemplo `../`.
- Bloquear upload em prefixos arbitrarios.
- Preparar pontos para validacao futura de permissao.
- Tratar erros de AWS de forma clara para o frontend.

## Frontend

Alterar a navegacao para:

```text
Check Compliance
  - Chat
  - Documentos
```

### Chat

Criar tela placeholder.

Estado inicial:

- Sem integracao Hermes.
- Texto simples indicando que a integracao esta em definicao.
- Rota pronta para receber a implementacao futura.

### Documentos

Criar tela funcional com:

- Listagem de arquivos em `documents/`.
- Organizacao por fonte/pasta.
- Busca/filtro por nome.
- Upload escolhendo a pasta/fonte.
- Remocao com confirmacao.
- Aba ou filtro para lixeira.
- Restauracao de arquivos removidos.
- Estados de loading, vazio, erro, upload em progresso e remocao em progresso.

## Ordem De Implementacao

1. Mapear frontend atual: sidebar, rotas e pagina atual do Check Compliance.
2. Mapear backend atual: URLs, views e padroes de autenticacao/permissao.
3. Criar submenu `Check Compliance`.
4. Criar tela placeholder `Chat`.
5. Criar backend minimo para listar `documents/`.
6. Criar tela `Documentos` com listagem.
7. Implementar upload seguro.
8. Implementar remocao movendo para `trash/`.
9. Implementar listagem da lixeira.
10. Implementar restauracao.
11. Testar fluxo completo.
12. Avaliar depois a remocao definitiva do fluxo antigo.

## Decisoes Pendentes

- Quem podera remover documentos.
- Quem podera restaurar documentos.
- Limite maximo de tamanho por arquivo.
- Se o upload sera por presigned URL ou se o backend recebera o arquivo e enviara ao S3.
- Se sera necessario versionamento ou auditoria formal das acoes.
- Como o agente Hermes sera integrado na tela de Chat.

## Recomendacao Tecnica Inicial

Para upload, a recomendacao inicial e usar presigned URL, pois evita trafegar arquivos grandes pelo backend.

Caso o projeto atual nao tenha padrao pronto para isso, podemos iniciar com upload via backend para simplificar a primeira entrega e depois evoluir para presigned URL.

## Observacoes

Os 133 documentos iniciais extraidos dos Excels do cliente ja foram buscados, validados manualmente e enviados ao S3 em `documents/regulatory/`.

O prefixo `documents/regulatory/ivass/` ficou vazio porque nenhuma referencia extraida dos Excels apontou IVASS como fonte provavel.

O prefixo `documents/editorial/` nao sera usado inicialmente, pois o escopo atual da base documental e regulatorio/oficial.
