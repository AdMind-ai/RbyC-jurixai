# Auditoria temporaria pos-Replit

Documento temporario para registrar o que foi ajustado depois das alteracoes feitas no Replit e o que ainda sera revisado manualmente.

Data de inicio: 2026-07-17
Branch atual no momento do registro: develop

## Contexto

Depois de trazer alteracoes feitas no Replit, foi feita uma primeira revisao local do projeto para entender o estado do Git, validar build e remover residuos que nao deveriam permanecer no repositorio.

O objetivo deste documento e manter uma trilha simples de auditoria para as proximas revisoes funcionais, evitando perda de contexto entre ajustes.

## Ajustes ja realizados

Commit criado:

```txt
fe4004c chore: clean replit artifacts and stabilize chat assistant
```

Incluido nesse commit:

- Remocao dos arquivos auxiliares vindos do Replit:
  - `.replit`
  - `artifacts/mockup-sandbox/`
  - `attached_assets/`
- Ajuste da porta local do Vite para `5173`.
- Correcao do build do frontend apos as alteracoes do Replit.
- Remocao do Perplexity da tela `Chat Assistant`.
- Manutencao da `Chat Assistant` apenas no fluxo GPT/Terra.
- Ajuste do modelo padrao do backend da chat para `gpt-5.6-terra`.
- Limpeza de imports, variaveis e props nao utilizados que quebravam o TypeScript.
- Correcao pontual de texto com encoding incorreto em tela de consumo.
- Ajuste em `Newsletter` para iniciar nova sessao com novo UUID, evitando `sessionId` nulo em estado tipado como string.

Validacao realizada:

```txt
npm run build
```

Resultado:

```txt
Build concluido com sucesso.
```

Observacoes do build:

- Permanecem apenas avisos nao bloqueantes de bundle grande, browserslist desatualizado e `pdfjs-dist`.
- Esses avisos nao impediram o build e podem ser tratados em uma etapa posterior de otimizacao.

## Funcionalidades a revisar

As funcionalidades serao revisadas uma por uma, nesta ordem inicial:

1. Ricerca documentale
2. Check Compliance
3. Chat Assistant
4. Newsletter
5. Consumo AI

## Plano de revisao por funcionalidade

Para cada funcionalidade, registrar:

- Estado atual percebido.
- Fluxo principal esperado.
- Pontos quebrados ou inconsistentes.
- Ajustes aplicados.
- Validacoes executadas.
- Pendencias restantes.

## Registro das revisoes

### 1. Ricerca documentale

Status: fechado nesta etapa.

Notas:

- A revisar fluxo de tela, envio de mensagens, historico/sessoes, salvamento e exclusao.
- Confirmar se os ajustes feitos pelo Replit nao quebraram comportamento existente.

Ajustes aplicados:

- Recolocada a acao de exclusao de pesquisa salva na interface.
- O comportamento segue o padrao da `Chat Assistant`: ao selecionar uma pesquisa salva, aparece um botao `X` ao lado do seletor.
- O botao abre o modal de confirmacao de exclusao que ja existia no fluxo.

Validacao:

```txt
npm run build
```

Resultado: build concluido com sucesso.

### 2. Check Compliance

Status: em revisao.

Notas:

- A revisar chat com Vera, gerenciamento de documentos, logs e fluxo S3.
- Confirmar se o novo fluxo assincromo/runs e o historico salvo continuam funcionando corretamente.

Ajustes aplicados:

- Corrigida a persistencia dos blocos de resposta da chat.
- Durante o streaming, os blocos gerados por pausa agora tambem sao mantidos em uma referencia local.
- Ao salvar/atualizar automaticamente a conversa, os `response_blocks` finais sao enviados junto com a mensagem do assistente.
- Isso evita que uma conversa recarregada volte a mostrar a resposta inteira em um unico bloco.
- Ajustada a mensagem inicial da chat para italiano correto:
  - `Carica uno o più documenti e descrivi l'analisi di compliance che vuoi effettuare.`
- Ajustada a exibicao dos arquivos anexados na mensagem do usuario para aparecerem dentro da bolha azul da mensagem.
- Ajustada a configuracao de regiao do bucket de uploads da chat:
  - novo setting `COMPLIANCE_CHAT_BUCKET_REGION`;
  - fallback para `COMPLIANCE_DOCUMENTS_BUCKET_REGION`;
  - fallback final para `AWS_S3_REGION_NAME`;
  - a view de upload da chat agora usa essa regiao especifica para montar o client S3.
- Corrigido layout do filtro de cartella no gerenciador de documentos:
  - o `select` agora respeita a largura disponivel;
  - nomes longos de cartella nao estouram mais a linha/conteiner;
  - a busca permanece ao lado do filtro em telas maiores.
- Refinado o posicionamento da barra de filtros:
  - filtro de cartella ficou proximo ao contador `Documenti`;
  - campo de busca usa o espaco restante da linha;
  - icone de lupa recebeu mais padding para nao sobrepor o placeholder.
- Substituido o `select` nativo de cartella por dropdown customizado:
  - evita que opcoes muito longas expandam a largura do menu;
  - mantem largura fixa e truncamento visual das opcoes;
  - campo de pesquisa voltou a ficar a direita com largura controlada.

Validacao:

```txt
npm run build
```

Resultado: build concluido com sucesso.

Validacao backend:

```txt
python -m compileall core backend
```

Resultado: compilacao concluida com sucesso.

### 3. Chat Assistant

Status: parcialmente estabilizado.

Notas:

- Perplexity foi removido da tela.
- Fluxo principal permanece GPT/Terra.
- Build validado.
- Ainda revisar comportamento em runtime: envio, streaming, anexos e salvamento de conversas.

### 4. Newsletter

Status: pendente.

Notas:

- Tela adicionada pelo Replit.
- A revisar UX, contrato com backend, tags enviadas para Vera e renderizacao da bozza.
- Atenção especial a possiveis textos com encoding incorreto.

### 5. Consumo AI

Status: pendente.

Notas:

- A revisar endpoints de consumo Vera, ingestion, graficos e tabela.
- Confirmar permissoes e seguranca das APIs de ingestao.

## Pendencias tecnicas gerais

- Revisar se os endpoints novos de log/usage precisam de permissao mais restrita que `IsAuthenticated`.
- Verificar se existem textos com encoding incorreto em telas adicionadas pelo Replit.
- Confirmar se arquivos legados de Perplexity devem permanecer no backend ou ser removidos em uma limpeza futura.
- Avaliar warnings de bundle grande depois que as funcionalidades estiverem estaveis.
