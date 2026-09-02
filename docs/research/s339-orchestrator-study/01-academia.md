# Pesquisa acadêmica 2025–2026 — orquestração multi-agente LLM

**Data:** 2026-09-02
**Escopo:** literatura sobre topologia multi-agente, verificação externa vs. auto-correção, roteamento por custo/dificuldade e escalonamento de effort/thinking budget, avaliada contra a doutrina já registrada em `PROTOCOL.md` (§Debate, §Verification cascade, §Honest limitation) e `docs/HONEST-LIMITATIONS.md` (§4).
**Rótulos:** `[JÁ ADOTADO]` = o repo já implementa isso; `[LACUNA]` = a literatura sugere algo que o repo ainda não tem; `[CONTRADIZ a doutrina atual]` = a literatura questiona uma prática vigente; `[NÃO VERIFICADA]` = fonte não pôde ser aberta.

---

## 1. Topologia — orquestrador–trabalhadores vs. debate vs. mixture/voting

**1.1 Anthropic, "How we built our multi-agent research system"** (anthropic.com/engineering/multi-agent-research-system, jun/2025). O padrão de produção é **orquestrador-trabalhadores**: um agente líder decompõe a query, despacha subagentes que exploram facetas independentes em paralelo com contexto próprio, e sintetiza. Medido: multi-agente supera agente único em **90,2%** numa avaliação interna de pesquisa (Opus líder + Sonnet trabalhadores vs. Opus solo), mas consome **~15× mais tokens** que um chat simples (agentes isolados já consomem ~4×), e o uso de token sozinho explica **80%** da variância de performance em avaliações de busca. A Anthropic lista explicitamente QUANDO NÃO usar multi-agente: tarefas que exigem contexto compartilhado por todos os agentes, alta interdependência entre passos, baixo potencial de paralelização (ex.: coding na maior parte dos casos) e tarefas de baixo valor econômico que não justificam o custo extra.
`[JÁ ADOTADO]` parcial — o CEO já opera como orquestrador de especialistas com FILE ASSIGNMENT anti-colisão (`PROTOCOL.md` Step 0, "0 arquivos em comum → paralelo sem worktree", "4+ arquivos em comum → não paralelizar"). `[LACUNA]`: essa regra é só sobre SOBREPOSIÇÃO DE ARQUIVOS, não sobre ESTRUTURA DA TAREFA (interdependência sequencial, contexto compartilhado, valor econômico) nem sobre o multiplicador de custo em tokens — o repo não tem uma heurística "esta tarefa é decomponível o suficiente para valer o overhead de 4-15×".
**Implicação:** antes de despachar 2+ agentes em paralelo, o CEO deveria perguntar explicitamente "as subtarefas são independentes o bastante, e o valor da tarefa justifica o multiplicador de tokens?" — não só "os arquivos colidem?".

**1.2 Cemri et al., "Why Do Multi-Agent LLM Systems Fail?" — MAST** (arXiv:2503.13657, v1 mar/2025, v3 out/2025). Taxonomia de 14 modos de falha (kappa=0,88 com anotadores humanos, 1600+ traces, 7 frameworks) em 3 categorias: (i) problemas de design de sistema, (ii) desalinhamento inter-agente, (iii) **verificação de tarefa** (terminação prematura, verificação incompleta/ausente). A categoria (iii) é apontada como a mais tratável mecanicamente.
`[JÁ ADOTADO]` — a categoria "verificação de tarefa" da MAST casa quase literalmente com o design do repo: ADR-186 já trata timeout do matcher canônico como **fail-CLOSED por ser "uma verificação incompleta, não infraestrutura"**, exatamente o antipadrão "verificação incompleta" que MAST cataloga. O V0-V3 (`PROTOCOL.md` §Verification cascade) também é uma resposta estrutural às categorias (ii) e (iii): nenhuma etapa autoriza shipping sozinha.
**Implicação:** citar MAST explicitamente no PROTOCOL.md como base para as categorias de falha que V0-V3 e ADR-186 mitigam fortalece a rastreabilidade da doutrina — mas as categorias (i) "design de sistema" (ex.: papéis mal definidos, perda de contexto entre agentes) não têm um gate mecânico dedicado hoje.

**1.3 Kim et al., "Towards a Science of Scaling Agent Systems"** (arXiv:2512.08296, v1 dez/2025, v3 abr/2026; 19 autores, Stanford/MIT). Estudo multifatorial com 260 configurações, 6 benchmarks, 5 arquiteturas (single-agent + 4 tipos multi-agente), 3 famílias de modelo (R²=0,373 cross-validado). Achado central: o efeito de usar múltiplos agentes é **fortemente dependente da tarefa** — de **+80,8%** em raciocínio financeiro decomponível a **−70,0%** em planejamento sequencial, na mesma família de arquiteturas. Coordenação tem retornos decrescentes uma vez que a baseline single-agent já é forte; arquiteturas sem verificação centralizada propagam erro mais que as centralizadas. Conclusão dos autores: "architecture-task alignment determines collaborative success" — não existe uma topologia universalmente melhor.
`[LACUNA]` — o repo não tem uma regra explícita ligando **tipo de tarefa** (decomponível vs. sequencial/tightly-coupled) à **decisão de paralelizar**. O gate atual (`PROTOCOL.md` Step 0) decide por sobreposição de arquivos, não por dependência lógica entre subtarefas — uma tarefa sequencial com 0 arquivos em comum ainda seria despachada em paralelo hoje, e o achado de Kim et al. sugere que isso pode custar até −70% de performance.
**Implicação:** adicionar ao Step 0 do Spawn Protocol uma pergunta binária "esta tarefa é sequencialmente dependente (a saída de um agente é entrada do outro)?" — se sim, serializar independentemente da sobreposição de arquivos.

**1.4 Debate vs. voting/mixture.** MAST + Kim et al. convergem: debate ajuda quando a tarefa tem "task verification" fraca e agentes com perspectivas genuinamente diferentes; degrada quando a tarefa é sequencial ou quando os agentes compartilham o mesmo viés de treino (ver §2). Não encontrei, na janela de busca, um paper específico 2025-26 comparando debate vs. mixture/voting puro (self-consistency) em produção de forma que renderia uma comparação nova — a doutrina do repo já cobre esse ponto via a distinção V0 (coerência de design) vs. V1-V3 (verdade mecânica/cross-model).

---

## 2. Verificação externa/refutação vs. auto-correção

**2.1 Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet"** (arXiv:2310.01798, ICLR 2024). Achado central: sem feedback externo, LLMs falham em autocorrigir raciocínio — e às vezes a "autocorreção" **piora** a resposta correta original.
`[JÁ ADOTADO]` — é exatamente o fundamento por trás de V2 no `PROTOCOL.md` ("Codex pair-rail — o **único** portão de verdade LLM... fail-closed ao Owner: sem veredito do Codex → escalar, nunca auto-aprovar") e do §Honest limitation ("'Independent review' — um agente revisando o código de outro agente é o mesmo modelo"). O repo nunca permite que Claude aprove seu próprio trabalho como verificação final — está alinhado com esse achado desde a origem do design.
**Implicação:** nenhuma mudança necessária; vale citar 2310.01798 no PROTOCOL.md como a evidência primária por trás de "nunca auto-aprovar", que hoje é afirmado sem citação.

**2.2 FrugalGPT** (arXiv:2305.05176, Chen/Zaharia/Zou, mai/2023) e cascatas de custo. Modelo barato responde primeiro; se a confiança/score é baixa, escala para modelo caro. Resultado: até 98% de redução de custo mantendo a qualidade do melhor modelo isolado, ou +4% de acurácia no mesmo custo.
`[LACUNA]` — o repo tem `llm-finops-architect` e ADR-052/064 para roteamento por tier de modelo, mas não documenta uma **cascata de confiança** (modelo barato tenta primeiro, escala só se o score de confiança for baixo) como mecanismo formal — o roteamento hoje parece ser decidido a priori por tipo de tarefa, não por um sinal de confiança pós-hoc do próprio modelo barato.
**Implicação:** avaliar se o `llm-finops-architect` deveria ganhar um modo "tentativa barata + escalonamento condicionado a confiança" para tarefas L1-L2, reduzindo custo sem abrir mão de qualidade.

**2.3 "Scaling Flaws of Verifier-Guided Search in Mathematical Reasoning"** (arXiv:2502.00271, fev/2025). Achado: verificador guiando busca supera amostragem repetida simples com POUCAS amostras, mas com MUITAS amostras a vantagem desaparece e o verificador **passa a performar pior** que amostragem simples — porque um verificador imperfeito pode podar (eliminar) TODOS os caminhos corretos à medida que o espaço de candidatos cresce. Robusto entre 2 modelos, 2 benchmarks e vários verificadores.
`[CONTRADIZ a doutrina atual]` (parcial, com ressalva de escopo) — o V2 do repo trata o veredito do Codex como "o único portão de verdade LLM", fail-closed. O achado de 2502.00271 não se aplica diretamente (o repo não faz busca sobre N candidatos gerados pelo mesmo modelo, e sim revisão cross-vendor de UM patch canônico já escrito), mas o MECANISMO de risco é o mesmo em espécie: um único verificador, por mais bem desenhado, tem taxa de erro não-zero, e confiar nele como portão único sem um caminho de recuperação para "o verificador errou" é uma fragilidade estrutural, não um bug pontual. O repo já mitiga isso parcialmente (ADR-161: reviewer indisponível → `UNAVAILABLE` + allow-com-ruído, nunca bloqueio infinito nem auto-aprovação silenciosa), mas não tem uma via para "o Codex aprovou, mas errou" além do Owner humano no V3.
**Implicação:** o V3 (cerimônia GPG do Owner) já é a resposta correta a essa classe de erro — vale documentar explicitamente no PROTOCOL.md que V3 existe, entre outras razões, porque nenhum verificador único (nem V2) tem taxa de erro zero, citando 2502.00271 como evidência de que "mais escala não corrige um verificador que pode estar sistematicamente errado".

**2.4 LLM-as-judge: self-preference e verbosity bias** (survey de vários papers: arXiv:2410.21819 "Self-Preference Bias in LLM-as-a-Judge", out/2024; arXiv:2604.23178 "Judging the Judges", 2026; e outros). GPT-4 e modelos similares mostram viés de self-preference mensurável (preferem saídas familiares/baixa perplexidade para si mesmos); verbosity bias favorece respostas mais longas independente de conteúdo em parte dos modelos.
`[JÁ ADOTADO]` parcial — o §Artifact Paradox do PROTOCOL.md já documenta que "outputs polidos recebem ~5,2pp menos escrutínio" (pesquisa de fluência da Anthropic) e prescreve revisar como trabalho júnior, focar no que está ausente. `[LACUNA]`: essa mitigação é aplicada à revisão HUMANA/CEO de saída de sub-agentes, mas não há menção de verbosity/self-preference bias como risco específico do **veredito do próprio pair-rail** (Codex revisando um patch Claude, ou Claude revisando Codex na direção invertida) — um patch mais verboso/bem formatado poderia receber veredito GO mais facilmente por viés de verbosidade do revisor, não por ser mais correto.
**Implicação:** considerar adicionar ao checklist do pair-rail um lembrete explícito de resistir a verbosity bias — patch mais longo/polido não é evidência de correção.

---

## 3. Roteamento por dificuldade/custo em 2026

**3.1 "Is Escalation Worth It? A Decision-Theoretic Characterization of LLM Cascades"** (arXiv:2605.06350, 2026). Formaliza quando escalar de um modelo barato para um caro vale a pena como problema de decisão (custo esperado da escalada vs. ganho esperado de qualidade), não como heurística fixa.
`[LACUNA]` — o repo tem tiers de modelo e ADR-052/064, mas a decisão de escalar (ex.: subir de effort baixo para alto, ou de Sonnet para Opus num spawn) não parece ser modelada como troca explícita de custo-esperado-vs-ganho-esperado; é mais uma classificação estática por tipo de tarefa (L1-L2 vs L3+).
**Implicação:** o gate de blast-radius (L1-L4) já é um proxy grosseiro dessa decisão — formalizar isso com um score de confiança explícito (não só a classe de risco da tarefa) poderia refinar quando vale escalar effort/modelo.

**3.2 ProgRouter — "Online Progress-Guided Orchestration for Multi-Agent LLM Workflows under Quality-Cost Tradeoffs"** (arXiv:2608.25992, 2026). Roteamento passo-a-passo (não decidido de uma vez no início) usando um "scorer" de progresso da tarefa, balanceando ganho de progresso, orçamento de tempo e custo operacional de longo prazo.
`[LACUNA]` — o repo decide o roteamento/effort no MOMENTO DO SPAWN (via `/effort`, arquétipo escolhido, tier de modelo), não dinamicamente enquanto o agente trabalha. Não há um "checkpoint de progresso" que decida se vale continuar no mesmo modelo/effort ou escalar/rebaixar no meio da execução.
**Implicação:** para tarefas longas (spawns de workflow multi-hora), um checkpoint de progresso que reavalia effort/modelo no meio do caminho é uma linha de pesquisa aplicável, mas de custo de implementação alto — baixa prioridade agora.

**3.3 RouteLLM** (arXiv:2406.18665, jun/2024). Roteador aprendido (classificador treinado em dados de preferência humana) decide entre modelo forte/fraco por query; reduz custo em mais de 2× sem perda de qualidade perceptível; generaliza razoavelmente entre pares de modelo.
`[JÁ ADOTADO]` conceitualmente (roteamento por tier existe via `llm-finops-architect`), mas `[LACUNA]` no mecanismo: o roteamento do repo é baseado em REGRAS (classe de tarefa, arquétipo) e não em um classificador aprendido a partir de dados de preferência — o que é uma escolha razoável para um framework auditável (regras são mais explicáveis que um classificador treinado), mas vale nomear essa é uma escolha deliberada de auditabilidade sobre otimização, não uma lacuna cega.
**Implicação:** nenhuma ação — mas vale documentar explicitamente por que o repo prefere roteamento por regra a roteamento aprendido (auditabilidade > otimização marginal de custo), fechando a leitura de "por que não fazer como RouteLLM".

---

## 4. Effort / thinking budget em agentes

**4.1 "Large Language Monkeys: Scaling Inference Compute with Repeated Sampling"** (arXiv:2407.21787, Brown et al., jul/2024). Cobertura (fração de problemas resolvidos por QUALQUER amostra) escala como lei de potência com o número de amostras ao longo de 4 ordens de magnitude — mas isso só converte em ganho real quando existe verificação automática barata (código, prova formal) para escolher a amostra certa; SWE-bench Lite: 15,9% com 1 amostra → 56% com 250 amostras (DeepSeek-V2-Coder).
`[JÁ ADOTADO]` implicitamente — o pair-rail (verificação cross-model barata e automatizável) é o mecanismo que tornaria escalar amostras/tentativas valioso; hoje o repo não faz repeated-sampling explícito de patches, mas a infraestrutura de verificação barata já existe caso quisesse.
**Implicação:** se o custo por sessão continuar sendo um problema, repeated-sampling + o pair-rail já existente como verificador automático é uma via de melhoria de qualidade com custo previsível — não implementado hoje.

**4.2 "When More Thinking Hurts: Overthinking in LLM Test-Time Compute Scaling"** (arXiv:2604.10739, 2026) e "Scaling over Scaling: Exploring Test-Time Scaling Plateau in Large Reasoning Models" (arXiv:2505.20522, 2025). Retornos marginais caem substancialmente em budgets altos de raciocínio, e em budgets muito altos o modelo pode **abandonar uma resposta correta anterior** ("overthinking") — não é monotônico. Existe um platô de escala de teste bem documentado, não um "quanto mais effort, melhor" sem limite.
`[LACUNA]` — o skill `/effort` do repo (PLAN-086/134) escala o thinking effort para o próximo spawn, mas não há, na doutrina lida, um teto documentado ou heurística de "effort alto pode piorar, não só custar mais" — a doutrina trata effort como dial de custo/qualidade monotônico implícito.
**Implicação:** documentar no skill `effort` (ou no PROTOCOL.md) que effort máximo não é estritamente dominante — para tarefas já bem especificadas, um effort excessivo pode fazer o modelo abandonar um raciocínio correto por "overthinking"; a escolha de effort deveria ser calibrada por complexidade real da tarefa, não "sempre o mais alto para segurança".

**4.3 "Steering LLM Thinking with Budget Guidance"** (arXiv:2506.13752, 2026). "Budget forcing" (corte rígido de tokens de raciocínio) é inferior a "budget guidance" (orientação suave que direciona o modelo a concluir dentro do orçamento sem cortar abruptamente) — budget guidance mantém acurácia melhor no mesmo comprimento médio de raciocínio.
`[NÃO VERIFICADA]` quanto a aplicabilidade direta ao mecanismo de effort da Claude API (que usa budgets de thinking tokens nativos, não necessariamente o mesmo mecanismo estudado no paper, que usa modelos open-weight). Não consegui confirmar que a técnica de "budget guidance" (que exige acesso a logits/steering interno) é aplicável via API pública da Anthropic.
**Implicação:** nenhuma ação recomendável sem mais investigação — citado só por transparência de busca.

---

## Top 5 implicações acionáveis (ordenadas por valor/custo)

1. **Adicionar ao Step 0 do Spawn Protocol uma checagem de dependência sequencial**, não só de sobreposição de arquivos — se a saída de um agente alimenta o outro, serializar mesmo com 0 arquivos em comum (Kim et al. 2512.08296, achado de −70% em tarefas sequenciais paralelizadas). Custo: baixo (1 pergunta a mais no checklist); valor: evita a classe de degradação mais bem quantificada da literatura 2026.
2. **Citar MAST (2503.13657) e Huang et al. (2310.01798) explicitamente no PROTOCOL.md** como evidência primária por trás de V0-V3/ADR-186 e do "nunca auto-aprovar" — hoje essas regras são afirmadas sem citação; a literatura já as fundamenta. Custo: quase zero (edição de doc); valor: fortalece a rastreabilidade da doutrina para qualquer auditor externo.
3. **Documentar explicitamente que effort máximo não é estritamente dominante** (overthinking, 2604.10739 + platô de 2505.20522) no skill `effort` — evita o antipadrão "sempre effort alto por segurança", que a literatura mostra ter retornos negativos em alguns casos. Custo: baixo (doc); valor: médio (evita desperdício de tokens sem ganho, ou pior, respostas piores).
4. **Nomear como decisão deliberada** (não lacuna cega) que o roteamento do repo é por REGRA e não por classificador aprendido (RouteLLM 2406.18665) — auditabilidade > otimização marginal. Custo: zero (framing); valor: fecha uma pergunta óbvia de qualquer revisor familiarizado com a literatura de roteamento.
5. **Avaliar uma cascata de confiança barata→cara para tarefas L1-L2** no `llm-finops-architect` (FrugalGPT 2305.05176, "Is Escalation Worth It" 2605.06350) — hoje o roteamento parece estático por classe de tarefa; um sinal de confiança pós-hoc do modelo barato poderia reduzir custo sem abrir mão de qualidade. Custo: médio-alto (desenho + medição); valor: incerto até medir — por isso último na lista.

---

## Fontes

- [When Identity Skews Debate: Anonymization for Bias-Reduced Multi-Agent Reasoning](https://arxiv.org/abs/2510.07517) — arXiv:2510.07517
- [Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) — arXiv:2503.13657 (Cemri et al., MAST)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — Anthropic Engineering, jun/2025
- [Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296) — arXiv:2512.08296 (Kim et al.)
- [Large Language Models Cannot Self-Correct Reasoning Yet](https://arxiv.org/abs/2310.01798) — arXiv:2310.01798 (Huang et al., ICLR 2024)
- [FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance](https://arxiv.org/abs/2305.05176) — arXiv:2305.05176
- [RouteLLM: Learning to Route LLMs with Preference Data](https://arxiv.org/abs/2406.18665) — arXiv:2406.18665
- [Large Language Monkeys: Scaling Inference Compute with Repeated Sampling](https://arxiv.org/abs/2407.21787) — arXiv:2407.21787
- [Scaling Flaws of Verifier-Guided Search in Mathematical Reasoning](https://arxiv.org/abs/2502.00271) — arXiv:2502.00271
- [Self-Preference Bias in LLM-as-a-Judge](https://arxiv.org/abs/2410.21819) — arXiv:2410.21819
- [Judging the Judges: A Systematic Evaluation of Bias Mitigation Strategies in LLM-as-a-Judge Pipelines](https://arxiv.org/pdf/2604.23178) — arXiv:2604.23178
- [Is Escalation Worth It? A Decision-Theoretic Characterization of LLM Cascades](https://arxiv.org/pdf/2605.06350) — arXiv:2605.06350
- [ProgRouter: Online Progress-Guided Orchestration for Multi-Agent LLM Workflows under Quality-Cost Tradeoffs](https://arxiv.org/abs/2608.25992) — arXiv:2608.25992
- [When More Thinking Hurts: Overthinking in LLM Test-Time Compute Scaling](https://arxiv.org/html/2604.10739v1) — arXiv:2604.10739
- [Scaling over Scaling: Exploring Test-Time Scaling Plateau in Large Reasoning Models](https://arxiv.org/abs/2505.20522) — arXiv:2505.20522
- [Steering LLM Thinking with Budget Guidance](https://arxiv.org/abs/2506.13752) — arXiv:2506.13752 `[NÃO VERIFICADA quanto à aplicabilidade via API Anthropic]`
- [Process Reward Models That Think](https://arxiv.org/abs/2504.16828) — arXiv:2504.16828 (contexto de best-of-N/verifier-guided)

### Fontes internas consultadas (doutrina já adotada, não repetida)
- `PROTOCOL.md` §Debate, §Verification cascade, §Honest limitation, §Artifact Paradox
- `docs/HONEST-LIMITATIONS.md` §4 (Same-LLM limitation)
- `.claude/plans/DEBATE-SCHEMA.md` §13.2 (anonimização anti-halo)
