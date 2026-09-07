---
id: PLAN-171
title: Imports de governança (cloudflare-os/xirp) — batch-approval, proveniência de leituras, FILE ASSIGNMENT write-time, living docs local
status: executing
executing_at: 2026-09-05
reviewed_at: 2026-08-11
reviewed_by: "Owner - ratificacao S302f via OWNER-RATIFY-S302.sh: ratifico os 6 planos na v2.6 (rail Codex 7 rounds, r7 APPROVE, commits ab45f56..0c90174)"
created: 2026-08-11
owner: CEO
depends_on: [PLAN-169]
budget_tokens: 400-700k (W0 censo = ~6 lotes de ~10 hooks ≈ metade do custo; firmado S302e)
budget_sessions: 5-8 (W0 3-4; W1/W1b-d 1-2; W4-W5 1-2)
context_risk: medium
external_wait: nenhum
tags: [governance, audit, provenance, seed]
---

# PLAN-171 — Imports de governança: proveniência e cerimônia de lote

> **SEMENTE (S302, 2026-08-11).** Registrada pelo CEO a pedido do Owner
> após estudo de dois sistemas externos (cloudflare-os da Cloudflare,
> Apache 2.0, aberto 2026-08-05; xirp do Spotify, proprietário, beta
> 2026-08-10) via workflow de 5 agentes + análise de fit. **Gatilho
> ATUALIZADO (decisão do Owner, S316 2026-08-20): W0 pode iniciar JÁ —
> GA v1.3.0 saiu 2026-08-17 e o antigo acoplamento "land de W3/W4 do
> 169" era milestone sem consumo de artefato (o censo retroativo dos 57
> hooks não consome nada da W4). O único insumo real é o registro de
> entrega do AC-9 no FECHAMENTO do 169, que a W0 consome QUANDO
> existir.** Refinamento + debate L3 antes de `reviewed`.

## 0. Papel no roadmap

Este plano é o **habilitador de governança do PLAN-172 (E5/WIP=2)**,
não uma trilha independente (verdito da síntese speed-research-r2,
S302): FILE ASSIGNMENT em write-time e proveniência de leituras são o
que torna duas unidades em voo AUDITÁVEIS (colisão de sentinel-scope é
o risco de governança nomeado do E5); batch-approval é o pré-requisito
do mecanismo "batching L1-L2" do 172. Priorizar os itens pelo caminho
crítico do 172.

## 1. Contexto (o que os externos validaram)

- **cloudflare-os** opera com Gatekeepers (brokers de credencial por
  serviço), capabilities zero-by-default e um **observation log**: toda
  leitura do agente é registrada e anexada aos artefatos produzidos;
  visualização é validada contra o log. A política de contribuição
  deles ("o gargalo é revisar, não escrever") ecoa a tese deste
  framework. Validação externa da direção; o runtime deles (Workers,
  Durable Objects) é categoricamente incompatível com este layer
  stdlib-only — importamos IDEIAS, zero código.
- **xirp** persiste contexto entre sessões/engenheiros e gera "living
  documentation" das sessões — mas faz upload de transcripts sem
  redação de segredos para cloud proprietária. Importamos a ideia,
  invertendo a postura: tudo LOCAL, egress zero por default.

## 2. Escopo (itens, em ordem de prioridade)

### W1 — Cerimônia de aprovação em lote (batch-approval) formalizada
A prática já existe (packs staged + dry-run em clone + `OWNER-*-CUT.sh`
com UMA assinatura GPG sobre manifesto sha256; commit-por-manifesto
validado na S301). Falta codificar: schema do approval-queue, corpo da
cerimônia em PROTOCOL/skill, e o invariante anti-lote-parcial — o gate
DEVE recusar conjunto ≠ manifesto (lição do fix-forward `8a178f5`:
gate que aceita run parcial é vácuo). Cada item do lote carrega
evidência de dry-run individual; lote não dilui o escrutínio V3.

### W2 — Manifesto de proveniência de LEITURAS (observation log local)
Estender o audit HMAC (PostToolUse em Read/Grep/Glob/WebFetch) para
registrar digests/paths do que cada agente LEU, em **sidecar
encadeado** (nunca inflar a cadeia principal — perf-gate p99 e o
histórico float-em-HMAC proíbem). Anexar o manifesto aos artefatos
decisórios (verditos de debate/council, packs). No `/council`, validar
o prompt egresso contra o manifesto: a **allowlist-por-proveniência
entra como CAMADA ADICIONAL sobre a blocklist-por-classe do ADR-114 —
a blocklist nunca é removida** (Codex r1: layer, não replace). Honestidade
de fronteira: leituras de lanes fora do harness (`codex exec`) são
INVISÍVEIS — documentar como limite, não vender cobertura total.

### W3 — FILE ASSIGNMENT enforcado em write-time

**CORTADA (Owner, 2026-09-06 23:5x, revisão S348):** duplica o flip da
janela advisory já agendado no PLAN-178 — mesma classe, outro dono.
Decisão registrada em
`.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md`
§8 (Q3, bloco B). Texto da wave preservado abaixo como histórico.

Hook PreToolUse(Edit/Write) que bloqueia escrita de agente nomeado fora
do `## FILE ASSIGNMENT` declarado no spawn. Converte declaração
advisory em invariante mecânica. **Classificação corrigida (Codex r1,
P1): FILE ASSIGNMENT malformado é INPUT de segurança não-parseável =
fail-CLOSED (block)** — doutrina §4 fail-closed-on-input; infra real
(hook ausente, timeout) segue fail-open com breadcrumb. É
defense-in-depth ("Bash escapa"), não fronteira — escrever a claim no
tamanho do enforcement.

### W4 — Living documentation LOCAL-ONLY

**CORTADA (Owner, 2026-09-06 23:5x, revisão S348):** vira follow-up
próprio se alguém pedir — não segue como wave deste plano. Decisão
registrada em
`.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md`
§8 (Q3, bloco B). Texto da wave preservado abaixo como histórico.

Gerador stdlib que materializa docs navegáveis ("o que aconteceu e por
quê") a partir do audit log + closeouts. Tudo local e advisory; log
renderizado como untrusted data; de-id por CLASSES (não por-nome)
antes de qualquer materialização; qualquer versão que saia do disco
passa pelo redactor ADR-114 ou não existe.

### W5 — Higiene de worktree para paralelismo (pré-requisito E5)

**CORTADA (Owner, 2026-09-06 23:5x, revisão S348):** servia ao E5 do
PLAN-172, que está congelado — sem comprador enquanto o PLAN-172 não
reabrir. Decisão registrada em
`.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md`
§8 (Q3, bloco B). Texto da wave preservado abaixo como histórico.

Audit log e memória são keyed por cwd-slug: N worktrees fragmentam a
cadeia. Definir convenção de log ÚNICO no repo principal (worktrees
anotam `worktree_id` no evento) ANTES de qualquer execução WIP=2 do
PLAN-172. Sem isso, E5 não roda.

## 3. Não-escopo (decidido no estudo, não re-litigar sem dado novo)

- Code Mode (ações dentro de código autorado pelo agente) — alarga a
  superfície não-auditada de propósito.
- Runtime residente de qualquer espécie (Workers/daemons/brokers).
- Upload de transcripts / workspace cloud.
- Metade viewer-side do observation log (sem ponto de mediação no
  consumo de artefatos git — enforce só no egress).

## 4. Riscos nomeados

- W2 é o item de maior valor E maior risco de perf — pilotar em
  sidecar com medição que imprime seus inputs (lição S285).
- W3 pode colidir com spawns legítimos multi-arquivo — janela de
  exceção via assignment glob, nunca via desligar o hook.
- Todos os itens tocam superfície de hooks → cerimônia canonical-edit
  + pair-rail por item; L3 com debate.

## 5. Revisão v2 — auditoria total S302 (workflow framework-total-audit, 14 agentes, 12 lanes ok)

**Re-escopo: este plano fica MENOR e ganha um W0 bloqueante.**

- **W0 (NOVO, bloqueante, pré-tudo): censo de gates com positive
  control.** Nenhum gate entra em settings.json/CI sem controle
  positivo que FALHA quando o enforcement é removido + registro de
  qual workflow o executa; aplicado retroativamente aos 57 hooks.
  As 3 dívidas de enforcement abertas desde S294 (pair-rail-gate.sh
  inexecutável, injector persona fuzzy, overhead-ack não cobre Write)
  PERTENCEM ao AC-9 do PLAN-169: o W0 as AUDITA e herda apenas o que
  o fechamento do 169 declarar não-feito (r2: sem posse dupla — o
  texto operativo e a cura dizem a MESMA coisa). Racional: F4 do PLAN-166 é a 5ª
  instância nomeada da classe "gate vermelho invisível" — não se
  importa governança nova sobre camada de enforcement com dívida.
- **W1 (mantido, ampliado):** batch-approval + formato de verdito com
  pin único `delta_manifest` (em vez de allowlist enumerada — fecha o
  loop evidência-de-evidência da S301).
- **NOVO W1b:** ADR curto formalizando a economia de revisores:
  **Codex = único revisor bloqueante do rail; Grok = gatilho**
  (desacordo Claude↔Codex, L4/SPEC/release, auditorias periódicas).
  A auditoria constatou que `grok.py` é host-adapter de papel único —
  o claim "dois revisores externos" não corresponde ao enforcement.
- **NOVO W1c:** fronteira de ownership dos domain-packs (116 domain
  skills → squad-packs opt-in via squad-install; 1-2 domínios de
  referência em-tree) — pré-trabalho do PLAN-175.
- **NOVO W1d:** fixes de doc-drift baratos: spawn.md (manda injetar
  SKILL.md inteiro; default é reference-mode desde ADR-090 — ~9-16k
  tok/spawn desperdiçados se seguido literalmente) + propagação do
  cap G12 (skill de parallelization manda 6; ratificado é 8
  read-only).
- **ADIADO:** W2 (proveniência de leituras/observation log) e W3
  (FILE ASSIGNMENT write-time) só DEPOIS do W0 fechar — mesma lógica:
  primeiro provar vivo o que existe, depois adicionar.
- W4 (living docs) e W5 (higiene worktree) mantidos; W5 continua
  pré-requisito do E5 (PLAN-172).

## 6. Debate Codex r1 (S302) — curas incorporadas + ACs

Verdito r1: NO-GO com 4 P1 — todos aceitos e curados nesta v2.1:
1. **Milestone, não trem inteiro** (§seed corrigido).
2. **W0 não re-clama os débitos do AC-9 do PLAN-169**: os 3 débitos
   de enforcement PERTENCEM ao 169 (AC-9, parcialmente executado). O
   W0 os AUDITA e herda apenas o que o fechamento do 169 declarar
   não-feito — coordenação por registro de entrega, sem dupla posse.
3. **W1c é contract-only**: define a fronteira de ownership dos
   domain-packs; a MIGRAÇÃO é do PLAN-175 (passo 3).
4. **W3 fail-CLOSED em input malformado** (corrigido acima).

ACs mínimos (anti-churn de rail):
- W0: censo em lotes de ~10 hooks/sessão; AC = 100% dos hooks com
  {positive control OU registro "sem-controle-por-design" justificado};
  kill = lote sem fechar em 2 sessões ⇒ re-escopo antes de continuar.
- W2 (quando destravar): piloto em sidecar com kill numérico —
  overhead p95 do PostToolUse acima do teto do perf-gate vigente ⇒
  redesenho; medição imprime inputs.
- Budget firmado (frontmatter); nada de TBD.

## 7. Pronto-para-execução (S302e)

**ACs por wave (além dos já definidos no §6):**
- W1 (batch-approval): schema do approval-queue commitado + gate
  anti-lote-parcial com positive control (recusa conjunto ≠ manifesto)
  + 1 lote real landado pela cerimônia nova com verdito pin único
  `delta_manifest`.
- W1b (ADR economia de revisores): ADR curto ACEITO por cerimônia;
  `grok.py` docstring e docs de rail passam a refletir o papel real
  (Codex bloqueante; Grok gatilho). AC: nenhuma superfície de doc
  claim "dois revisores externos de release".
- W1c (fronteira ownership packs): contrato escrito (o que é
  framework vs pack; quem assina pack; como CI trata pack ausente);
  AC: PLAN-175 consegue executar migração SEM decisão nova.
- W1d (doc-drift): spawn.md corrigido p/ reference-mode + G12 cap 8
  propagado na skill; AC: grep zero de "inject SKILL.md inteiro" e
  zero de "cap 6" em superfícies vivas.
- W3 (FILE ASSIGNMENT write-time — r4: AC de segurança faltava):
  positive controls nos TRÊS ramos — assignment malformado ⇒ BLOCK;
  arquivo fora do escopo ⇒ BLOCK; infra simulada (hook
  ausente/timeout) ⇒ allow com breadcrumb; AC adicional: replay dos
  spawns históricos de uma janela de observação retrospectiva de 7
  dias-calendário (janela de DADOS, não estimativa de esforço —
  ADR-081) com ZERO falso-bloqueio.
- W4 (living docs): gerador emite índice navegável de 1 plano
  histórico como demo; AC: zero segredos (grep por CLASSES) e
  advisory-only.
- W5 (worktree): convenção log-único documentada + `worktree_id` no
  evento; AC: 2 worktrees paralelos escrevem no MESMO log encadeado
  sem quebra de verify_chain.

**Runbook sessão 1:** rodar lote-1 do censo W0 (10 hooks mais
críticos: canonical-edit, bash-safety, agent-spawn, pair-rail,
overhead, adequacy, audit-emit, injector, sentinel-unlock,
credential-leak) — para cada um: positive control existente? vivo?
(rodar o controle) → tabela verde/vermelho/sem-controle + herança
AC-9. Gate 3: `/debate start PLAN-171` antes do primeiro item L3.

**Debate:** pair-rail Codex 3 rounds (r1 REJECT → r3 APPROVE,
S302c) cumpre o review cross-model do conjunto; o `/debate` formal
L3 roda no início da execução (Gate 3), como manda o protocolo.

## Registro de execução

- **2026-09-05 (S345)** — W0 lote 1/6 MEDIDO: os 10 gates do runbook
  §7 (canonical-edit, bash-safety, agent-spawn, pair-rail, overhead,
  adequacy, audit-emit, injector, sentinel-unlock, credential-leak),
  cada um com o controle positivo rodado nas DUAS metades (verde como
  está; **vermelho com o enforcement removido**, mutação mínima numa
  worktree descartável). 10/10 verde, 0 vácuo, 0 sem-controle; ZERO
  dívidas herdadas do AC-9 do PLAN-169 — as três dívidas de S294 estão
  CLOSED no fechamento do 169, e a evidência de disco de CADA uma está
  no §2 do relatório (uma linha por dívida, com o arquivo que a fecha).
  Relatório: `.claude/plans/PLAN-171/w0/lote-1-S345.md` — §1 é a tabela
  do censo, §2 a herança do AC-9, Apêndices A e B as duas metades do
  controle. Falta: lotes 2-6.
- **2026-09-06 (S347)** — W0 lote 2/6 MEDIDO: os 10 hooks REGISTRADOS de
  `R[0:10]` da partição determinística (§1 do relatório): adversary,
  plan-edit, protocol-semver-cascade, skill-patch-sentinel, tier-policy,
  arbitration-kernel, scratchpad-access, budget, read-injection,
  codex-filewrite. Cada um com o controle positivo rodado nas TRÊS
  metades — verde como está; **vermelho com o enforcement removido**
  (mutação mínima numa worktree descartável); e verde OUTRA VEZ depois
  do `git restore` (o **controle de restauração**, novo neste lote:
  sem ele um `.pyc` velho no `sys.pycache_prefix` do macOS falsifica a
  medição, o que foi reproduzido e está no §4 do relatório). 10/10
  verde, 0 vácuo, 0 sem-controle. Relatório:
  `.claude/plans/PLAN-171/w0/lote-2-S347.md`. O **lote 3 roda em
  PARALELO** sobre `R[10:20]` e reporta em arquivo PRÓPRIO — as duas
  fatias são disjuntas por construção da partição, não por acordo.
  Falta: lotes 3-6.
- **2026-09-06 (S347, noite autônoma, land combinado)** —
  `p171-w0-lote2-fix` landado: cura pós-land dos DOIS P1 que o rail achou
  DEPOIS do land do lote 2 (`184a1a2`). (a) A classificação «advisory por
  desenho — SEMPRE allow» das linhas 3, 8 e 9 era falsa para
  `check_read_injection.py`, que BLOQUEIA sob `CEO_UNICODE_HARDBLOCK=1`:
  a rota opt-in passou a ser MEDIDA por instrumento (`measure-optin.py`,
  novo Apêndice F) nas três metades, com os limites do detector GERADOS
  como complemento dos conjuntos que ele imprime — `0 / 0 / 1` construtos
  de bloqueio nos três hooks advisory. (b) A linha de contagem do §2, que
  se dizia «derivada por comando» enquanto os seis números eram literais
  digitados no gerador, passou a ser PRODUZIDA por `gen-count.py` sobre a
  própria tabela, com o Apêndice C reproduzindo `10 / 10 / 0 / 0 / 10`.
  Bateria: 10 node ids do censo (10 passed in 1.19s) + 3 node ids do
  Apêndice F (3 passed in 0.11s), controle das formas do detector
  («VEREDITO: todos os controles OK», incluindo o arquivo REAL rastreado
  `.claude/hooks/check_harness_config.py` l. 688 e a RECUSA do instrumento
  inteiro), Apêndice F re-derivado byte-idêntico do JSON, gates de corpus
  todos rc 0 (`validate-governance.sh` COMPLETO Errors: 0;
  `verify-counts.sh` sem drift, 818 arquivos / 15.724 testes;
  claude-md-claims; staleness; test-env-hygiene; contaminação). Rail r1
  do land: as DUAS pistas codex (`review --uncommitted` e texto)
  APPROVE, zero P1/P2 — registro em
  `.claude/plans/PLAN-171/w0/s345-p171-w0-lote2-fix/rail-land-round-1.md`.
  Residuais NOMEADOS: `PLAN-171-FOLLOWUP-lote2-generated-figures` (as
  figuras de §1/§4/§5 e dos Apêndices A/B/D seguem literais no gerador do
  lote 2) e `PLAN-171-FOLLOWUP-readinjection-docstring` (o docstring
  canônico ainda diz «always allows» — sai por cerimônia GPG). Os lotes
  3-6 herdam o detector de QUATRO formas.
- **2026-09-06 (S347)** — W0 lotes 3 e 4/6 no registro. **Lote 3**
  (`R[10:20]`: cost-envelope, worktree-writer, config-protection,
  ledger-checkpoint, audit-log, confidence-gate, output-safety,
  subagent-fabrication, skill-reference-read, output-secrets) landou em
  `00839a6` como pack SÓ-RELATÓRIO — sem linha de registro, que esta paga:
  relatório em `.claude/plans/PLAN-171/w0/lote-3-S347.md`. **Lote 4/6
  MEDIDO** sobre `R[20:30]` da MESMA partição determinística —
  skill-bootstrap-post, webfetch-injection, mcp-response, codex-response,
  bash-canonical-forensic, SessionStart, turbo-sessionstart,
  compact-pinning, SessionEnd, UserPromptSubmit —, cada um nas TRÊS
  metades (verde como está; **vermelho com o enforcement removido**, mutação
  ancorada numa worktree descartável; verde outra vez depois do `git
  restore`). 10/10 verde, 0 vácuo, 0 sem-controle, 0 UNREGISTERED. Duas
  coisas que este lote acrescenta ao método: (a) uma coluna «O que o
  controle prova» por linha, porque oito dos dez hooks são OBSERVADORES e um
  `verde` sem essa coluna seria lido como «bloqueia» — quatro linhas provam
  DETECÇÃO, não emissão, e o §4 declara essa lacuna do corpus; (b) o
  detector de bloqueio herdado do `lote2-fix` ganhou DUAS formas com
  controle positivo próprio, e a primeira delas
  (`getattr(<x>, "decision", ...) == "block"`) DESMENTIU um zero: o
  detector de quatro formas reportava «nenhum construto de bloqueio» para
  `SessionStart.py`, que REGISTRA a recusa do validador a um
  `.claude/instructions.md` envenenado — contabiliza
  `instructions_blocked` e emite `persistent_instructions_blocked`. O que
  a medição NÃO estabelece, e por isso não está afirmado aqui: essa função
  não carrega o arquivo em nenhuma das versões (`SessionStart.py:347-363`),
  então o vermelho prova a perda do REGISTRO, não um carregamento
  impedido. Relatório:
  `.claude/plans/PLAN-171/w0/lote-4-S347.md`. Falta: lotes 5-6 (`R[30:42]`,
  12 hooks).
- **2026-09-06 (S347)** — W0 lote 5/6 MEDIDO: os 6 hooks REGISTRADOS de
  `R[30:36]` da partição determinística (§1 do relatório): Stop, codex-review-user-code, review-loop, closeout-guard, fluency-nudge, precompact-continuity.
  Cada um com o controle positivo rodado nas TRÊS metades — verde como
  está; **vermelho com o enforcement removido** (mutação mínima de âncora
  contada, o instrumento RECUSA se a contagem divergir); e verde OUTRA VEZ
  depois do `git restore`. 6/6 verde, 0 vácuo, 0 sem-controle. A
  fatia é de CICLO DE VIDA (`Stop`, `SubagentStop`, `PreCompact`): os seis
  registros têm matcher vazio, e os seis controles vivem em
  `.claude/hooks/tests/`, logo rodam nos DOIS jobs de hook do
  `validate.yml` — ao contrário do lote 1, cujo controle do injector fica
  fora do dual-rail. A classe de cada hook é **MEDIDA**, não lida no
  docstring (o P1 que o `lote-2-fix` pagou): Apêndice E conta os construtos
  de recusa em quatro formas — 2 bloqueantes, ambos **opt-in**
  (`codex_review_user_code.py` sob `CEO_CODEX_USER_REVIEW_BLOCK=1`;
  `review_loop.py` sob `CEO_REVIEW_LOOP=1`, `review_loop.py:42`+`:200`) e
  4 com ZERO. Relatório:
  `.claude/plans/PLAN-171/w0/lote-5-S347.md`. Falta: lote 6 (`R[36:42]`,
  6 hooks).
- **2026-09-06 (S347)** — W0 lote 6/6 MEDIDO: os 6 hooks REGISTRADOS de
  `R[36:42]` da partição determinística (§1 do relatório) — a ÚLTIMA
  fatia: postcompact-reinject, config-change, subagent-start, setup-verification,
  directory-added, notification. Cada um com o controle positivo rodado nas
  TRÊS metades — verde como está; **vermelho com o enforcement removido**
  (mutação mínima numa worktree descartável); verde OUTRA VEZ depois do
  `git restore` (o controle de restauração do lote 2). 6/6 verde, 0
  vácuo, 0 sem-controle. Fatia de eventos de CICLO DE VIDA: 5 das 6
  linhas são OBSERVADORES — e o §4 do relatório declara, POR LINHA (do
  campo `proves` do `red-half.json`), qual mecanismo cada controle
  estabelece: emissão da observação em 4 delas e o SCRUB de
  não-eco na de `notification`, que NÃO prova emissão. A palavra
  «advisory» só é usada depois de `measure-optin.py` medir os
  construtos de bloqueio e sondar cada switch fim-a-fim com controle
  positivo próprio — 1 hook com construto de bloqueio (3 construtos
  ao todo), 0 rodada(s) do probe classificada(s) como BLOCK. Quem
  COLETA cada controle é derivado por COLEÇÃO (`--collect-only` sobre
  os ALVOS de pytest de cada step E sobre os seletores `-m`/`-k`
  desse step, os DOIS replayados), não por grep — e coletar
  SOBREVIVENDO ao seletor é condição NECESSÁRIA, não suficiente: o
  replay não exercita a condição `if:` do job nem o ambiente do
  runner. Relatório:
  `.claude/plans/PLAN-171/w0/lote-6-S347.md`. Esta é a ÚLTIMA fatia por
  ÍNDICE — o que **não** quer dizer que `R` esteja coberto: no momento
  desta derivação não falta em disco NENHUM relatório de lote: os outros
  cinco já estão lá e este pack acrescenta o sexto — medido por
  `os.listdir` sobre `.claude/plans/PLAN-171/w0/`
  (é o §5 do relatório). Linhas de
  `Registro de execução` ainda devidas por relatório já em disco: nenhuma.
  O W0 ainda deve, além disso, a consolidação dos seis num veredito
  único.
- **2026-09-06 (S348)** — W0 CONSOLIDADA: os seis relatórios de lote
  (`lote-1-S345.md` a `lote-6-S347.md`) somados num veredito único, sem
  medição nova — cada número citado por `arquivo:linha`. Partição:
  `|L| = 48` arquivos de hook em `settings.json` (50 registrações, 49
  nomeando `.py`); o lote 1 cobre 6 desses 48 (mais 2 arquivos fora de
  `L`); os lotes 2-6 cobrem os 42 restantes (`R[0:42]`), em fatias de
  10/10/10/6/6. Total: 52 linhas de gate censadas, 51 verde (controle
  positivo provado vermelho e, a partir do lote 2, restaurado verde de
  novo), 0 vácuo, 0 sem-controle-por-design, 0 UNREGISTERED, **1 sem
  controle** (`check_cost_envelope.py`, caminho de bloqueio sem
  controle demonstrado nos 59 testes existentes — achado do lote 3).
  Cobertura de `L`: **100% (48/48)**. O AC do §7 («100% dos hooks com
  positive control OU sem-controle-por-design justificado») fica a UMA
  linha de fechar. Dívida declarada consolidada: os 11 arquivos de hook
  em disco fora de `L` (59 no total), a condição
  `if: vars.CEO_SOTA_DISABLE != '1'` dos jobs de CI nunca exercitada, o
  replay de seletores `-m`/`-k` (necessário, não suficiente) e os dois
  follow-ups já nomeados (`PLAN-171-FOLLOWUP-lote2-generated-figures`,
  `PLAN-171-FOLLOWUP-readinjection-docstring`), nenhum ainda com
  arquivo de plano próprio no disco. Fora do escopo desta consolidação:
  as waves W1-W5 do plano, que a revisão de portfólio S348 recomendou
  RE-ESCOPAR (3/3 críticos,
  `PLAN-186/portfolio-review-S348/portfolio-review-S348.md:40`) citando
  «4 de 6 lotes landados» — premissa escrita em `7f6b564` (22:41:55)
  ANTES dos lotes 5 e 6 landarem (`ef4c1b3` 22:48:17, `690c3e2`
  23:26:39); a ratificação dessa recomendação segue PENDENTE do Owner
  em 2026-09-07, agora com a W0 em 6/6. Relatório:
  `.claude/plans/PLAN-171/w0/W0-consolidated-verdict-S348.md`.
- **2026-09-06 (S348, ~23:5x)** — **Owner RATIFICA o re-escopo:** «Sim:
  o plano vira W0 + W1 + W2 (Recomendado)» — decisão Q3 do bloco B,
  registrada em
  `.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md`
  §8. W3, W4 e W5 (§2 acima) são CORTADAS, cada uma com a nota e a
  razão no topo da própria seção; o texto das três waves permanece no
  arquivo como histórico, não apagado. W4 pode voltar como follow-up
  próprio se alguém pedir. Nenhuma mudança de `status:` — o plano
  segue `executing`.
