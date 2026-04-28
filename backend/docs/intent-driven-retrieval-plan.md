# Intent-Driven Retrieval Plan

## Objetivo

Evoluir a pesquisa documental para um fluxo orientado por intent, sem substituir a arquitetura atual baseada em Responses API + MCP.

A ideia e melhorar a recuperacao documental e a qualidade das respostas sem transformar o backend em um sistema hardcoded nem migrar para agentes agora.

Essa evolucao deve ser compartilhada entre:

- API de integracao;
- funcionalidade do site;
- MCP comum utilizado pelos dois fluxos.

Por isso, a logica de intents e estrategias deve morar em uma camada compartilhada do `core`, e nao em `integrations`.

## Principio

O backend decide a estrategia de recuperacao, nao a resposta final.

Isso significa:

- classificar a pergunta em um intent conhecido quando houver sinais suficientes;
- escolher filtros, prioridades e agrupamentos mais adequados;
- manter um fallback generico quando a pergunta nao se encaixar em nenhum intent conhecido;
- continuar usando a OpenAI para sintese final.

## Regra de fallback

Se a pergunta nao tiver match confiavel com um intent conhecido, o sistema deve usar:

```text
intent_type = generic_document_search
```

Esse fallback deve manter o comportamento atual, baseado em busca progressiva e uso preferencial de `search_documents`.

## Intents iniciais

Os intents iniciais derivam diretamente das 8 perguntas reais do cliente.

### 1. appointment_and_powers

Pergunta-base:

- Quando e stato nominato l'Amministratore Delegato e quali poteri gli sono stati attributi

### 2. director_general_appointment_check

Pergunta-base:

- E stato nominato un Direttore Generale?

### 3. financial_summary_last_three_years

Pergunta-base:

- Effettua una sintesi dei dati di bilancio degli ultimi tre esercizi

### 4. control_functions_findings_and_remedies

Pergunta-base:

- Quali sono stati i rilievi delle funzioni di controllo (Risk, Compliance e Internal Audit) nell'esercizio 2025 e quali sono stati i piani di rimedi proposti

### 5. investment_policies_summary_by_board

Pergunta-base:

- Effettua una sintesi delle politiche di investimento deliberate dal Consiglio di Amministrazione nel corso del 2025 sui portafogli in delega

### 6. risk_management_board_involvement

Pergunta-base:

- Quante volte la funzione di risk management e stata coinvolta nelle riunioni del Consiglio di Amministrazione ed ha svolto le proprie analisi in merito alla politica di investimento

### 7. organizational_structure_year_comparison

Pergunta-base:

- Se e stata modificata e come e stata modificata la relazione sulla struttura organizzativa nel 2025 rispetto al 2024

### 8. consob_topic_meeting_tracking

Pergunta-base:

- In quali riunioni del consiglio di Amministrazione e stato trattato il tema di contestazioni da parte di Consob?

### 9. generic_document_search

Fallback para perguntas que nao se encaixem com confianca nos intents acima.

## Fase 1

Criar componentes base e nao intrusivos:

- `intent_classifier.py`
- `retrieval_strategies.py`

Sem alterar o fluxo principal ainda.

### Entregas da fase 1

1. Catalogo central de intents.
2. Classificacao heuristica inicial.
3. Estrategias declarativas por intent.
4. Funcoes utilitarias para fallback seguro.

Local recomendado:

- `core/services/document_retrieval/intent_classifier.py`
- `core/services/document_retrieval/retrieval_strategies.py`

## Estrategias por intent

### appointment_and_powers

- prioridade para documentos de governanca, nomeacao, verbali, estratti, deleghe e poteri;
- foco em localizar evento de nomeacao e atribuicao de poderes;
- agrupamento preferencial por data de reuniao.

### director_general_appointment_check

- busca objetiva por nomeacao de Direttore Generale;
- preferencia por documentos de governanca;
- se nao houver evidencia, responder com cautela.

### financial_summary_last_three_years

- agrupamento por ano;
- preferencia por documentos de bilancio, relazioni e material financeiro principal;
- evitar anexos pouco relevantes.

### control_functions_findings_and_remedies

- foco em Risk, Compliance e Internal Audit;
- agrupar por funcao e/ou ano;
- procurar achados, rilievi, remediation, piani di rimedi, action plan.

### investment_policies_summary_by_board

- priorizar verbali/estratti/relazioni com politica di investimento;
- foco em 2025;
- agrupar por reuniao do CdA.

### risk_management_board_involvement

- foco em ocorrencias em reunioes;
- agrupar por `meeting_date`;
- contar reunioes ou evidencias de participacao.

### organizational_structure_year_comparison

- localizar documentos equivalentes em 2024 e 2025;
- comparar por familia documental;
- selecionar um documento principal por ano.

### consob_topic_meeting_tracking

- foco em tema transversal por reuniao;
- agrupar por reuniao;
- priorizar verbali e estratti do CdA com sinais de Consob.

### generic_document_search

- manter comportamento atual;
- usar `search_documents` como estrategia principal;
- sem agrupamento forte nem filtros tematicos adicionais.

## Mudancas futuras provaveis no indice

Esses campos parecem os mais promissores para fases seguintes:

- `meeting_date`
- `governing_body`
- `document_family`
- `topic_tags`
- `control_function_tags`

Esses campos nao entram obrigatoriamente na fase 1.

## Mudancas futuras provaveis no MCP

Talvez sejam necessarias em fases posteriores, mas nao obrigatoriamente agora:

- suportar filtros por `document_family`;
- suportar filtros por `topic_tags`;
- suportar filtros por `control_function_tags`;
- suportar agrupamento por reuniao/ano;
- aceitar uma `strategy` opcional no `search_documents`.

## Criterio de sucesso da fase 1

- o sistema consegue identificar as perguntas mais recorrentes do cliente;
- existe um fallback seguro para perguntas fora do catalogo;
- a logica fica modular e legivel;
- a arquitetura fica pronta para futuras evolucoes sem retrabalho grande.

## Validacao da fase 1

Os testes realizados com perguntas reais do cliente validaram a direcao da fase 1.

### Casos validados com bom resultado

- `appointment_and_powers`
- `director_general_appointment_check`
- `financial_summary_last_three_years`
- `organizational_structure_year_comparison`
- `consob_topic_meeting_tracking`
- `control_functions_findings_and_remedies`

### Aprendizados principais

- a classificacao por intent esta acertando bem os casos conhecidos;
- o enriquecimento do prompt melhorou a escolha dos documentos e a estrutura das respostas;
- perguntas objetivas e de governanca ficaram mais confiaveis;
- perguntas comparativas e por reuniao passaram a recuperar trilhas documentais melhores;
- perguntas analiticas densas continuam caras, mesmo quando a resposta final fica boa.

### Padrao de latencia observado

- perguntas objetivas: melhor comportamento relativo;
- perguntas comparativas e por reuniao: comportamento bom, mas ainda caro;
- perguntas analiticas multi-ano ou multi-funcao: custo alto, com tempo concentrado na OpenAI/orquestracao.

### Conclusao da fase 1

A fase 1 deve ser considerada validada como camada de orientacao de busca.

O proximo ganho relevante nao vem de criar mais intents nem de adicionar mais termos manuais, e sim de estruturar melhor a evidencia antes da sintese final do modelo.

## Fase 2

Objetivo:

- reduzir exploracao desnecessaria do modelo em intents analiticos;
- preparar melhor a evidencia antes da chamada final de sintese;
- manter a arquitetura agent-ready sem criar handoffs, grafo de execucao ou logica hardcoded de resposta.

### Principio da fase 2

O backend continua sem decidir a resposta final.

Ele passa apenas a:

- compactar e organizar melhor a evidencia documental;
- limitar o numero de documentos realmente relevantes por bloco analitico;
- entregar para o modelo uma base mais enxuta e mais estruturada para sintese.

### Escopo minimo recomendado

Criar uma camada leve de preparacao de evidencia para intents analiticos, sem mexer no MCP inicialmente.

Local recomendado:

- `core/services/document_retrieval/evidence_builder.py`

### Intents prioritarios da fase 2

1. `financial_summary_last_three_years`
2. `control_functions_findings_and_remedies`
3. `organizational_structure_year_comparison`

Esses tres intents foram os que mais mostraram necessidade de estrutura adicional antes da sintese final.

### Estrategia por intent na fase 2

#### financial_summary_last_three_years

- selecionar no maximo um documento principal por ano;
- montar blocos de evidencia por exercicio;
- evitar que o modelo explore anexos paralelos quando um documento principal ja representa o ano.

#### control_functions_findings_and_remedies

- selecionar no maximo um documento principal por funcao;
- montar blocos separados para Risk, Compliance e Internal Audit;
- destacar achados e remedios antes da sintese final.

#### organizational_structure_year_comparison

- selecionar um documento base por ano;
- permitir no maximo um documento adicional de suporte, como verbale de aprovacao/aggiornamento;
- montar evidencia ja orientada para comparacao entre versoes.

### Estrutura desejada da evidencia

A evidencia preparada deve ser pequena, legivel e previsivel.

Exemplo conceitual:

```text
intent_type=financial_summary_last_three_years
evidence_grouping=year

2024
- documento principal
- trechos curtos relevantes

2023
- documento principal
- trechos curtos relevantes

2022
- documento principal
- trechos curtos relevantes
```

Ou, para funcoes de controle:

```text
intent_type=control_functions_findings_and_remedies
evidence_grouping=control_function

Compliance
- documento principal
- rilievi
- rimedi

Risk Management
- documento principal
- rilievi
- rimedi

Internal Audit
- documento principal
- rilievi
- rimedi
```

### Regras de contencao

Para evitar crescimento excessivo nessa camada:

- nao criar mais intents nesta fase;
- nao aumentar listas fixas de termos;
- nao mover logica de conteudo da resposta para o backend;
- nao introduzir OCR ou leitura completa como padrao;
- nao mexer no MCP antes de validar ganho com evidencias mais estruturadas.

### Mudancas tecnicas minimas da fase 2

1. criar um `evidence_builder` compartilhado;
2. permitir que estrategias declarem um `evidence_grouping` simples;
3. preparar contexto estruturado apenas para intents prioritarios;
4. manter fallback total para o fluxo atual quando nao houver evidencia suficiente.

### Criterio de sucesso da fase 2

- reduzir o trabalho exploratorio do modelo em intents analiticos;
- manter ou melhorar a qualidade das respostas validadas na fase 1;
- reduzir latencia nos casos mais caros, mesmo que parcialmente;
- manter a camada pequena, legivel e reutilizavel entre integracao e site.

## Limite identificado na fase 2

Os testes mostraram um limite claro da abordagem baseada apenas em orientacao por prompt:

- `financial_summary_last_three_years` respondeu bem a um `evidence_plan` leve;
- `control_functions_findings_and_remedies` manteve boa qualidade, mas piorou em latencia.

Conclusao:

- prompt guidance leve ajuda quando o agrupamento e simples e temporal;
- para intents analiticos mais densos por funcao ou tema, o proximo ganho relevante deve vir de enriquecimento do indice, nao de mais instrucoes textuais nem de logica acoplada aos documentos atualmente encontrados.

## Proxima fase recomendada: indice enriquecido

Objetivo:

- melhorar a recuperacao com base em sinais estruturados e estaveis;
- reduzir dependencia de nomes acidentais dos documentos atuais;
- preparar o terreno para filtros melhores no backend e, depois, no MCP.

### Principio

Os novos campos devem ser:

- baratos de derivar;
- baseados em sinais relativamente estaveis;
- uteis tanto para o site quanto para a integracao;
- adicionados de forma incremental, sem obrigar migracao de arquitetura.

### Base atual do indice

Hoje o `DocumentIndex` ja possui:

- `client`
- `bucket_name`
- `object_key`
- `filename`
- `extension`
- `size_bytes`
- `last_modified`
- `etag`
- `year`
- `document_type`
- `text_preview`
- `extracted_text`
- `extraction_status`

Tambem ja existem derivacoes heuristicas para:

- `year`
- `document_type`

E a busca atual usa principalmente:

- `filename`
- `object_key`
- `document_type`
- `year`
- `text_preview`

### Campos candidatos para enriquecimento

#### 1. `document_family`

Finalidade:

- classificar melhor o papel documental do arquivo, em um nivel mais util do que o `document_type` atual.

Exemplos de familias desejadas:

- `verbale_cda`
- `estratto_cda`
- `bilancio`
- `relazione_struttura_organizzativa`
- `report_controlli`
- `policy_investimento`
- `materiale_supporto`

Origem heuristica inicial:

- `object_key`
- `filename`
- combinacoes de termos com o `document_type`

Valor esperado:

- melhorar perguntas de nomeacao, comparacao anual, politica di investimento e tracking por reuniao.

#### 2. `control_function_tags`

Finalidade:

- identificar quando um documento pertence ou se refere a uma funcao de controle.

Tags iniciais:

- `risk`
- `compliance`
- `internal_audit`
- `aml`

Origem heuristica inicial:

- `filename`
- `object_key`
- `text_preview` quando disponivel

Valor esperado:

- melhorar principalmente `control_functions_findings_and_remedies`;
- ajudar tambem em `risk_management_board_involvement`.

#### 3. `topic_tags`

Finalidade:

- marcar temas recorrentes importantes sem depender apenas de busca textual livre.

Tags candidatas iniciais:

- `consob`
- `contestazioni`
- `nomina`
- `poteri`
- `deleghe`
- `bilancio`
- `market_abuse`
- `struttura_organizzativa`
- `politica_investimento`
- `rimedi`
- `rilievi`

Origem heuristica inicial:

- `filename`
- `object_key`
- `text_preview`

Valor esperado:

- melhorar busca tematica transversal;
- reduzir falsos positivos em perguntas por assunto.

#### 4. `governing_body`

Finalidade:

- identificar o orgao principal relacionado ao documento.

Valores iniciais:

- `cda`
- `assemblea`
- `collegio_sindacale`
- `altro`

Origem heuristica inicial:

- `object_key`
- `filename`

Valor esperado:

- melhorar perguntas ligadas a reunioes do Consiglio di Amministrazione;
- ajudar a filtrar documentos de governanca.

#### 5. `meeting_date`

Finalidade:

- explicitar data de reuniao quando ela estiver embutida no caminho ou no nome do documento.

Origem heuristica inicial:

- padroes em `object_key`
- padroes em `filename`

Valor esperado:

- melhorar `consob_topic_meeting_tracking`;
- melhorar `appointment_and_powers`;
- preparar agrupamento por reuniao.

### Ordem recomendada de implementacao

#### Etapa 1

- `document_family`
- `control_function_tags`

Motivo:

- maior ganho para os intents que mais expuseram limites recentes;
- sinais relativamente baratos de derivar.

#### Etapa 2

- `topic_tags`

Motivo:

- amplia muito a recuperacao tematica sem ainda exigir parser de reunioes.

#### Etapa 3

- `governing_body`
- `meeting_date`

Motivo:

- muito uteis, mas com heuristica um pouco mais sensivel a formato de path.

### Onde implementar

Ponto principal:

- `backend/integrations/services/document_index_sync.py`

Complementos possiveis:

- `backend/integrations/models/__init__.py`
- nova migration para os campos adicionais em `DocumentIndex`

### Estrategia tecnica recomendada

1. adicionar campos novos no modelo;
2. criar inferencias heuristicas pequenas e legiveis;
3. preencher esses campos durante o sync do indice;
4. nao depender de preview para todos os casos, mas usar `text_preview` como sinal adicional quando existir;
5. so depois expor filtros novos na API interna do indice e, posteriormente, no MCP.

### O que evitar

- nao codificar logica dependente dos documentos especificos que apareceram nos testes;
- nao criar taxonomias grandes demais logo no inicio;
- nao usar OCR nem LLM para enrichimento nesta fase;
- nao misturar regra de recuperacao com regra de resposta.

### Primeiro corte recomendado

Se for para escolher apenas um inicio pequeno e de alto retorno, a ordem recomendada e:

1. adicionar `document_family`
2. adicionar `control_function_tags`

Isso deve atacar diretamente:

- `control_functions_findings_and_remedies`
- `organizational_structure_year_comparison`
- `consob_topic_meeting_tracking`

sem depender da base atual de documentos de forma fragil.

## Resumo executivo da fase atual

### Leitura geral

A combinacao de:

- camada de intent;
- enriquecimento do indice;
- exposicao de filtros estruturados no MCP;
- e reforcos pequenos no prompt

produziu uma melhora real de qualidade e uma melhora relevante de eficiencia em parte importante dos casos testados.

O principal ganho desta rodada foi fazer o modelo encontrar o trilho documental correto mais cedo, sem acoplar a arquitetura aos documentos especificos hoje presentes na base.

### O que ja pode ser considerado validado

- `financial_summary_last_three_years`
- `control_functions_findings_and_remedies`
- `consob_topic_meeting_tracking`

Esses intents mostraram combinacao boa entre:

- qualidade da resposta;
- selecao documental coerente;
- uso real dos filtros estruturados;
- e reducao de latencia em relacao aos cenarios anteriores mais caros.

No caso de `consob_topic_meeting_tracking`, o ajuste final mais eficaz nao foi um endurecimento generico de stopping, e sim um `evidence_plan` curto e especifico para garantir cobertura de todas as riunioni rilevanti del medesimo procedimento Consob, incluindo fases iniziali e successive sem colapsar a resposta apenas no evento mais formal.

### O que esta quase validado

- `investment_policies_summary_by_board`
- `organizational_structure_year_comparison`

Nesses casos, a recuperacao e a resposta ja estao boas, mas ainda existe algum espaco para reduzir exploracao redundante depois que o perimetro documental correto ja foi encontrado.

### O que claramente funcionou

- `document_family`
- `control_function_tags`
- `topic_tags`
- uso desses campos no MCP
- regras adicionais no prompt para favorecer filtros estruturados e reduzir redundancia

O efeito combinado foi melhor do que insistir apenas em `evidence_plan` textual para todos os casos.

### Limite atual identificado

O principal problema remanescente deixou de ser descoberta documental pura.

Agora, o padrao mais recorrente e:

- o modelo encontra cedo os documentos ou familias corretas;
- mas em alguns casos continua explorando mais do que o necessario antes de encerrar a resposta.

Portanto, a proxima fronteira de ganho e mais sobre disciplina de parada e reducao de exploracao redundante do que sobre criar novas taxonomias imediatamente.

### Recomendacao de curto prazo

- considerar esta fase bem-sucedida e suficientemente madura para consolidacao;
- evitar abrir uma nova frente estrutural grande agora;
- permitir apenas refinamentos pequenos de stopping e anti-redundancia;
- continuar validando com perguntas reais do cliente antes de endurecer a orquestracao no backend.

### Proxima prioridade tecnica recomendada

Se houver nova iteracao tecnica, ela deve ser pequena e focada em um unico objetivo:

- reduzir exploracao redundante apos uma primeira busca estruturada bem-sucedida.

A ordem recomendada continua sendo:

1. tentar esse ajuste no prompt;
2. medir novamente;
3. so depois considerar uma orquestracao leve e deterministica no backend para intents conhecidos.

## Status consolidado dos intents

### Fortemente validados

- `financial_summary_last_three_years`
- `consob_topic_meeting_tracking`

### Praticamente validados fortes

- `control_functions_findings_and_remedies`
- `investment_policies_summary_by_board`
- `organizational_structure_year_comparison`
- `appointment_and_powers`
- `director_general_appointment_check`

### Validados ou quase validados

- `risk_management_board_involvement`

### Leitura final deste ciclo

O ciclo atual confirmou que:

- filtros estruturados no indice e no MCP valem o investimento;
- pequenos reforcos no prompt funcionam melhor quando seguem a estrutura real da pergunta;
- `evidence_plan` curto e seletivo funciona melhor do que tentar generalizar demais a camada de stopping;
- o melhor proximo passo continua sendo refinamento pequeno e medido, nao ampliacao estrutural ampla.

No caso de `risk_management_board_involvement`, a melhora veio quando o `evidence_plan` passou a explicitar melhor:

- o criterio de contagem por riunione;
- a exigencia de contributo analitico concreto da funzione;
- e a exclusao de evidenza apenas indireta do total final.

Esse intent deve ser tratado como quase validado forte: a qualidade e a eficiencia melhoraram bastante, mas ainda existe uma nuance residual de recorte temporal implicito quando a pergunta nao fixa ano de forma expressa.

No caso de `investment_policies_summary_by_board`, a melhora veio quando o `evidence_plan` passou a separar com mais clareza:

- continuidade das investment guidelines;
- aggiustamenti puntuali su singoli fondi o prodotti;
- vere modifiche di policy o asset allocation.

Esse intent deve ser tratado como praticamente validado forte: a resposta passou a organizar melhor as riunioni rilevanti e a evitar interpretar monitoramento recorrente como mudanca strutturale di politica di investimento.

No caso de `control_functions_findings_and_remedies`, a melhora mais recente veio da combinacao de tres fatores:

- maior disponibilidade de `text_preview`, sobretudo para relazioni annuali di controllo;
- leitura mais conservadora no MCP, reduzindo casos em que `excerpt` acabava se comportando como leitura completa de PDF;
- `evidence_plan` mais restritivo, primeiro para privilegiar `preview/excerpt` e depois para limitar a expansao para documentos tematicamente correlati.

Esse intent deve ser tratado como praticamente validado forte: a qualidade permaneceu boa, a latencia caiu de forma relevante e o uso de documentos ficou mais disciplinado. A ressalva residual principal deixou de ser semantica e passou a ser operacional: o modelo ainda sobe para `full` em alguns verbali com certa facilidade, embora em um perimetro documental bem mais controlado do que antes.

No caso de `organizational_structure_year_comparison`, a melhora veio quando o `evidence_plan` passou a:

- privilegiar documentos realmente equivalentes entre os dois anos;
- separar melhor mudancas substanciais, atualizacoes menores e continuidade;
- reduzir o risco de interpretar diferencas redacionais como mudancas reais de assetto.

Esse intent deve ser tratado como praticamente validado forte. O risco residual principal nao esta mais na semantica do intent, mas na variabilidade de custo quando o modelo decide abrir PDFs longos em `mode=full` em vez de resolver a comparacao com `excerpt` suficiente.

No caso de `appointment_and_powers`, a melhora veio quando o `evidence_plan` passou a privilegiar explicitamente:

- a fonte societaria primaria de nomina e deleghe;
- a separacao entre delibera formale e semplici richiami biografici al ruolo;
- o uso de CV e autodichiarazioni apenas como contesto secondario.

Esse intent deve ser tratado como praticamente validado forte: a resposta passou a ancorar melhor a conclusao no verbale societario rilevante e a reduzir a ambiguidade entre data di nomina formale e storico professionale dichiarato.

No caso de `director_general_appointment_check`, a melhora veio quando a strategia passou a exigir com mais firmeza:

- evidenza formale ed esplicita di nomina;
- distinzione entre nomina, menzione del ruolo e incarichi ad interim;
- uso de fonte societaria primaria come base della conclusione.

Esse intent deve ser tratado como praticamente validado forte: a resposta ficou direta, bem ancorada no verbale corretto e com baixo risco residual de inferencia indevida.

## Proximo foco apos a estabilizacao dos intents

Com o catalogo inicial praticamente consolidado, a proxima fronteira tecnica muda de natureza.

O ganho principal agora nao parece vir de:

- criar novos intents;
- ampliar listas de termos;
- ou adicionar mais regras semanticas finas por pergunta.

O ganho principal passa a vir de:

- reduzir exploracao residual depois que a trilha documental correta ja foi encontrada;
- reduzir leitura pesada de documentos longos, sobretudo PDFs, quando `excerpt` ja seria sufficiente;
- e tornar mais previsivel a escolha entre `preview`, `excerpt` e `full`.

### Prioridades tecnicas recomendadas para a proxima etapa

#### 1. Reducao de leitura pesada

Objetivo:

- diminuir casos em que o modelo abre PDFs longos em `mode=full` apenas para confirmar diferencas que poderiam vir de `excerpt`.

Direcoes possiveis:

- melhorar o recorte de `excerpt` para documentos estruturados e longos;
- priorizar trechos de indice, sommario ou sezioni organizzative quando o documento tiver estrutura previsivel;
- tornar mais facil para o modelo reconhecer quando o preview ja cobre a diferenca procurada.

#### 2. Reducao de exploracao residual

Objetivo:

- evitar que o modelo reabra buscas textuais amplas depois de ja ter identificado documentos primarios adequados.

Direcoes possiveis:

- reforcos pequenos adicionais no prompt, se necessario;
- ou, se os ganhos por prompt saturarem, uma orquestracao backend muito leve apenas para casos bem delimitados.

#### 3. Observabilidade orientada a custo

Objetivo:

- medir melhor onde a latencia ainda esta sendo gasta.

Direcoes possiveis:

- distinguir com mais clareza custo de descoberta, custo de leitura e custo de sintese;
- registrar quando houve abertura de `mode=full`;
- identificar intents em que o caminho bom ja existe, mas ainda nao e seguido com consistencia.

### Leitura final do estado atual

Hoje o sistema parece estar em um ponto bom para mudar de foco:

- a camada semantica de intents esta madura o bastante;
- os filtros estruturados do indice provaram valor real;
- os `evidence_plan` curtos e seletivos funcionaram melhor do que regras genericas mais amplas;
- o problema remanescente dominante passou a ser eficiencia operacional de recuperacao e leitura, nao compreensao da pergunta.

## Proposta tecnica curta da proxima fase

### Objetivo

Reduzir latencia residual sem mexer na arquitetura principal, atacando dois comportamentos observados nos logs:

- abertura de `mode=full` quando `excerpt` ou `preview` ja eram potencialmente suficientes;
- reabertura de buscas textuais depois que o perimetro documental correto ja estava razoavelmente definido.

### Escopo minimo

1. adicionar uma camada leve de heuristica de leitura no MCP;
2. melhorar a observabilidade para diferenciar descoberta, leitura leve, leitura pesada e sintese;
3. validar o ganho em 2 ou 3 intents caros antes de qualquer mudanca mais estrutural.

### Mudanca 1: heuristica de leitura mais conservadora

Objetivo:

- reduzir abertura de documentos longos em `mode=full`, sobretudo PDFs anuais e relazioni.

Implementacao candidata:

- `backend/mcp_server_ricerca/server/server.py`

Ideia:

- quando existir `text_preview` suficiente, reforcar o retorno de `excerpt` com recorte util antes de permitir `full`;
- para PDFs longos, privilegiar trechos iniciais ou trechos estruturais antes de leitura completa;
- manter `full` disponivel, mas tornar seu uso mais excepcional e melhor observavel.

### Mudanca 2: observabilidade de custo por request

Objetivo:

- entender com mais clareza onde cada intent ainda gasta tempo.

Implementacao candidata:

- `backend/integrations/views/ricerca_documentale.py`
- `backend/core/views/openai/chat/assistant/assistant_streaming_view.py`
- `backend/mcp_server_ricerca/server/server.py`

Ideia:

- manter logs de `cost_tier`;
- consolidar por request sinais como:
  - quantidade de buscas;
  - quantidade de `list_documents`;
  - quantidade de `get_document`;
  - quantos `full` e quantos `heavy`.

### Mudanca 3: reducao de exploracao residual

Objetivo:

- evitar loops de descoberta quando o modelo ja tem documentos primarios adequados.

Implementacao candidata:

- primeiro no prompt/contexto;
- so depois, se necessario, no backend.

Ideia:

- usar os logs atuais para identificar intents em que a deriva ainda e sistematica;
- aplicar reforcos pequenos e localizados antes de qualquer orquestracao deterministica.

### Ordem recomendada

1. melhorar leitura conservadora no MCP;
2. enriquecer logs por request com contadores simples;
3. rodar novamente:
   - `organizational_structure_year_comparison`
   - `control_functions_findings_and_remedies`
   - `financial_summary_last_three_years`
4. medir se o custo residual caiu;
5. so entao decidir se vale introduzir uma orquestracao backend mais explicita.
