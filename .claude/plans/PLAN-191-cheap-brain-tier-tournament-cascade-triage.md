---
id: PLAN-191
title: "Cérebro barato — torneio de tiers, cascata com verificador e triagem; Jev como lane opcional"
status: draft
created: 2026-09-18
owner: CEO
depends_on: []
level: L2
budget_tokens: "W0 torneio: 0 de CEO, QUOTA de 60-90 tentativas de orquestração (eval/runner, ~100-200k cada); W1 cascata: mesma ordem, 3 braços; W2 roteador: <50k + centavos de API externa; W3 triagem: <100k + 1 lane Codex + ~2 h do Owner rotulando; W4 compactação: instrumento só. Teto: 1,5 M de agente + quota de duas noites."
budget_sessions: "W0 1 noite; W1 1 noite; W2 1; W3 1-2; W4 1"
context_risk: medium
external_wait: "Nenhuma assinatura para EXECUTAR (tudo é experimento, leitura, opt-in). Assinatura só se um resultado virar mudança de política de roteamento (PLAN-186 W-ROTA) ou lane nova de fornecedor (L3 próprio). Egresso para api.typesafe.ai é OPT-IN do Owner por flag; sem a flag, os braços Jev são PULADOS e o plano fecha com os braços locais."
eta_calendar: "W0+W1 em duas noites autônomas; W2 condicionada ao W0; W3 no ritmo do rotulamento do Owner; W4 quando houver uma compactação real para medir"
tags: [finops, roteamento, cascata, torneio, triagem, jev, experimento, opcional]
---

# PLAN-191 — Cérebro barato: o que um classificador barato e rápido compra de verdade

> **Nível:** L2 — só experimentos, leitura, instrumentos em `.claude/plans/PLAN-191/` e um flag
> opt-in. Nenhuma edição canônica, nenhuma integração. Se um resultado pedir mudança de política
> (roteamento, lane de fornecedor), isso é wave de OUTRO plano com a própria cerimônia.
>
> **Origem:** S355 (2026-09-17/18) — avaliação medida do Jev (TypeSafe) e do plugin
> `fast-jev-compaction`; ordem do Owner de 16/09 (consumo −1/3 ao mesmo output, zero lockouts);
> decisão do Owner de 18/09: *egresso é decisão de quem usa — declarar riscos, nunca remover a opção*.
> Memórias: `project-jev-typesafe-evaluation-s355`, `project-fast-jev-compaction-evaluation-s355`,
> `project-inert-mechanisms-s355`, `reference-jev-literature-s355`, `feedback-egresso-e-decisao-do-adopter`.

## Context — o que já está medido (não re-medir)

| # | fato | valor | fonte |
|---|---|---|---|
| C1 | 84 % do custo do framework está em subagentes Opus 5, por POLÍTICA (S339: «Opus executa»), não por herança | US$ 10.418 de 12.547 (API-equiv., 03→17/09) | `docs/research/s354-token-consumption-study/README.md` §2b M1 |
| C2 | PLAN-186 PROÍBE Haiku «sem evidência de torneio (n≥30/célula, gap≥25pp)» — e esse torneio nunca foi corrido | `tier_mix_rationale` | `PLAN-186-orchestrator-operating-model.md:29` |
| C3 | Cascata com verificador num workload REAL de Claude Code: draft barato aceito em 88,8 % de 125 requisições, **−45,8 % de custo** vs Opus direto; verify-then-escalate: −61 % de tokens | literatura | arXiv 2606.22840 (RLM-Cascade); `Cheese-Singh/LLM-Cascade` |
| C4 | Roteadores por classificador: RouteLLM −85 % em MT-Bench a 95 % da qualidade, MAS LLMRouterBench (ACL 2026) mostra que muitos, incluindo comerciais, não batem baselines simples; ganho realista ≈ 1/3 do publicado; 50-200 ms por decisão compõem | literatura | `reference-jev-literature-s355` |
| C5 | Jev: US$ 0,042/MTok entrada, saída grátis; p50 1,05 s (us-west); consistente (8/8 entradas idênticas; 2,2 % de flips entre passes no benchmark externo) | medido S355 + `anisselbd/jev-phishing-bench` | idem |
| C6 | **Veredito ÚNICO do Jev é fraco** (62,6 % em phishing vs 81,3 % Haiku; 60 % em substrato vs 22 % do regex, n=50) e a probabilidade não é calibrada (ECE 0,154; Brier ≈ preditor constante; Murphy: resolution 4 %) | medido | idem |
| C7 | **Jev como EXTRATOR DE SINAIS + cabeça logística LOCAL é forte:** 5 Nouls + regressão logística, holdout B: 95,0 % [93,5-96,2], AUROC 0,982, ECE 0,027 — empata com Haiku-sinais+regressão (93,2 %, p=0,063) a 27× menos custo e 5× menos latência; bate regex de 2 linhas (91,8 %, p=0,002) | benchmark externo controlado | `anisselbd/jev-phishing-bench` README (controles de 17/09) |
| C8 | Encoders pequenos fine-tuned batem LLM zero-shot em classificação; SetFit com 8 exemplos/classe ≈ RoBERTa-large em 3k | literatura | arXiv 2406.08660; SetFit |
| C9 | Painel de 3 juízes da mesma família NÃO é 3 opiniões (ρ 0,94-0,97); referência honesta exige lane de outro fornecedor | literatura + regra do repo | arXiv 2506.07962; `feedback-codex-read-only-probe-finds-what-serial-claude-refuters-miss` |
| C10 | Compactação: do que o `fast-jev-compaction` apagava, só 6,7 % era usado depois; 15/16 eram saída de Bash; o custo real de compactar aqui é F = 97.292 tokens de prefixo repago, T ≈ 107k | issue #26 do plugin; `PLAN-179/w0-measurement.md` | `project-fast-jev-compaction-evaluation-s355` |
| C11 | `.claude/eval/`: 10 tarefas reais com verificador determinístico, worst-of-N, cap de quota, launcher por `CEO_EVAL_EXEC_CMD` | existe | `.claude/eval/README.md` |
| C12 | `cost-table.yaml`: Opus 5 5/25, Sonnet 5 2/10, Haiku 4.5 1/5, Fable 5.1 10/50 (US$/MTok in/out) | existe | `.claude/scripts/cost-table.yaml:70-123` |
| C13 | **Classificador NATIVO:** function hooks (CC ≥ 2.1.274, early access, `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`) expõem `$.model.classify(text, labels, {model:'haiku'})` — decisão barata dentro do engine, sem terceiro; no `jev-phishing-bench`, Haiku com as MESMAS perguntas de sinal empatou com o Jev (93,2 % × 95,0 %, p=0,063, AUROC maior) | d.ts gerado por `/plugin-types` | `types/claude-code.d.ts:2205` (cópia inspecionada em S355); `check-substrate-watch.py`: CLI reconciliada em 2.1.198, instalada 2.1.276 |

## Goal

Responder com número, e com regra de morte pré-registrada, se um «cérebro barato» — cascata com
verificador, roteador local, ou Jev como lane opcional — compra **custo, velocidade ou qualidade**
no uso real do framework. Três perguntas, uma por eixo:

1. **Custo:** uma cascata Sonnet/Haiku-primeiro com verificador entrega a meta do Owner
   (−1/3 de tokens ao mesmo output) sem subir escapes? (W1)
2. **Roteamento:** um roteador ANTES da chamada (local ou Jev+cabeça logística) bate a cascata em
   custo à mesma taxa de acerto — ou o roteador é o passo a mais que a literatura diz que não paga? (W2)
3. **Qualidade/tempo do Owner:** para triagem de achados de rail (censo e recidiva), Jev-sinais +
   cabeça local bate SetFit/embedding local e o regex atual, em acurácia e em minutos humanos? (W3)

E uma pergunta lateral, sem fornecedor: (4) uma regra LOCAL de poda de resultados de ferramenta
reduz F sem subir re-execuções? (W4)

## Thesis

- O ganho de custo, se existir, vem da **cascata com verificador** (C3), que não precisa de
  classificador nenhum — o verificador é o roteador. O roteador ex-ante é a hipótese mais fraca (C4).
- Se o Jev entrar, entra como **extrator de sinais com cabeça calibrada LOCAL treinada nos rótulos
  do repo** (C7) — nunca pelo veredito nem pela probabilidade dele (C6). A cabeça local é o que
  torna a decisão calibrada e auditável; o Jev é só um gerador barato de features.
- **Baseline local é obrigatório e vai primeiro** (C8): se SetFit/embedding empatar, não há lane
  externa a construir — e o Owner não precisa nem decidir sobre egresso.
- Egresso é decisão do Owner/adopter, por flag opt-in, com o conteúdo enviado MINIMIZADO e listado
  (descrição de tarefa ou bloco de achado; nunca código, nunca diff, nunca resultado de ferramenta).

## Items

### W0 — PILOTO do torneio de tiers  [P0]  (livre; quota de 1 noite)
**É piloto, não a evidência do PLAN-186:29.** A régua que o `:29` invoca é `ADR-064:108-109` — n ≥ 30
por célula **(papel × tipo de tarefa)** E gap ≥ 25 pp — e 10 tarefas × 3 repetições dão 30 tentativas
por MODELO, mas 3 por tarefa×modelo: agrupar tarefas heterogêneas não satisfaz a célula (rail r1, P2).
O piloto decide se vale FINANCIAR o torneio completo (W0.c), não substitui ele.
- Rodar `.claude/eval/runner.py` sobre as 10 tarefas × {`claude-haiku-4-5`, `claude-sonnet-5`,
  `claude-opus-5`} × 3 repetições (worst-of-N do próprio runner), launcher com o modelo pinado por
  célula. `--allow-expensive` sob cap declarado; **serial**, como o README manda.
- **Verificadores fracos saem ANTES de rodar:** `t09_readme_doc.verify` devolve 1,0 para um README só
  com título (`# add subtract multiply usage`, medido no rail r1). Consertar o verificador ou excluir
  a tarefa do W0/W1 — nunca contar um pass que o verificador não sabe negar.
- W0.c [P1] — torneio COMPLETO que satisfaz ADR-064: células por tipo de tarefa (as 10 tarefas
  classificadas em ≤ 4 tipos), n ≥ 30 por célula×modelo. Só é financiado se o piloto mostrar variância
  entre tiers em algum tipo; custo de quota estimado e aprovado pelo Owner antes (OQ-2).
- Saída: `PLAN-191/w0/tournament.tsv` — tarefa × modelo × {pass, reward, tokens in/out, wall,
  escalou?}. Custo API-equivalente pela `cost-table.yaml`; quota lida da statusline nativa.
- **Pré-registro (antes de rodar):** «gap» = pass(Opus) − pass(tier) por tarefa; «qualificada» =
  tarefa com gap ≥ 25 pp para algum tier. A partição é TOTAL (rail r1, P2 — o caso do meio existia
  sem regra):
  - **0 qualificadas** ⇒ **W2 morre** (não há sinal para rotear) e o resultado vira ADENDO ao
    PLAN-186: para esta classe de tarefa a política «Opus executa» não tem evidência — a economia
    vem de POLÍTICA, não de roteador. W1 segue.
  - **1-2 qualificadas** ⇒ W2 NÃO abre ainda; roda-se W0.b para ampliar a amostra e a MESMA regra é
    reaplicada ao conjunto W0 ∪ W0.b: ≥ 3 qualificadas abre, < 3 mata. Sem terceira chance.
  - **≥ 3 qualificadas** ⇒ W2 abre com esses rótulos.
- W0.b [P1] — as 10 tarefas são pequenas (fizzbuzz, busca binária). Derivar 10 tarefas DURAS do
  histórico real: commits «controle vermelho→verde» (teste + cura no mesmo land) viram tarefa
  «faça este teste passar», verificador = o próprio teste. Mini-SWE-bench do repo, sem rótulo manual.
  Dispara com 0-2 qualificadas no W0 (no caso 0, só para informar o adendo; não reabre o W2).

### W1 — Cascata com verificador (execução)  [P0]  (livre; quota de 1 noite)
- Braços, sobre as mesmas tarefas do W0: **A** Opus direto (política atual, controle);
  **B** Sonnet-primeiro → verificador → Opus só se falhar; **C** Haiku → Sonnet → Opus.
  Verificador de aceitação = o `verify` determinístico da tarefa (C11); onde não houver, o pair-rail.
- **Escapes precisam de um juiz que NÃO seja o verificador** (rail r1, P2: o mesmo `verify` decide a
  aceitação da cascata e o sucesso do benchmark, logo não enxerga os próprios falsos positivos —
  `t09` aceita README só com título). Regra: TODA saída aceita pelo `verify` em B e C, mais uma
  amostra do mesmo tamanho de A, passa por avaliação CEGA ao braço (grader Opus com rubrica da
  tarefa, ou pair-rail); **escape** = aceita pelo `verify` e reprovada no juiz cego. Escapes de A
  medidos do mesmo jeito — é a linha de base.
- Métricas por braço: **tokens processados** (entrada+saída, incluindo as escaladas), custo
  API-equiv. pela `cost-table.yaml`, **quota** (leitura de `rate_limits` antes/depois do braço),
  wall-clock, pass rate, escapes, taxa de escalada.
- **Pré-registro (rail r1, P2 — preço não é a meta do Owner; tokens são):** SUCESSO = **tokens ≤ 0,67 × A**
  E custo ≤ 0,67 × A, com pass rate ≥ A − 5 pp e escapes ≤ A. Um braço que corte preço sem cortar
  tokens (Sonnet a 40 % do preço com o mesmo volume) é RESULTADO SEPARADO — «preço cai, quota não» —
  e não conta como sucesso do Goal 1. **MORTE** = taxa de escalada > 50 % (a cascata paga o barato
  E o caro) OU escapes > A.
- Perímetro financeiro NÃO desce de tier (R1 da ordem do Owner) — tarefas assim ficam fora do W1.

### W2 — Roteador ex-ante: local × Jev-sinais × regra trivial  [P1]  (condicionado ao W0)
- Rótulo = «precisa de Opus?» derivado do W0 (contrafactual medido, não inferido).
- Quatro roteadores lendo SÓ a descrição da tarefa: (i) **regra trivial** (tamanho, nº de paths,
  menção a hook/cerimônia); (ii) **local** — SetFit/embedding sobre os rótulos do W0; (iii) **Jev**
  — 5-7 Nouls como sinais (toca hook? multi-arquivo? tem oráculo de teste? sensível a segurança?
  spec ambígua?) + regressão logística LOCAL (Platt, n<1.000), calibrada por validação cruzada;
  (iv) **Haiku-sinais** — as MESMAS perguntas de (iii) a `claude-haiku-4-5` pela Messages API
  (o controle do `jev-phishing-bench`, C13) + a mesma cabeça local; sem fornecedor terceiro. Quando
  os function hooks saírem do early access, `$.model.classify` é a forma nativa deste braço.
- Métrica: custo à MESMA pass rate, comparado ao W1-B; ECE da cabeça; latência total adicionada.
- **Pré-registro:** o roteador só sobrevive se bater a cascata W1-B em custo a pass rate igual;
  a lane Jev só nasce se (iii) bater (ii) E (iv) por ≥ 5 pp — se Haiku-sinais empatar, o «cérebro
  barato» é nativo e o egresso a terceiro não se justifica.
- Egresso de (iii): apenas a descrição da tarefa, sob `CEO_JEV_LANE=1` (default OFF) e pelo redator
  ADR-114; operador/local; nunca CI; nunca hook. Sem a flag, (iii) é pulado e a wave fecha com (i)/(ii).

### W3 — Triagem de achados: censo e recidiva  [P1]  (livre; ~2 h do Owner)
- Corpus público já extraído (685 blocos, `corpus_v2.jsonl`, taxonomia v2 de 6 classes);
  famílias do `PLAN-188/ceremony-defect-corpus-S348.md` para recidiva.
- **Referência cega com DOIS fornecedores** (C9; rail r2, P2): as 3 lanes Claude contam como UM voto
  de família (sua maioria interna), a lane Codex como outro. Um bloco só recebe rótulo de referência
  quando os DOIS fornecedores concordam; toda discordância entre fornecedores vai ao Owner (é o que
  custa as ~2 h). Uma maioria 3-1 de lanes correlacionadas NUNCA vence o outro fornecedor sozinha.
- Censo — cinco braços: regex atual; SetFit local; Jev-veredito (controle negativo, já medido:
  60 %); **Jev-sinais + cabeça logística local** (C7); **Haiku-sinais + a mesma cabeça** (C13,
  mesmas perguntas, sem terceiro). Métricas: acurácia em CERIMÔNIAS NOVAS (split por cerimônia,
  nunca por bloco), ECE da cabeça, minutos do Owner por 100 blocos corrigindo sugestões vs.
  rotulando do zero.
- Recidiva — recuperação de antecedentes no top-3 por replay cronológico: SBERT/FAISS local ×
  Jev-Noul por família × busca lexical. Sugestão verificável, nunca fusão automática (PLAN-189 OQ-2:
  quem cura julga).
- **Pré-registro (regra ÚNICA; a Regra de parada abaixo a espelha byte a byte — rail r1, P2):**
  seja `B` = o MELHOR entre TODOS os baselines sem egresso a terceiro medidos na wave — regex atual,
  SetFit local, busca lexical, Haiku-sinais (rail r2, P2: nenhum baseline medido fica fora do máximo,
  senão a regra promove uma lane externa mais fraca que algo que já existe); `Δ` =
  acurácia(Jev-sinais+cabeça) − acurácia(`B`); `T` = variação dos minutos do Owner por 100 blocos
  contra `B`. A lane Jev **nasce se e só se** `Δ ≥ 3 pp` **OU** (`T ≤ −30 %` **E** `Δ ≥ −1 pp`).
  Qualquer outro resultado ⇒ não nasce, e W3 fecha com `B` como entrega. Recidiva: a mesma forma,
  com `B` = melhor entre busca lexical e SBERT/FAISS local, e recuperação no top-3 como acurácia.

### W4 — Poda local de resultados de ferramenta  [P1]  (instrumento; sem fornecedor)
- Regra determinística no PreCompact (ou function hook `session.compact`, early access — se estável):
  truncar resultados de `Read`/`Grep`/`Glob` mais velhos que K turnos a 300 chars + nota
  «re-leia»; **preservar `Bash`** (15/16 dos reutilizados, C10); nunca tocar os N mais recentes.
- Medir: **tokens processados por unidade de trabalho comparável** (mesma tarefa/cerimônia, com e
  sem a regra) e **nº de compactações por sessão**; re-execuções de ferramenta (proxy: mesmo `Read`
  do mesmo path após a compactação). F (`PLAN-179/w0/gateboot_repay.py`) fica como DIAGNÓSTICO:
  rail r2 apontou que F mede o piso repago do prefixo, e a poda pode encolher histórico e resumo
  sem mover o prefixo — um gate em F seria cego ao ganho que a wave procura.
- **Pré-registro:** SUCESSO = tokens processados −20 % **OU** compactações/sessão −30 %, em ambos os
  casos com re-execuções ≤ +10 %. MORTE = re-execuções > +25 %.
- Pode migrar para o PLAN-190 W5 («contexto por fase») se o Owner preferir — é a mesma medição.

## Adendos propostos aos planos existentes (o Owner aplica; este plano NÃO os edita)

- **PLAN-186** (executing): (a) o W0 daqui é PILOTO do torneio do `tier_mix_rationale:29`; a evidência
  que o `:29` e o `ADR-064:108` exigem (n ≥ 30 por célula papel×tipo) só nasce com W0.c — citar assim,
  não como equivalente; (b) o censo
  US5 (`PLAN-186/w0/us5-routing-surfaces-census-S340.md`) ganha três superfícies que EXISTEM e NÃO
  EXECUTAM: `.claude/scripts/optimizer/fanout.py:72` (`choose(context_size=)` sem arquétipo/complexidade),
  `_lib/model_routing.py::resolve_full()` sem call-site, `check_agent_spawn.py:321` `classify(desc, [])`
  com hints sempre vazios ⇒ ramo VETO do `task-route.py` inerte. Consertar antes de qualquer roteador.
- **PLAN-189** (draft, W0 em voo — não tocar o arquivo agora): a recidiva do W3 daqui é instrumento
  OPCIONAL da regra de classe (OQ-2), com SBERT local como baseline; sugestão, nunca fusão.
- **PLAN-190** (executing): JEV continua FORA (`:25`, `:274`) — este plano não muda isso. O W4 daqui
  é a medição que o W5 («recomendação no template SÓ após medir») pede para `bashOutputMaxChars`/poda.
- **PLAN-172** (reviewed): E6 (cascata de FILTROS pré-review) fica intacto; registrar em nota que a
  cascata de EXECUÇÃO (W1 daqui) tem evidência de campo (C3) e não compete com E6.
- **`check_pair_rail.py:1917`**: `_compute_jaccard_bucket` só é chamado por testes e o bucket é sempre
  `""` — o Caso E nunca discrimina; `docs/PAIR-RAIL-VERDICT-MATRIX.md` §2 promete «semantic similarity».
  Decisão do Owner: religar ou apagar junto com a promessa (cerimônia: hook canônico).

## Fora deste repositório — bot de market-making (Hummingbot), só desenho

O Owner levantou o Jev como decisor de reajuste do bot. Não é escopo deste plano; fica o desenho
honesto para o outro repo, pelo mesmo padrão C7:
- **Onde cabe:** decisões em cadência de MINUTOS (alargar spread, viés de inventário, pausar em
  regime adverso) — 1 s de latência é indiferente; **não** cabe em nada por tick.
- **Forma:** state = features públicas de mercado + inventário próprio; 5-8 Nouls como SINAIS
  (regime tendencial? volatilidade acima do normal? assimetria de pressão? risco de seleção adversa?)
  → cabeça logística LOCAL treinada nos PRÓPRIOS fills. Nunca o veredito do Jev direto.
- **Baseline obrigatório, primeiro:** um logístico/GBM local sobre as mesmas features — é calibrado
  por construção nos seus dados e não sai da máquina; e as regras já existentes (Avellaneda-Stoikov,
  volatility-spread do Hummingbot, detecção de regime por clustering→supervisionado).
- **Risco de egresso diferente:** não é código — é inventário e estratégia. Decisão sua.
- **Kill:** se o modelo local empatar em paper-trading, sem egresso. Nada aqui é recomendação de
  operação; é desenho de sistema de decisão, a validar em paper-trading antes de capital.

## O que este plano NÃO faz (declarado)
- Não integra o Jev, não cria dependência, não muda política de roteamento, não edita canônicos.
- Não usa a probabilidade do Jev como decisão (`p ≥ θ ⇒ aja` — regra de Chow, reprovada aqui).
- Não envia código, diff, resultado de ferramenta ou conteúdo de adopter a fornecedor externo.
- Não conclui «calibrado» a partir de ECE agregado sem a decomposição de Murphy nos dados limpos.

## Open questions (Owner)
- **OQ-1** Egresso opt-in para os braços Jev (W2-iii, W3): liga a flag neste repo PÚBLICO? (Recomendado:
  sim aqui, porque o corpus já é público; nos adopters privados fica OFF por padrão.)
- **OQ-2** Quota: W0+W1 são duas noites de orquestração real. Aceita, ou W0 só com Haiku×Sonnet (metade)?
- **OQ-3** Os cinco adendos acima: aplicar como está, ou só os de PLAN-186 (inertes)?
- **OQ-4** W0.b (tarefas duras do histórico): financiar agora ou só se W0 sair sem variância?

## How to continue
1. Owner responde OQ-1..4 (AskUserQuestion, rótulos verbatim → `PLAN-191/owner-decisions-S355.md`).
2. Pré-registrar W0/W1 (`PLAN-191/PREREG.md`, molde `PLAN-134/w0b/W0B-PREREG.md` do repo antigo).
3. Rodar W0 numa noite; publicar `tournament.tsv`; decidir W2 pela regra.
4. Rodar W1; publicar custo/quota/pass/escapes por braço; veredito contra o pré-registro.
5. W3 no ritmo do Owner; W4 na próxima compactação real medida.

## Success criteria
- [ ] W0 (piloto): tabela tarefa×modelo×repetição com tokens, custo e quota; `t09` consertado ou
      excluído ANTES da primeira tentativa; decisão de financiar W0.c registrada com o número.
- [ ] W1: um braço com **tokens ≤ 0,67 × A** e custo ≤ 0,67 × A, pass ≥ A − 5 pp, escapes ≤ A
      medidos por juiz cego ao braço — OU morte declarada com número.
- [ ] W2: veredito numérico roteador × cascata; lane Jev nasce SÓ se bater o local por ≥ 5 pp.
- [ ] W3: acurácia em cerimônias novas + minutos do Owner, quatro braços; referência com 2 fornecedores.
- [ ] W4: tokens processados e compactações por unidade de trabalho comparável, com e sem a regra;
      taxa de re-execução; F reportado como diagnóstico.
- [ ] Nenhum item deste plano editou arquivo canônico; nenhum byte saiu sem a flag.

## Regra de parada (pré-registrada)
- W0: 0 qualificadas ⇒ W2 cancelada, W1 segue, adendo ao PLAN-186; 1-2 ⇒ W0.b e reaplicação única
  da regra (≥ 3 abre, < 3 mata); ≥ 3 ⇒ W2 abre. W0 é piloto: a evidência do PLAN-186:29 só existe com
  W0.c (n ≥ 30 por célula tipo-de-tarefa×modelo).
- W1: escalada > 50 % ou escapes > A (escapes pelo juiz CEGO, nunca pelo `verify`) ⇒ cascata morta;
  «custo ≤ 0,67 × A» sem «tokens ≤ 0,67 × A» NÃO é sucesso do Goal 1.
- W3: a lane Jev nasce se e só se `Δ ≥ 3 pp` OU (`T ≤ −30 %` E `Δ ≥ −1 pp`), com `Δ` e `T` contra `B`
  = o MELHOR entre TODOS os baselines sem egresso medidos (regex, SetFit, lexical/SBERT, Haiku-sinais);
  qualquer outro resultado ⇒ não nasce (mesma regra do W3, sem segunda leitura).
- W4: sucesso e morte medidos em tokens processados e nº de compactações por unidade de trabalho
  comparável — F é diagnóstico, nunca o gate (rail r2).
- Owner recusa OQ-1 ⇒ todos os braços Jev pulados; o plano segue inteiro com braços locais.
- Qualquer wave que precise editar canônico para MEDIR ⇒ parar e abrir wave própria com cerimônia.
