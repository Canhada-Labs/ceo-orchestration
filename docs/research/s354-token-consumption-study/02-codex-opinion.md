<!-- Lane 02 do estudo S354. Parecer do Codex CLI (pin do repo 0.154.0; modelo não registrado na colagem), produzido em 17/09/2026 a partir de prompts/02-codex-brief.md, com leitura do repositório e busca web. Colado pelo Owner a partir do terminal e salvo VERBATIM, incluindo a renderização de tabelas e as linhas de status do terminal. A avaliação do CEO sobre este parecer está no README.md, §5. -->

A conclusão está tomando forma: há medidas promissoras para economizar contexto, mas não
  há evidência para fixar "2 ou 3 agentes" como regra universal nem para prometer que cortar
  um terço dos tokens evitará todos os bloqueios. Vou separar as ações de baixo esforço das
  hipóteses que precisam de teste, mantendo o piso de modelo e revisão do código financeiro.

• Searching the web

• Searched the web for https://learn.chatgpt.com/docs/config-file/config-reference

────────────────────────────────────────────────────────────────────────────────────────────

• [INFERÊNCIA] Sim, há espaço para economizar contexto preservando as entregas. Mas eu
  corrigiria partes importantes do diagnóstico anterior antes de mudar o framework. O
  objetivo deve ser concluir mais trabalho aprovado por unidade de quota; manter sete
  agentes ocupados e aumentar tokens de output não mede isso.

  Análise realizada em 17/09/2026, com leitura do repositório e fontes primárias. Não
  alterei arquivos nem executei chamadas pagas de teste. [VERIFICADA] identifica evidência
  consultada; [NÃO VERIFICADA], afirmação ainda sem comprovação independente; [INFERÊNCIA],
  interpretação ou cenário.

  A. Diagnóstico independente

  [VERIFICADA] A instrumentação proposta já existe. O arquivo .claude/scripts/ceo-cost-
  transcripts.py:1, presente desde o commit 2ef423e31cd9, de 04/09, lê message.usage dos
  JSONL, separa sessão principal e subagentes, contabiliza cache e deduplica registros. Está
  integrado ao ceo-cost.py e ao budget-summary.py. Portanto, a afirmação de que todos os
  instrumentos dependem exclusivamente do audit-log está desatualizada.

  [VERIFICADA] "96,3% cache read" não significa "96,3% desperdício". Cache reaproveita
  processamento anterior. Além disso, conteúdo novo pode entrar em
  cache_creation_input_tokens; input_tokens representa apenas uma categoria da
  contabilização. Logo, os 0,007% de input não medem todo o conteúdo novo enviado.
  Documentação da API
  (https://platform.claude.com/docs/en/build-with-claude/prompt-caching).

  [INFERÊNCIA] O problema provável é a combinação de contexto desnecessário, chamadas
  excessivas e trabalho repetido. A participação do cache, isoladamente, não distingue essas
  causas. Também não permite estimar a penalidade na assinatura.

  [VERIFICADA] Os 97k não são uma medição isolada do peso do framework. O PLAN-179 estima um
  piso pós-compactação em uma sessão de agosto, com Opus 5, e explicita componentes cuja
  origem não conseguiu separar. Parte do prefixo permaneceu em cache. Transformar isso em
  "97k inteiramente regravados após toda compactação, em todo agente" excede a evidência.
  Medição e limitações (.claude/plans/PLAN-179/w0-measurement.md:711).

  [VERIFICADA] Existe evidência local contra atribuir tudo aos subagentes. O estudo S339, de
  02/09, sobre transcripts de 03/08–02/09 deste repo, atribuiu aproximadamente 71% do custo
  API-equivalente às sessões principais. Isso não contradiz automaticamente o perfil global
  de 16/09: são períodos, universos e métricas diferentes. Estudo anterior (docs/research/
  s339-orchestrator-study/05-finops-routing.md:155).

  [NÃO VERIFICADA] Não reproduzi os 57,5 bilhões nem a distribuição das últimas 24 horas a
  partir dos registros originais. Trato-os como dados fornecidos, referentes ao ambiente
  descrito e à CLI 2.1.274 apresentada na conversa.

  [INFERÊNCIA] Duas contas dimensionam as hipóteses:

  - Se os 238 requests principais tivessem realmente média de 600k, reduzi-la para 150k
    pouparia 107,1 milhões, aproximadamente 17% dos 630,7 milhões daquela sessão. Dividir
    4,9 milhões por oito misses não comprova essa média.

  - Um heartbeat de 865,3k, executado 48 vezes/dia, representa aproximadamente 3,8% da média
    diária dos 57,5 bilhões/52 dias. É uma alavanca clara, mas não explica sozinho o
    problema.

  [INFERÊNCIA] Reduzir consumo em um terço tampouco garante cinco horas sem bloqueio. Sob
  consumo constante e quota proporcional, um saldo que dura uma hora passaria a durar
  aproximadamente 1,5 hora. A relação real precisa ser medida.

  B. Literatura acadêmica: o que acrescenta ao estudo anterior

  [VERIFICADA] Multiagente depende da estrutura da tarefa. Kim et al., na revisão de abril
  de 2026, estudam 260 configurações e encontram resultados favoráveis em tarefas
  decomponíveis e desfavoráveis em planejamento sequencial. O modelo explicativo tem poder
  preditivo limitado; não autoriza uma regra universal de quantidade de agentes. Os
  experimentos tampouco reproduzem a quota Max. Scaling Agent Systems
  (https://arxiv.org/abs/2512.08296v3).

  [VERIFICADA] O conhecido "15×" tem como referência chat simples. A Anthropic informa
  aproximadamente 4× para agentes e 15× para sistemas multiagente, em seu sistema de
  pesquisa de 2025. Não é uma medição deste framework nem uma comparação universal de 15×
  contra agente único. Relato original
  (https://www.anthropic.com/engineering/multi-agent-research-system).

  [VERIFICADA] Reduzir saídas antigas de ferramentas merece prioridade sobre instalar outro
  sumarizador. Lindenbauer et al. comparam mascaramento de observações e sumarização por LLM
  em agentes de programação. Ambas reduzem custos nos experimentos; a sumarização pode
  acrescentar chamadas e alongar trajetórias. A economia experimental não é uma previsão
  para Opus/Fable atuais. The Complexity Trap (https://arxiv.org/html/2508.21433v3).

  [VERIFICADA] Mais instruções não garantem melhor execução. Gloaguen et al. encontram
  aumento médio de custo superior a 20% e benefícios inconsistentes de arquivos de contexto
  em tarefas de programação. A avaliação se concentra em resolução de tarefas, não em
  preservação de governança ou segurança. Portanto, não justifica remover controles deste
  repo. Evaluating AGENTS.md (https://arxiv.org/html/2602.11988v2).

  [VERIFICADA] Contexto longo pode prejudicar recuperação de informação. Lost in the Middle
  demonstra sensibilidade à posição; Context Rot amplia a investigação de degradação por
  comprimento. Nenhum estabelece "150k" como limite universal para os modelos desta sessão.
  Liu et al. (https://arxiv.org/abs/2307.03172), Chroma
  (https://www.trychroma.com/research/context-rot).

  [VERIFICADA] Compressão e cache precisam ser avaliados juntos. SGLang demonstra
  reutilização de prefixos; CacheBlend exige mecanismos no servidor para combinar caches de
  trechos. CAPC, preprint de julho de 2026, investiga como compressões diferentes por
  consulta podem destruir reutilização. Não são funcionalidades que um hook local consegue
  adicionar ao servidor da assinatura. SGLang (https://arxiv.org/abs/2312.07104), CacheBlend
  (https://arxiv.org/abs/2405.16444), CAPC (https://arxiv.org/abs/2607.15516).

  [VERIFICADA] Roteamento e tentativas adicionais precisam de seleção confiável. FrugalGPT e
  RouteLLM demonstram economia em seus conjuntos de avaliação. Large Language Monkeys mostra
  a importância de verificadores para transformar múltiplas tentativas em soluções
  aproveitáveis; votação e seleção imperfeitas limitam o ganho. FrugalGPT
  (https://arxiv.org/abs/2305.05176), RouteLLM (https://arxiv.org/abs/2406.18665v4), Brown
  et al. (https://arxiv.org/abs/2407.21787).

  [VERIFICADA] Há literatura aplicável ao agendamento. VTC considera custos variáveis por
  tokens; HiveMind combina admissão, prioridades e reação a congestionamento. A avaliação
  principal do HiveMind usa servidor simulado: seus percentuais não devem virar promessa
  operacional. VTC (https://arxiv.org/abs/2401.00588v2), HiveMind
  (https://arxiv.org/html/2604.17111v1).

  [VERIFICADA] MAST oferece categorias úteis para localizar desperdício: repetição, falhas
  de término, desalinhamento e problemas de verificação. Não fornece diretamente uma
  porcentagem recuperável da quota. MAST (https://arxiv.org/html/2503.13657v3).

  C. Documentação e engenharia: correções relevantes

  [VERIFICADA] O diagnóstico sobre herança de modelo precisa ser atualizado. A documentação
  registra, desde 2.1.251, precedência do modelo por chamada sobre frontmatter e variável de
  ambiente; CLAUDE_CODE_SUBAGENT_MODEL=inherit equivale a deixá-la indefinida. Isso deve ser
  confirmado pelo modelo registrado nas respostas, não pela intenção do despacho. Subagentes
  (https://code.claude.com/docs/en/sub-agents).

  [VERIFICADA] Workflows atuais podem compartilhar prefixos entre agentes compatíveis. A
  documentação descreve inclusive uma espera inicial de até cinco segundos para aproveitar o
  cache do primeiro agente. Também mantém resultados intermediários nas variáveis do
  workflow, fora do contexto principal. Portanto, Workflow pode ajudar a controlar contexto
  quando bem utilizado. Workflows (https://code.claude.com/docs/en/workflows).

  [VERIFICADA] TTL e invalidação não são universais. O padrão documentado diferencia
  conversa principal e subagentes; Fable 5.1 preserva cache ao mudar effort em
  assinatura/API desde 2.1.260, com exceções documentadas. "Nunca mudar effort" é uma regra
  excessiva. Prompt caching no Claude Code (https://code.claude.com/docs/en/prompt-caching).

  [VERIFICADA] No Codex, as lições transferíveis são isolamento e limites explícitos. A
  documentação expõe model_auto_compact_token_limit, tool_output_token_limit e
  agents.max_concurrent_threads_per_session. Subagentes isolam exploração, mas aumentam
  consumo total quando acrescentam trabalho. Isso não demonstra superioridade de custo sobre
  Claude. Configuração (https://learn.chatgpt.com/docs/config-file/config-reference),
  Subagentes (https://learn.chatgpt.com/docs/agent-configuration/subagents).

  [VERIFICADA] ccusage oferece uma conferência externa dos JSONL. Para o framework, eu
  preservaria o coletor stdlib existente, sem introduzir dependência de runtime.
  Documentação (https://ccusage.com/guide/).

  D. Respostas específicas

  1. Como a quota pondera tokens?

  [NÃO VERIFICADA] Não encontrei fórmula pública que converta input, cache read, cache write
  e output em percentual Max. A documentação confirma limites e diferenças de consumo por
  modelo, sem publicar os coeficientes. O limite semanal é descrito como ciclo com horário
  fixo de reset. Max (https://support.claude.com/en/articles/11049741-what-is-the-max-plan),
  Fable nos planos
  (https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan).

  [VERIFICADA] Existe uma fonte nativa para observar a quota: rate_limits.five_hour e
  rate_limits.seven_day, com used_percentage e resets_at, no JSON da statusline. O repo já
  os lê em .claude/scripts/statusline-ceo.py:424. Contrato oficial
  (https://code.claude.com/docs/en/statusline).

  [INFERÊNCIA] Experimento econômico: primeiro correlacionar passivamente esses dados com os
  JSONL. Se insuficiente, usar uma conta, versão/modelo fixos e ausência de consumo
  concorrente; alternar pequenos blocos comparáveis com prefixo quente/frio e output curto.
  Separadamente, variar output. Medir atraso/arredondamento da quota e reportar intervalos.
  Isso estima relações locais; não revela uma fórmula universal.

  2. Modelo de trabalho útil por janela

  [INFERÊNCIA] Para um lote com (n) agentes:

  [
  T_n \approx n,t_n(B+\bar H_n+\bar O_n)+K_n
  ]

  Aqui, (B) é prefixo, (H) histórico médio, (O) output, (t) chamadas por agente e (K)
  coordenação/revisão/retrabalho.

  A quota exige pesos próprios, desconhecidos:

  [
  q_n=\sum(a_m I+b_m W_{5m}+c_m W_{1h}+d_m R+e_m O)+q_{\mathrm{coord}}
  ]

  Com (u_n) entregas aprovadas por lote, duração (L_n) e saldo (Q):

  [
  U_n \approx u_n\min\left(\frac{Q}{q_n},\frac{5h}{L_n}\right)
  ]

  [INFERÊNCIA] Quando quota é o limitante, sete agentes pioram o resultado em relação a dois
  se
  [
  q_7/q_2 > u_7/u_2.
  ]

  Sete tarefas independentes, com o mesmo custo por entrega, podem terminar antes sem perder
  eficiência. Sete agentes repetindo investigação para a mesma entrega podem consumir mais
  sem ganho proporcional.

  [INFERÊNCIA] Exemplo puramente ilustrativo: sete agentes × dez chamadas ×150k =10,5
  milhões de tokens de contexto. Reduzir o prefixo hipotético de97k para20k, mantendo53k de
  histórico, reduz para5,11 milhões. É uma economia de51%, se esses componentes forem
  realmente observados; não é previsão para este repo.

  3. Controles nativos

  [VERIFICADA] A tabela descreve controles documentados em 17/09; não executei testes de
  comportamento na instalação local.

   Controle                        Nome e configuração           Limite relevante
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Auto-compactação                /autocompact 200k; setting    Limiar precisa deixar
                                   autoCompactWindow; flag       espaço acima do contexto
                                   --autocompact; env            indispensável. Fonte
                                   CLAUDE_CODE_AUTO_COMPACT_W    (https://code.claude.com/
                                   INDOW                         docs/en/model-config)
  ──────────────────────────────  ────────────────────────────  ────────────────────────────
   Modelo, ferramentas, turnos     Frontmatter .claude/          Limitar turnos pode
                                   agents/*.md: model,           devolver trabalho parcial.
                                   effort, tools,                Fonte (https://
                                   disallowedTools, maxTurns     code.claude.com/docs/en/
                                                                 sub-agents)
  ──────────────────────────────  ────────────────────────────  ────────────────────────────
   Contexto de subagente           omitClaudeMd: true,           Omite arquivos CLAUDE.md
                                   desde2.1.271                  conforme escopo
                                                                 documentado. Fonte
                                                                 (https://code.claude.com/
                                                                 docs/en/sub-agents)
  ──────────────────────────────  ────────────────────────────  ────────────────────────────
   Concorrência Agent              Env                           Não controla Workflow; há
                                   CLAUDE_CODE_MAX_CONCURRENT    exceções para retomadas/
                                   _SUBAGENTS                    forks. Fonte (https://
                                                                 code.claude.com/docs/en/
                                                                 sub-agents)
  ──────────────────────────────  ────────────────────────────  ────────────────────────────
   Tamanho do Workflow             Setting                       É orientação, não teto
                                   workflowSizeGuideline         rígido. Fonte (https://
                                                                 code.claude.com/docs/en/
                                                                 workflows)
  ──────────────────────────────  ────────────────────────────  ────────────────────────────
   Saída Bash/MCP                  bashOutputMaxChars ou env     Unidades e exceções
                                   BASH_MAX_OUTPUT_LENGTH;       variam. Fonte (https://
                                   MAX_MCP_OUTPUT_TOKENS         code.claude.com/docs/en/
                                                                 env-vars)
  ──────────────────────────────  ────────────────────────────  ────────────────────────────
   Substituir resultado de tool    PostToolUse →                 Precisa preservar o
                                   hookSpecificOutput.updated    formato exigido;
                                   ToolOutput                    additionalContext
                                                                 acrescenta conteúdo. Fonte
                                                                 (https://code.claude.com/
                                                                 docs/en/hooks)
  ──────────────────────────────  ────────────────────────────  ────────────────────────────
   TTL                             Settings promptCacheTtl,      TTL maior tem custo de
                                   subagentPromptCacheTtl        escrita diferente. Fonte
                                                                 (https://code.claude.com/
                                                                 docs/en/prompt-caching)
  ──────────────────────────────  ────────────────────────────  ────────────────────────────
   Execução agendada nova          Agendamento Desktop cria      Sessão nova ainda carrega
                                   sessão nova; /loop usa a      seu contexto inicial.
                                   conversa atual                Desktop (https://
                                                                 code.claude.com/docs/en/
                                                                 desktop-scheduled-
                                                                 tasks), /loop (https://
                                                                 code.claude.com/docs/en/
                                                                 scheduled-tasks)

  [INFERÊNCIA] Neste framework, omitClaudeMd só deve entrar após definir um contrato mínimo
  por função que preserve as obrigações aplicáveis. Economizar apagando instruções de
  segurança não satisfaz o objetivo.

  [NÃO VERIFICADA] Não encontrei um controle nativo que garanta simultaneamente orçamento
  global Max, contexto total≤5k e conclusão de todas as tarefas.

  4. Scheduler ciente da quota

  [INFERÊNCIA] Eu faria um controlador local, sem LLM, com:

  - Saldo/reset da statusline e estimativa conservadora de consumo por classe de tarefa.
  - Reserva para trabalhos já admitidos e para sua revisão/conclusão.
  - Prioridade por dependência, urgência e tempo de espera.
  - Admissão somente quando saldo menos reservas cobre o consumo previsto e uma margem.
  - Checkpoints, tentativas limitadas e espera até o reset; sem rotação de contas.

  [INFERÊNCIA] Token bucket serve como mecanismo de controle, mas não devemos presumir que
  Max repõe saldo continuamente. O controlador deve acompanhar os resets observados. Campos
  ausentes significam desconhecimento, não saldo livre.

  [VERIFICADA] Usage credits são a alternativa oficial para continuar além do plano, com
  cobrança API e limite de gasto configurável. Documentação
  (https://support.claude.com/en/articles/12429409-manage-usage-credits-for-paid-claude-plans).

  [INFERÊNCIA] Overflow para API exigiria orçamento previamente definido e handoff limitado
  ao necessário, mantendo Opus/Fable no perímetro financeiro. Enfileirar pode evitar
  bloqueio abrupto, mas a espera continua existindo: deve entrar na métrica de entrega.

  5. Heartbeat

  [INFERÊNCIA] Redesenho: script determinístico verifica mudança; arquivo de estado guarda
  revisão, cursor e tarefas pendentes; trava evita duplicidade; somente eventos relevantes
  acordam uma sessão curta. Uma verificação periódica barata recupera eventos perdidos.

  [INFERÊNCIA] Sem mudança: zero chamada de modelo. Para triagem não financeira, uma chamada
  Haiku com5k tokens totais de entrada e500 de saída custaria aproximadamente US$0,0075, ou
  US$0,00875 se toda a entrada fosse escrita em cache de5min. Os preços vêm da tabela
  oficial (https://platform.claude.com/docs/en/about-claude/pricing).

  [INFERÊNCIA] Comparado aos865,3k reportados, esse cenário reduz tokens por execução
  em99,4%. O requisito é5k incluindo sistema, ferramentas e instruções; um prompt de usuário
  pequeno dentro de um boot enorme não atende. Código e decisões financeiras continuam no
  modelo e revisão exigidos.

  6. Várias contas

  [VERIFICADA] Os termos proíbem compartilhar credenciais e contornar sistemas ou medidas de
  proteção. Não encontrei nessa cláusula uma proibição literal de simplesmente possuir
  várias contas. Termos, §§2–3 (https://www.anthropic.com/legal/consumer-terms).

  [INFERÊNCIA] Rotacioná-las para superar limites merece esclarecimento escrito do
  fornecedor. Não há base aqui para afirmar banimento certo ou reconhecer padrões internos
  de detecção. A alternativa defensável é capacidade autorizada, créditos/API com orçamento
  e nenhuma automação de alternância.

  E. Crítica à ordem do estudo

  [INFERÊNCIA] Eu reorganizaria as cinco frentes:

  1. Validar o inventário existente e definir entrega aprovada, defeitos, retrabalho e tempo
     de espera.

  2. Reconciliar coletor JSONL, preços por data/TTL e quota observada.
  3. Testar contexto inicial, saídas de ferramentas e continuidade entre tarefas.
  4. Comparar roteamento e concorrência sob orçamento e qualidade equivalentes.
  5. Dimensionar scheduler e capacidade paga com a demanda restante.

  [INFERÊNCIA] Literatura deve orientar esses experimentos, não virar uma etapa extensa
  depois deles. Falta ao plano uma avaliação explícita de qualidade e governança. Sem ela,
  cortar tokens pode apenas transferir custo para correções futuras.

  F. Recomendações e primeira semana

  [INFERÊNCIA] Impactos abaixo são cenários condicionais, não economias medidas; não devem
  ser somados.

   Alavanca            Validar medição existente
   Tokens processados  Sem redução direta
   Bloqueios de quota  Permite previsão
   Esforço             Baixo
   Evidência / risco   Código presente; risco de dupla contagem/atribuição
  ──────────────────────────────────────────────────────────────────────────────────────────
   Alavanca            Reduzir contexto médio
   Tokens processados  Metade do contexto elegível economiza metade dessa parcela
   Bloqueios de quota  Depende dos pesos Max
   Esforço             Médio
   Evidência / risco   Literatura e aritmética; risco de perder informação
  ──────────────────────────────────────────────────────────────────────────────────────────
   Alavanca            Enxugar boot por função
   Tokens processados  Cenário97k→20k:77k por chamada elegível
   Bloqueios de quota  A medir
   Esforço             Médio/alto
   Evidência / risco   Piso não isolado; preservar contratos
  ──────────────────────────────────────────────────────────────────────────────────────────
   Alavanca            Limitar resultados de tools
   Tokens processados  Se40% do contexto for ruído e metade sair:20% nessa população
   Bloqueios de quota  A medir
   Esforço             Baixo/médio
   Evidência / risco   Evidência experimental; manter logs completos acessíveis
  ──────────────────────────────────────────────────────────────────────────────────────────
   Alavanca            Heartbeat orientado a evento
   Tokens processados  ≈99% por execução no cenário;≈4% global se48/dia
   Bloqueios de quota  Parcial
   Esforço             Baixo/médio
   Evidência / risco   Dados fornecidos; risco de perder eventos
  ──────────────────────────────────────────────────────────────────────────────────────────
   Alavanca            Roteamento fora do financeiro
   Tokens processados  Pode até aumentar tokens
   Bloqueios de quota  A medir por modelo
   Esforço             Médio
   Evidência / risco   Cascatas exigem verificação e controle de tentativas
  ──────────────────────────────────────────────────────────────────────────────────────────
   Alavanca            Concorrência adaptativa
   Tokens processados  Nenhuma economia automática
   Bloqueios de quota  Evita saturação prematura
   Esforço             Médio
   Evidência / risco   Precisa medir entregas e espera

  [INFERÊNCIA] Cinco ações para a primeira semana:

  1. Auditar amostra do ledger: conferir sessões principais/subagentes, deduplicação,
     modelos e TTL; registrar cobertura e divergências.

  2. Ligar quota a resultado: percentual consumido por entrega aceita, duração, retrabalho e
     defeitos; separar projetos.

  3. Testar contexto enxuto: saídas limitadas e handoff com objetivo, decisões, arquivos e
     verificações; comparar tarefas equivalentes.

  4. Substituir heartbeat ocioso: medir chamadas sem mudança, tokens por evento e eventos
     perdidos.

  5. Comparar1/3/7 agentes e roteamento permitido: mesmo conjunto de tarefas, orçamento,
     testes e revisão; escolher por entrega aceita e tempo total.

  [INFERÊNCIA] Critério de êxito: redução de pelo menos um terço dos tokens em trabalho
  comparável, com entregas e qualidade preservadas. Redução de bloqueios precisa ser
  demonstrada separadamente.

  Fontes consultadas

  Todas abaixo foram abertas em17/09/2026. Datas de artigos distinguem publicação inicial e
  revisão quando relevante; documentação contínua usa a data de acesso.

   Título / fonte      Autores ou órgão       Data                         O que sustenta
  ━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━
   Towards a           Kim et al.             09/12/2025;                  Dependência
   Science of                                 rev.08/04/2026               entre
   Scaling Agent                                                           arquitetura,
   Systems —                                                               tarefa e
   2512.08296v3                                                            orçamento
   (https://
   arxiv.org/
   abs/2512.08296v3
   )
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   The Complexity      Lindenbauer et al.     29/08/2025;                  Mascaramento
   Trap —                                     rev.27/10/2025               versus
   2508.21433v3                                                            sumarização
   (https://
   arxiv.org/
   html/2508.21433v
   3)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Evaluating          Gloaguen et al.        12/02/2026;                  Custos e efeitos
   AGENTS.md —                                rev.23/06/2026               de arquivos de
   2602.11988v2                                                            contexto
   (https://
   arxiv.org/
   html/2602.11988v
   2)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Lost in the         Liu et al.             06/07/2023                   Sensibilidade à
   Middle —                                                                posição da
   2307.03172                                                              informação
   (https://
   arxiv.org/
   abs/2307.03172)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Context Rot         Hong, Troynikov,       14/07/2025                   Avaliação de
   (https://           Huber / Chroma                                      contexto longo;
   www.trychroma.co                                                        estudo de
   m/research/                                                             engenharia
   context-rot)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   SGLang —            Zheng et al.           12/12/2023;                  Reuso de KV-
   2312.07104                                 rev.06/06/2024               cache por
   (https://                                                               prefixos
   arxiv.org/
   abs/2312.07104)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   CacheBlend —        Yao et al.             26/05/2024;                  Fusão de caches
   2405.16444                                 rev.03/04/2025               com recomputação
   (https://                                                               seletiva
   arxiv.org/
   abs/2405.16444)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Cache-Aware         Yan Song               17/07/2026                   Interação entre
   Prompt                                                                  compressão e
   Compression —                                                           cache; preprint
   2607.15516
   (https://
   arxiv.org/
   abs/2607.15516)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   FrugalGPT —         Chen, Zaharia, Zou     09/05/2023                   Cascatas
   2305.05176                                                              orientadas a
   (https://                                                               custo/qualidade
   arxiv.org/
   abs/2305.05176)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   RouteLLM —          Ong et al.             26/06/2024;                  Roteamento
   2406.18665v4                               rev.23/02/2025               aprendido
   (https://
   arxiv.org/
   abs/2406.18665v4
   )
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Large Language      Brown et al.           31/07/2024;                  Tentativas
   Monkeys —                                  rev.30/12/2024               adicionais e
   2407.21787                                                              seleção/
   (https://                                                               verificação
   arxiv.org/
   abs/2407.21787)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Fairness in         Sheng et al.           31/12/2023;                  Agendamento por
   Serving LLMs —                             rev.05/06/2024               custo variável
   2401.00588v2
   (https://
   arxiv.org/
   abs/2401.00588v2
   )
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   HiveMind —          Agyemang et al.        18/04/2026                   Admissão,
   2604.17111                                                              prioridades,
   (https://                                                               retries;
   arxiv.org/                                                              avaliação
   html/2604.17111v                                                        principalmente
   1)                                                                      simulada
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Why Do Multi-       Cemri et al.           17/03/2025;                  Taxonomia MAST
   Agent LLM                                  rev.26/10/2025
   Systems Fail? —
   2503.13657v3
   (https://
   arxiv.org/
   html/2503.13657v
   3)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Multi-agent         Anthropic              13/06/2025                   Origem e escopo
   research system                                                         dos
   (https://                                                               multiplicadores4
   www.anthropic.co                                                        ×/15×
   m/engineering/
   multi-agent-
   research-system)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Effective           Anthropic              29/09/2025                   Compactação,
   context                                                                 notas
   engineering                                                             persistentes e
   (https://                                                               recuperação sob
   www.anthropic.co                                                        demanda
   m/engineering/
   effective-
   context-
   engineering-for-
   ai-agents)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Caching da API      Anthropic              Acesso17/09/2026             Categorias de
   (https://                                                               tokens e preços
   platform.claude.                                                        por modelo/TTL
   com/docs/en/
   build-with-
   claude/prompt-
   caching) e
   preços (https://
   platform.claude.
   com/docs/en/
   about-claude/
   pricing)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Caching do Code     Anthropic              Acesso17/09/2026             Invalidação, TTL
   (https://                                                               e compactação
   code.claude.com/
   docs/en/prompt-
   caching) e
   modelos
   (https://
   code.claude.com/
   docs/en/model-
   config)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Subagentes          Anthropic              Acesso17/09/2026             Contexto,
   (https://                                                               precedência,
   code.claude.com/                                                        concorrência e
   docs/en/sub-                                                            cache
   agents) e                                                               compartilhado
   workflows
   (https://
   code.claude.com/
   docs/en/
   workflows)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Variáveis           Anthropic              Acesso17/09/2026             Limites e
   (https://                                                               substituição de
   code.claude.com/                                                        resultados
   docs/en/env-
   vars) e hooks
   (https://
   code.claude.com/
   docs/en/hooks)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Statusline          Anthropic              Acesso17/09/2026             Quota observada
   (https://                                                               e métricas
   code.claude.com/                                                        nativas
   docs/en/
   statusline) e
   monitoramento
   (https://
   code.claude.com/
   docs/en/
   monitoring-
   usage)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Agendamento CLI     Anthropic              Acesso17/09/2026             Conversa
   (https://                                                               existente versus
   code.claude.com/                                                        sessão nova
   docs/en/
   scheduled-tasks)
   e Desktop
   (https://
   code.claude.com/
   docs/en/desktop-
   scheduled-tasks)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Max (https://       Anthropic              Acesso17/09/2026             Limites,
   support.claude.c                                                        diferenças de
   om/en/                                                                  consumo e
   articles/1104974                                                        capacidade
   1-what-is-the-                                                          adicional
   max-plan), Fable
   (https://
   support.claude.c
   om/en/
   articles/1542496
   4-claude-fable-
   models-on-your-
   plan), créditos
   (https://
   support.claude.c
   om/en/
   articles/1242940
   9-manage-usage-
   credits-for-
   paid-claude-
   plans)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Consumer Terms      Anthropic              Vigência08/10/2025           Credenciais e
   (https://                                                               medidas de
   www.anthropic.co                                                        proteção
   m/legal/
   consumer-terms)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   Configuração        OpenAI                 Acesso17/09/2026             Controles de
   Codex (https://                                                         contexto e
   learn.chatgpt.co                                                        delegação
   m/docs/config-
   file/config-
   reference) e
   subagentes
   (https://
   learn.chatgpt.co
   m/docs/agent-
   configuration/
   subagents)
  ──────────────────  ─────────────────────  ───────────────────────────  ──────────────────
   ccusage             Projeto ccusage        Acesso17/09/2026             Conferência
   (https://                                                               local de consumo
   ccusage.com/                                                            em JSONL
   guide/)

  G. O que eu faria diferente do primeiro revisor

  [INFERÊNCIA] Concordo com reduzir contexto desnecessário, retirar polling do LLM e
  preservar modelos fortes no perímetro financeiro. Discordo de transformar hipóteses em
  causas já demonstradas.

  Eu começaria pelo coletor que já existe; verificaria o modelo realmente executado;
  separaria tamanho do contexto, custo API e quota; substituiria "sessão nova sempre" por
  continuidade delimitada por tarefa; e testaria concorrência antes de impor2–3 agentes.

  [INFERÊNCIA] Também reservaria orçamento para revisão antes de iniciar autoria. A
  configuração desejável é aquela que conclui trabalho verificado com contexto suficiente e
  pouca repetição. Hoje há evidência para experimentar essas mudanças, mas ainda não para
  prometer economia de33%, ausência de bloqueios ou vantagem geral de velocidade do
  framework.
