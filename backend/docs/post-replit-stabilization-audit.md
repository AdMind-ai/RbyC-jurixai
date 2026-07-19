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

Status: fechado nesta etapa.

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

Status: fechado nesta etapa.

Notas:

- Perplexity foi removido da tela.
- Fluxo principal permanece GPT/Terra.
- Build validado.
- Ainda revisar comportamento em runtime: envio, streaming, anexos e salvamento de conversas.

Ajustes aplicados:

- Confirmado que a tela deve operar apenas com `GPT-5.6 - Terra`.
- Atualizado o identificador frontend do modelo para `gpt-5.6-terra`.
- O envio da mensagem agora manda explicitamente:
  - `model=gpt-5.6-terra`;
  - `web_search_enabled=true|false`.
- Backend passou a aceitar apenas `gpt-5.6-terra` no endpoint da Chat Assistant.
- Corrigido o comportamento de `Cerca nel web`:
  - quando ativado, o backend envia `web_search_preview`;
  - quando desativado, o backend nao envia ferramentas de web search.
- Registro de consumo da Chat Assistant passou a usar o subtool `GPT-5.6 Terra`.
- Adicionados testes backend para validar:
  - web search desligado nao envia `tools`;
  - web search ligado envia `web_search_preview`;
  - modelos nao suportados sao rejeitados.

### 4. Newsletter

Status: fechado nesta etapa.

Notas:

- Tela adicionada pelo Replit.
- A revisar UX, contrato com backend, tags enviadas para Vera e renderizacao da bozza.
- Atenção especial a possiveis textos com encoding incorreto.

Atualizacao Newsletter:

- A tag `[CHAT]` nao pertence a Newsletter; fica restrita ao fluxo de chat do Check Compliance.
- Newsletter deve enviar apenas:
  - `newsletter` -> `[NEWSLETTER]`;
  - `pill` -> `[PILL FORMATIVO]`.
- O backend reforca que o conteudo final deve vir em um unico bloco `<bozza>...</bozza>` como ultimo elemento isolado da resposta.
- O frontend permanece somente com as opcoes `Newsletter` e `PILL Formativo`.
- Service frontend aceita apenas `draft_type=newsletter|pill`.
- Foram adicionados testes backend para validar o envio das tags `[NEWSLETTER]` e `[PILL FORMATIVO]`.

### 5. Consumo AI

Status: proxima revisao.

Notas:

- A revisar endpoints de consumo Vera, ingestion, graficos e tabela.
- Confirmar permissoes e seguranca das APIs de ingestao.
- Area considerada delicada; aguardar explicacao do fluxo esperado antes de alterar codigo.
- Pontos iniciais a mapear:
  - origem dos dados de consumo;
  - quem pode ingerir dados;
  - quem pode visualizar dados;
  - como separar consumo interno, consumo Vera e consumo por integracao/API key;
  - quais telas devem exibir agregados, detalhamento por usuario e detalhamento por cliente.

Fluxo esperado informado:

- OpenAI possui dois projetos relevantes:
  - `Rbyc`: custos das funcionalidades que usam IA diretamente no app, exceto agente Vera.
  - `Vera_Rbyc`: custos OpenAI do agente Vera, usado em `Check Compliance` e `Newsletter`.
- Claude/Anthropic entra apenas no custo do agente Vera, tambem associado a `Check Compliance` e `Newsletter`.
- A fonte de verdade dos custos deve ser a API/admin key dos providers, nao estimativa manual por interacao.
- A tela deve considerar o mes atual.
- Calculos esperados:
  - `custo_openai`: custo OpenAI do projeto `Rbyc`.
  - `custo_vera`: custo OpenAI do projeto `Vera_Rbyc` + custo Claude/Anthropic do agente Vera.
  - Markup do custo OpenAI direto do app/Rbyc: 20%.
  - Markup do custo do Agente Vera: 25%.
  - `Totale Mensile`: `(custo_openai + 20%) + (custo_vera + 25%)`.
  - `Totale con IVA`: `Totale Mensile + 22%`.
  - `Consumo Agente Vera`: `(custo_vera + 25%) + 22%`.

Estado atual encontrado:

- O backend ja possui `UsageRecord`, usado para contar interacoes por ferramenta/usuario.
- O backend ja possui `VeraUsageRecord`, usado para guardar custos Vera por dia, provider e modelo.
- Existe comando `sync_vera_costs`, que busca custos Vera na OpenAI e Anthropic e grava em `VeraUsageRecord`.
- Existem settings para Vera:
  - `VERA_OPENAI_ADMIN_KEY`;
  - `VERA_OPENAI_PROJECT_ID`;
  - `VERA_ANTHROPIC_API_KEY`;
  - `VERA_ANTHROPIC_WORKSPACE_ID`.
- Existe app `billing` com `ProviderMonthlyCost` e `ProviderCostService`, que busca custo OpenAI mensal.
- O `ProviderCostService` foi ajustado para considerar apenas OpenAI/RbyC no total mensal cobrado. Custos historicos de Perplexity podem continuar registrados, mas nao entram no novo fluxo de cobranca.
- O markup padrao do billing atual esta configurado como `BILLING_COMPANY_MARKUP_PERCENTAGE=20`.
- O fluxo desejado mantem 20% para custo OpenAI direto do app/Rbyc e usa 25% apenas para o Agente Vera.
- A tela `Usage.tsx` hoje usa:
  - `/usage/report/` para contagem de interacoes;
  - `/billing/monthly-summary/` para cards `Totale mensile` e `Totale con IVA`;
  - `/vera/usage/daily/` no grafico `Consumo Agente Vera`.
- O grafico `VevaUsageChart` passou a receber o valor Vera diario ja com markup + IVA calculado pelo backend.
- O endpoint `/billing/monthly-summary/` passou a retornar tambem `veraTotalWithVatEur` e `costBreakdown`, mantendo compatibilidade com os cards existentes.

Decisoes confirmadas:

- O project ID OpenAI do projeto `Rbyc` existe e sera configurado em env.
- O project ID OpenAI do projeto `Vera_Rbyc` existe e sera configurado em env.
- A Admin API key da Anthropic/Claude para custos Vera existe e sera configurada em env.
- A tela deve abrir no mes atual.
- A tela pode permitir selecionar meses anteriores quando existirem no historico do banco.
- Valores monetarios em euros devem ser visiveis apenas para admin ou company admin.
- A cobranca Stripe deve continuar existindo.
- O valor cobrado no Stripe deve ser o mesmo exibido em `Totale con IVA`.

Riscos/ajustes necessarios:

- Separar claramente "contagem de uso" de "custo monetario".
- Integrar o fluxo novo de Consumo AI com o billing/Stripe sem criar divergencia de calculo.
- O servico que gera a cobranca Stripe deve reutilizar o mesmo calculo consolidado exibido na tela.
- Nao reaproveitar `Perplexity` no calculo novo, pois foi removido do fluxo ativo da Chat Assistant.
- Centralizar markups e IVA no backend.
- Manter markups distintos:
  - Rbyc/OpenAI direto: 20%;
  - Vera/OpenAI + Claude: 25%.
- Garantir que os custos OpenAI do projeto `Rbyc` e do projeto `Vera_Rbyc` nao sejam duplicados.
- Definir variaveis de ambiente separadas para os dois projetos OpenAI.
- Rever permissao dos endpoints de ingestao/sync e visualizacao, principalmente custos reais.

Planejamento proposto:

1. Modelagem/configuracao
   - Definir settings explicitos:
     - Reutilizar `OPENAI_ADMIN_KEY`;
     - `RBYC_OPENAI_PROJECT_ID`;
     - `VERA_OPENAI_ADMIN_KEY`;
     - `VERA_OPENAI_PROJECT_ID`;
     - `VERA_ANTHROPIC_API_KEY`;
     - `VERA_ANTHROPIC_WORKSPACE_ID`;
     - `AI_USAGE_RBYC_MARKUP_PERCENTAGE=20`;
     - `AI_USAGE_VERA_MARKUP_PERCENTAGE=25`;
     - `AI_USAGE_IVA_PERCENTAGE=22`.
   - Decidir se `BILLING_COMPANY_MARKUP_PERCENTAGE` continua sendo a fonte do markup Rbyc/OpenAI direto ou se sera criado setting separado.
   - Garantir que o billing mensal/Stripe use o mesmo calculo consolidado do Consumo AI.

2. Fonte de dados
   - Manter `UsageRecord` apenas para contagem operacional por ferramenta/usuario.
   - Usar dados de provider para custos monetarios.
   - Reaproveitar ou adaptar `VeraUsageRecord` para custos do agente Vera.
   - Criar/ajustar uma fonte mensal para custo OpenAI do projeto `Rbyc`.
   - Avaliar se `ProviderMonthlyCost` deve ser reaproveitado com escopo/projeto ou se sera melhor criar um model mais especifico para custos AI por projeto/provider.

3. Sync dos providers
   - OpenAI `Rbyc`: buscar custos do projeto `Rbyc` via Costs API e salvar/retornar como custo base app.
   - OpenAI `Vera_Rbyc`: buscar custos do projeto Vera e salvar como parte do custo Vera.
   - Anthropic/Claude Vera: buscar custos via Admin Cost Report e salvar como parte do custo Vera.
   - Garantir sync para o mes atual e, quando necessario, sincronizar dias anteriores para preencher historico.

4. Endpoint consolidado para tela
   - Criar endpoint dedicado, por exemplo `/api/usage/ai-costs/`.
   - Response sugerida:
     - `periodMonth`;
     - `currency`;
     - `rawCosts.openaiRbyc`;
     - `rawCosts.veraOpenai`;
     - `rawCosts.veraAnthropic`;
     - `rawCosts.veraTotal`;
     - `rawCosts.total`;
     - `billing.rbycWithMarkup`;
     - `billing.veraWithMarkup`;
     - `billing.monthlyWithMarkup`;
     - `billing.monthlyWithVat`;
     - `billing.veraWithMarkupAndVat`;
     - `rbycMarkupPercentage`;
     - `veraMarkupPercentage`;
     - `ivaPercentage`;
     - `sources/status/errors`.
   - Este endpoint deve ser a fonte principal para os cards financeiros da tela.
   - O mesmo servico de calculo deve ser usado pelo Stripe.

5. Frontend
   - Trocar os cards de `Usage.tsx` para consumir o endpoint consolidado.
   - `Totale mensile` deve mostrar `(openaiRbyc * 1.20) + (veraTotal * 1.25)`.
   - `Totale con IVA` deve mostrar `Totale mensile * 1.22`.
   - `Consumo Agente Vera` deve mostrar `veraTotal * 1.25 * 1.22`.
   - Manter tabela de interacoes (`ConsumptionTable`) separada, pois ela mede uso por ferramenta, nao custo real.
   - Ajustar `VevaUsageChart` para receber valores ja calculados pelo backend ou, no minimo, usar percentuais vindos do backend.
   - Ocultar cards financeiros para usuarios que nao sejam admin ou company admin, ou exibir apenas metricas nao monetarias.

6. Seguranca/permissoes
   - Visualizacao de custos reais deve ser restrita a admin/company admin conforme regra de negocio.
   - Endpoints de ingestao/sync devem ser admin/service-token, nao apenas `IsAuthenticated`.
   - Evitar expor project IDs sensiveis no frontend quando nao forem necessarios.

7. Validacao
   - Testes unitarios para formulas:
     - total mensal;
     - total com IVA;
     - consumo Vera.
     - markup distinto de 20% para Rbyc e 25% para Vera.
   - Testes para separacao dos projetos OpenAI.
   - Testes para ausencia de duplicidade entre `Rbyc` e `Vera_Rbyc`.
   - Testes garantindo que a cobranca Stripe usa exatamente `billing.monthlyWithVat`.
   - Build frontend e compile/test backend.

Implementacao realizada:

- Criado `billing/services/ai_usage_costs.py` como servico central de calculo financeiro do Consumo AI.
- Formula centralizada:
  - OpenAI/RbyC direto: custo base * 1.20;
  - Vera: (OpenAI Vera + Anthropic Vera) * 1.25;
  - Totale mensile: soma dos valores com markup;
  - Totale con IVA: Totale mensile * 1.22;
  - Consumo Agente Vera: Vera com markup * 1.22.
- `StripeBillingService.build_monthly_summary` passou a usar o servico consolidado.
- `MonthlyBillingService.generate_invoice_for_month` passou a cobrar no Stripe o mesmo `Totale con IVA` exibido na tela.
- Adicionados settings:
  - `RBYC_OPENAI_PROJECT_ID`;
  - `AI_USAGE_RBYC_MARKUP_PERCENTAGE`;
  - `AI_USAGE_VERA_MARKUP_PERCENTAGE`;
  - `AI_USAGE_IVA_PERCENTAGE`.
- `ProviderCostService` agora prioriza `RBYC_OPENAI_PROJECT_ID` para buscar custos OpenAI do app RbyC.
- Custos vindos dos providers nao passam mais por conversao USD -> EUR.
- O valor numerico retornado pelo provider e usado diretamente nas formulas de markup/IVA e salvo/exibido como EUR.
- A lista de meses disponiveis passou a incluir:
  - mes atual;
  - meses com `UsageRecord`;
  - meses com `IntegrationUsageRecord`;
  - meses com `ProviderMonthlyCost`;
  - meses com `VeraUsageRecord`.
- Cards financeiros e grafico Vera ficam restritos a admin/company admin.
- Os cards superiores continuam sendo:
  - `Totale mensile`;
  - `Totale con IVA`;
  - `Data addebito`.
- O valor de `Consumo Agente Vera` permanece no bloco/grafico especifico do Vera.
- `VevaUsageChart` deixou de aplicar markup/IVA no frontend e passou a usar `total_cost_with_markup_eur` retornado pelo backend.
- Teste unitario adicionado para garantir markup distinto de RbyC e Vera no calculo consolidado.
- Investigacao do valor zerado em `Consumo Agente Vera`:
  - o grafico nao consulta OpenAI/Anthropic em tempo real;
  - ele le os custos ja gravados em `VeraUsageRecord`;
  - existia o comando `sync_vera_costs`, mas nao havia atualizacao sob demanda quando a tela era aberta;
  - foi adicionada task `core.tasks.sync_vera_costs` para usos assíncronos/manuais;
  - a sincronizacao diaria por cron nao foi mantida, pois o custo deve ser atualizado quando a tela/cobranca precisar dele;
  - `/billing/monthly-summary/` atualiza custos Vera antes de calcular os cards e o valor Stripe;
  - `/vera/usage/daily/` nao sincroniza automaticamente no carregamento inicial para evitar chamadas duplicadas;
  - o botao de refresh do grafico chama `/vera/usage/daily/?refresh=true` e atualiza o periodo selecionado;
  - a cobranca mensal continua fazendo sync imediatamente antes de gerar a invoice.
- Correcao de valores inflados:
  - quando existe `project_id`, os custos OpenAI agora aceitam somente linhas com o project id exato;
  - linhas agregadas com `project_id=None` nao entram mais no calculo do projeto;
  - o sync Vera remove registros antigos daquele dia/provider que nao aparecem mais na resposta correta, evitando que dados inflados antigos continuem no grafico.
- Separacao entre leitura e sincronizacao de custos:
  - endpoints GET do dashboard nao devem chamar APIs administrativas dos providers;
  - `/billing/monthly-summary/` passa a ler custos ja salvos no banco;
  - `/vera/usage/daily/` passa a ler apenas `VeraUsageRecord`, mesmo quando o usuario clica no refresh visual;
  - o refresh do grafico atualiza a leitura do banco, sem chamar OpenAI/Anthropic;
  - a cobranca mensal continua podendo sincronizar custos imediatamente antes de gerar a invoice Stripe;
  - `sync_vera_costs` deve ser usado em job/cron ou manualmente para popular `VeraUsageRecord`;
  - o comando `sync_vera_costs` foi ajustado para usar sync por intervalo, reduzindo risco de rate limit na Anthropic;
  - `429` da Anthropic agora retorna status `rate_limited`, registra `Retry-After` e headers `anthropic-ratelimit-*`, e entra no cooldown do sincronizador.
- Agendamento Celery Beat definido para os custos Vera:
  - OpenAI Vera roda de hora em hora, no minuto configurado por `VERA_OPENAI_COST_SYNC_MINUTE` (padrao `0`);
  - Anthropic Vera roda diariamente no horario configurado por `VERA_ANTHROPIC_COST_SYNC_HOUR`/`VERA_ANTHROPIC_COST_SYNC_MINUTE` (padrao `06:00`);
  - ambos usam `VERA_COST_SYNC_DAYS` para definir a janela historica sincronizada (padrao 35 dias);
  - Anthropic usa defasagem configuravel por `VERA_ANTHROPIC_COST_REPORT_LAG_DAYS` (padrao 2 dias), pois o `cost_report` pode rejeitar dias recentes ainda nao finalizados;
  - Anthropic usa `VERA_ANTHROPIC_COST_REPORT_LIMIT` com maximo 31 e paginacao, pois a API rejeita `limit > 31`;
  - valores `amount` da Anthropic vem em unidade menor da moeda (centavos para USD), entao sao divididos por 100 antes de salvar em `VeraUsageRecord.cost_eur`;
  - a task `core.tasks.sync_vera_costs` aceita `provider=all|openai|anthropic`.

## Pendencias tecnicas gerais

- Revisar se os endpoints novos de log/usage precisam de permissao mais restrita que `IsAuthenticated`.
- Verificar se existem textos com encoding incorreto em telas adicionadas pelo Replit.
- Confirmar se arquivos legados de Perplexity devem permanecer no backend ou ser removidos em uma limpeza futura.
- Avaliar warnings de bundle grande depois que as funcionalidades estiverem estaveis.
