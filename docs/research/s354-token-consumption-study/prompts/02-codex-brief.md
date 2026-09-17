# Brief para o Codex — estudo independente: consumo de tokens e quota do Claude Code sob um framework multi-agente

Você é um segundo revisor, de outro fornecedor, chamado para dar uma opinião INDEPENDENTE e para estudar a literatura a fundo. Um agente Claude já fez uma primeira leitura do problema; a sua função é complementar, contradizer onde houver evidência e trazer o que ele não viu. Não repita o que já está escrito. Marque acordo e desacordo de forma explícita. Prefira fontes primárias. Quando não conseguir verificar uma afirmação, diga isso e proponha um experimento que a decida.

## 1. O problema, em uma frase

Um operador solo, com oito frentes de trabalho paralelas (várias com lógica financeira: matching engine, arbitragem, câmbio), usa o Claude Code em regime de «velocidade máxima»: workflows com cerca de 7 agentes em paralelo, sessões que atravessam dias, loops de fundo. Resultado: 96 % dos tokens são releitura de contexto, a janela de 5 horas da assinatura esgota em cerca de 1 hora, e a resposta atual é rotacionar entre 7 contas Max 20x. A meta é manter ou aumentar o output útil por semana reduzindo o total processado em pelo menos um terço, zerar os bloqueios de janela e sair da rotação de contas.

## 2. Dados medidos (16/09/2026, Claude Code CLI, um Mac, todas as contas no mesmo diretório de configuração)

| Métrica | Valor |
|---|---|
| Período | 52 dias (26/07 a 16/09/2026), 199 sessões, 49 dias ativos |
| Total processado | 57,5 bilhões de tokens |
| Cache read / cache write / output / input novo | 96,3 % / 3,3 % / 0,35 % / 0,007 % |
| Tokens processados por token de output | ≈ 283 |
| Modelos (share) | Opus 5 44,8 %, Fable 5 32,3 %, Fable 5.1 20,4 %, resto ≈ 2,5 % |
| Sessão mais longa | 2 dias e 20 horas |
| Sessão de referência que esgotou a janela | 7h44 de tempo de API em 1h09 de relógio (paralelismo 6,7×), ≈ 631 mi de tokens, US$ 269 API-equivalente |
| Contexto da thread principal nessa sessão | ≈ 600k tokens (8 cache misses re-cachearam 4,9 mi) |
| Causas de miss apontadas pela ferramenta | troca de modelo, beta headers, effort, mensagens anteriores alteradas; TTL do cache 1 h |
| Perfil das últimas 24 h | 99 % sessões com subagentes; 95 % contexto > 150k; 85 % sessões ativas há 8 h+; 85 % dos subagentes vêm da Workflow tool |
| Loop de fundo (outro projeto, mesmo diretório) | 865k tokens por execução, 2× por hora |
| Limites na conta observada | janela de 5 h em 100 %; semana em 16 %; semana Fable em 4 % |
| Equivalente-API estimado | ≈ US$ 14 mil por mês (piso), sobre US$ 1.400 de assinatura |

Preços inferidos dos custos exibidos (a confirmar): Sonnet 5 input 2 / output 10 / cache read 0,20 / cache write 2,50 US$ por milhão; Opus 5 input 5 / output 25 / cache read 0,50 / cache write 6,25. Fable não inferível.

## 3. Como o trabalho é feito hoje (fatos verificados no repositório em 16/09)

- Framework `ceo-orchestration`: uma sessão principal («CEO») despacha especialistas via Agent tool e Workflow tool; governança por 48 hooks Python em cerca de 100 registrações; pair-rail cross-model (você, Codex, revisa edições canônicas); debate estruturado para mudanças arriscadas; cerimônias com assinatura GPG.
- Boot obrigatório de toda sessão: 191 KB em cinco arquivos de contrato, mais 17,8 KB de memória. O piso re-pago a cada compactação foi MEDIDO em ≈ 97k tokens (spread de 51,7 % em n=41); thrashing de compactação a partir de ≈ 107k. A meta «≤ 150k na thread principal» deixaria ≈ 50k de trabalho útil se o boot não encolher.
- Subagentes herdam o modelo da sessão (variável `CLAUDE_CODE_SUBAGENT_MODEL=inherit`); o parâmetro de modelo por chamada da Workflow tool foi registrado como inerte. Das 13 definições de agente, 9 fixam modelo, mas em gerações anteriores; nenhuma usa Haiku 4.5 ou Sonnet 5. Existe um script pronto que torna o modelo explícito em toda chamada de agente dos workflows; nunca foi aplicado.
- Instrumentos de custo existentes são todos advisory, leem um audit-log próprio e nenhum mede cache read, contexto por request ou consumo da janela de 5 h.
- O próprio repositório registra: seis experimentos internos não encontraram ganho geral de velocidade do multi-agente sobre um fluxo solo otimizado, e um run medido teve 59 % de tempo morto esperando revisão e correção, não autoria. Um estudo anterior (02/09/2026) já anotou a medição da Anthropic de que multi-agente custa ≈ 15× um chat simples, a lista de quando NÃO usar multi-agente, e marcou como lacuna a heurística «esta tarefa vale o multiplicador?».

## 4. Hipótese do primeiro revisor (para você atacar)

«Paralelismo compra tempo de relógio com quota a uma taxa ruim, na parte do trabalho que não é o gargalo, enquanto cada agente carrega um prefixo fixo pesado e relê o contexto inteiro a cada turno.» Alavancas propostas, em ordem de retorno por esforço: (1) sessão por tarefa, modelo e effort fixos, loop de fundo em sessão nova com modelo barato; (2) paralelizar só trabalho independente, teto de 2 a 3 agentes, fan-outs logo após o reset da janela, pipeline quando o limite é quota; (3) modelo barato em lanes com verificação automática, Opus/Fable só para veto e para código que toca dinheiro; (4) encolher o boot do framework com divulgação progressiva das instruções; (5) ledger a partir dos JSONL das sessões antes de qualquer outra medida.

## 5. O que eu quero de você

**A. Diagnóstico independente.** Sem partir da hipótese acima: dado o perfil de §2 e §3, o que está errado e em que ordem de grandeza cada causa contribui? Onde a hipótese do primeiro revisor está errada ou incompleta?

**B. Literatura acadêmica, 2023 a 2026, com arXiv/DOI e data.** Estude a fundo, não cite de memória. Temas mínimos:
1. Custo em tokens de sistemas multi-agente versus agente único; quando o paralelismo aumenta o trabalho útil por orçamento fixo e quando o reduz (prefixo duplicado, releitura, coordenação, verificação). Modelos analíticos, não só anedota.
2. Engenharia de contexto: compactação e sumarização guiada, memória externa e handoff por arquivo, truncamento de saídas de ferramentas, degradação em contexto longo («lost in the middle», context rot), divulgação progressiva de instruções, custo do prefixo de sistema.
3. Economia de prompt cache e reuso de KV-cache: o que muda quando o prefixo é estável, o que invalida o cache, TTL e janela de inatividade, cache em cascata para agentes com prefixo comum.
4. Roteamento e cascatas de modelos com verificação automática (FrugalGPT, RouteLLM, cascatas por dificuldade, custo de self-consistency), e como respeitar um piso de correção para código financeiro.
5. Controle de admissão e agendamento sob rate limit para APIs de LLM: token bucket, filas com prioridade, previsão de consumo, disparo pós-reset. Há literatura de sistemas aplicável?
6. Loops e heartbeats em agentes: polling versus orientado a evento, custo de acordar um agente com contexto vazio versus dentro de uma sessão viva.
7. Taxonomias de falha e de desperdício em sistemas multi-agente (por exemplo MAST) que apontem desperdício de tokens como classe.

**C. Fontes de engenharia e documentação primária.** Anthropic: prompt caching, custos e monitoramento do Claude Code, subagentes, hooks, compactação, limites de uso da assinatura. OpenAI: como o PRÓPRIO Codex gerencia contexto, compactação, subagentes e custo; quais lições transferem. Ferramentas de terceiros que leem os JSONL locais para estimar consumo. Para cada fonte, data e o que ela prova.

**D. Perguntas específicas.**
1. Como a quota de assinatura (janela de 5 h e semanal) pondera cache read versus input versus output? Só fontes públicas. Se não estiver documentado, diga isso e desenhe o experimento mais barato que decida.
2. Escreva um modelo simples de «trabalho útil por janela» em função do número de agentes, do tamanho do prefixo por agente, do contexto médio por turno e do número de turnos. Mostre para que valores dos dados de §2 o paralelismo passa a diminuir o trabalho útil.
3. Que controles NATIVOS do Claude Code impõem higiene de contexto automaticamente (limiar de auto-compact, modelo por agente, allowlist de ferramentas, truncamento de saídas, sessão nova por execução agendada)? Nome exato, onde configurar, fonte. O que não existe, diga que não existe.
4. Desenho de um scheduler ciente da janela de 5 h: fonte da estimativa, fila, throttling, overflow para API paga em vez de outra assinatura.
5. Redesenho do loop de fundo: arquivo de estado, acordar por mudança, sessão nova, modelo barato, prompt ≤ 5k tokens. Custo projetado por execução.
6. Conformidade do uso de várias contas: só fontes primárias (termos de uso, política de uso). Não aconselhe contorno de nenhuma regra; se a configuração for arriscada, diga e proponha a alternativa defensável.

**E. Crítica ao plano do primeiro revisor.** O estudo proposto tem cinco lanes: instrumentação a partir dos JSONL primeiro, depois controles nativos do substrato, depois roteamento por classe de tarefa, depois literatura como delta sobre o estudo de 02/09, depois conformidade e custo por cenário. A ordem está certa? Falta lane? Alguma é desperdício?

**F. Recomendações.** Tabela alavanca × impacto estimado em tokens processados e em bloqueios de janela × esforço × evidência × risco. Depois, as cinco ações de maior retorno para a primeira semana, com o que medir para saber se funcionaram.

**G. Lista de desacordos.** Onde você discorda do primeiro revisor, com a evidência. Esta seção é a razão de você ter sido chamado; não a deixe vazia por cortesia.

## 6. Restrições que valem para toda a resposta

- R1. Código que toca ordem, saldo, liquidação ou câmbio fica em Opus ou Fable. Nenhuma alavanca de custo rebaixa modelo nesse perímetro.
- R2. Nada que toque produção financeira é mergeado ou deployado por pipeline noturno sem testes e revisão.
- R3. Nenhuma solução pode depender de alternar contas automaticamente.
- R4. Otimização que reduz tokens reduzindo entrega não conta.
- R5. Nada que envolva disponibilizar conta ou credencial a terceiros ou a serviços externos.
- Toda afirmação medida carrega data e substrato (versão da CLI, modelo, ambiente). Benchmarks de junho de 2026 são de outra geração de modelo.
- Não confie no número «3,53× de throughput e 44 % de redução de custo» que circula sobre o framework: o registro do repositório diz o oposto. Trate como não verificado.
- Distinga dólar API-equivalente de quota de assinatura. A decisão real do operador é de quota.
- Rotule cada afirmação: `[VERIFICADA]` com fonte aberta, `[NÃO VERIFICADA]` quando a fonte não pôde ser aberta, `[INFERÊNCIA]` quando é raciocínio seu.

## 7. Formato de saída

Markdown em português, pronto para virar o arquivo `02-codex-opinion.md` de um diretório de estudo. Até cerca de 3.000 palavras de corpo, mais uma tabela de fontes ao final (título, autores ou órgão, data, URL ou arXiv/DOI, o que prova). Uma seção por letra de §5. Cada afirmação com fonte e rótulo. Termine com a seção «O que eu faria diferente do primeiro revisor».

## 8. Se você tiver acesso ao repositório

Leia, sem editar nada: `docs/research/s354-token-consumption-study/01-work-order-2026-09-16.md` (a ordem de trabalho completa, com fontes), `docs/research/s354-token-consumption-study/README.md` (os oito fatos do primeiro revisor), `docs/research/s339-orchestrator-study/01-academia.md` e `05-finops-routing.md` (o estudo anterior, para não repetir), o frontmatter de `.claude/agents/*.md`, e a seção 5 de `CLAUDE.md` (as medições de piso e thrashing). Se não tiver acesso, use só este brief.
