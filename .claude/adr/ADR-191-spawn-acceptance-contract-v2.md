---
adr_id: ADR-191
title: Spawn acceptance contract v2 — FILE ASSIGNMENT obrigatório e parseável; gramática reduzida para agentes de workflow; fence obrigatório no ingest de retornos in-harness
status: ACCEPTED
proposed_at: 2026-08-13
accepted_at: 2026-08-14
proposed_by: CEO (S305 — PLAN-178 W0 live-fire + censo de callers; staged em PLAN-178/staged-loteB)
decided_by: Owner (assinatura GPG da cerimônia do Lote B/PLAN-178; decisões ⚖️ 1-3 ratificadas S307 via AskUserQuestion)
risk_tier: A
debate_required: true
related_plans: [PLAN-133, PLAN-153, PLAN-178]
related_adrs: [ADR-136, ADR-141, ADR-175, ADR-186, ADR-089-AMEND-1]
---

# ADR-191 — Spawn acceptance contract v2

## §1 Contexto

Três achados do W0/PLAN-178 (tabela MAST-14 + injeção inter-agente)
motivam este contrato:

1. **A claim de CLAUDE.md prometia mais do que o hook entregava.**
   CLAUDE.md §4 dizia que todo spawn nomeado "carrega `## FILE
   ASSIGNMENT`"; o live-fire (S305) mostrou allow SILENCIOSO na
   omissão — o bloco era parseado apenas para o Rail 3 advisory
   (detector de colisão), e a omissão **removia o spawn da detecção
   de colisão da sessão inteira** (R-SEC1): o emit
   `spawn_file_assignment_recorded` vivia dentro do branch
   `if mine:` — sem paths, sem evento, sem visibilidade.
2. **Censo de callers** (`PLAN-178/c1-caller-census.md`): o gerador
   canônico `inject-agent-context.sh` tinha ZERO ocorrências do
   bloco — um enforce fail-closed quebraria o caminho PADRÃO de
   spawn no dia 1. Os 4 workflows shipados despacham `agent()` fora
   do gate de spawn (probe `wf_d7af49d9`: `blocked=false`).
3. **Assimetria de ingest**: o retorno de um subagente in-harness era
   interpolado CRU no prompt do consumidor (refuter/síntese),
   enquanto as lanes EXTERNAS do council já chegavam capped + fenced
   (`LANE_RESPONSE_CAP=24000`) — um confused deputy interno.

Havia ainda uma célula de gramática ambígua: o token `none` em
`CAN edit:` era DROPADO como placeholder (`_parse_file_assignment`),
tornando read-only intencional, wildcard e omissão indistinguíveis.

## §2 Decisão

1. **Spawn NOMEADO exige `## FILE ASSIGNMENT` parseável**: ≥1 path
   concreto em `CAN edit:` (path concreto = sem globs/expansões
   `*?[]{}<>`, sem espaços, sem `$`, sem control chars/separadores
   Unicode, ≤64 paths por declaração — qualquer violação MACULA a
   declaração inteira p/ `unparseable`, codex r16-r31) OU a forma
   read-only explícita
   `CAN edit: NONE-READ-ONLY` (token novo; case-insensitive; NUNCA
   entra como path no detector de colisão, por ordem de branch no
   classifier). Bloco ausente ou só-de-wildcard/placeholder =
   rejeição NOMEADA (`spawn_file_assignment_missing` /
   `spawn_file_assignment_unparseable`) — **após janela advisory
   medida** (measure-first, doutrina C5): o enforce arma somente com
   `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1`, e a janela conta como
   would-block os emits `spawn_file_assignment_recorded` com
   `path_count=0` E `path_hashes` ≠ o marcador read-only constante
   (codex r30: declarações `NONE-READ-ONLY` legítimas — o default do
   gerador sem `--files` — também emitem `path_count=0`; contá-las
   tornaria a calibração inutilizável).
   O token `none` PERMANECE placeholder dropado (classifica
   `unparseable`) — a ambiguidade era a célula a curar, não a manter.
   Discriminador de telemetria sem campo novo (allowlist intacta):
   read-only explícito grava o hash constante do token (NUL-framed,
   inalcançável de path real); ausência grava hash-set VAZIO;
   declaração TAINTED grava os hashes dos paths concretos que carrega
   (o detector de colisão continua informado) — todos com
   `path_count=0` (o sinal would-block da janela AC-2b); spawns
   BLOQUEADOS pelo enforce não gravam reserva (sem fantasma de 10min
   contra o retry corrigido).
2. **O gerador emite o bloco SEMPRE** (`inject-agent-context.sh`):
   `--files=<a,b>` → linhas `CAN edit:` concretas; sem o arg → a
   forma read-only explícita. O caminho feliz nasce conforme.
3. **Agentes de rail Workflow usam gramática REDUZIDA, validada
   PRÉ-despacho no próprio script** (mecanismo provado em
   `wf_f2707efc`: lança ANTES do spawn, custo zero): obrigatório
   `## PROMPT DEFENSE` com ≥6 bullets + `## FILE ASSIGNMENT`
   explícito (concreto ou NONE-READ-ONLY) + o marcador de HARD
   RULES do próprio workflow. `## AGENT PROFILE`/`## SKILL CONTENT`
   são DISPENSADOS — os agentes são purpose-built por design
   (⚖️ decisão 2, Owner S307: opção (a) — a gramática cheia
   quebraria as 4 skills shipadas, censo codex r2 P1).
4. **Todo retorno de subagente consumido em prompt de outro agente é
   FENCED como dado + capped** (`fenceUntrusted`, cap 24000 —
   espelho do precedente council). Truncamento **envenena o CLEAN da
   dimensão dona do shard** (⚖️ decisão 1, Owner S307: por dimensão,
   reusando o padrão finder-degradado) — nunca some silenciosamente.
   Nos sites de síntese cujo veredito é MECÂNICO por contagens, o
   truncamento degrada apenas o corpo do relatório (documentado
   inline); no nightly-hygiene, dimensão truncada força
   `skipped`→yellow por piso mecânico.
5. **Capability autodeclarada não conta como controle** (precedente
   `check_worktree_writer`; 3ª re-descoberta — agora doutrina
   escrita): um prompt que DIZ ser read-only não substitui validador,
   fence ou gate.
6. **Limitação DECLARADA**: enforcement write-time de FILE ASSIGNMENT
   não será construído — não existe primitivo de identidade de agente
   que atravesse a fronteira de spawn (`trusted_env`: "NEVER ship
   across spawn boundaries"); a autoridade residual do INJ-4 fecha
   por scoped permissions nativas (W1.3, se o probe de 5 casos
   provar) ou fica registrada como residual.

## §3 Rota de recuperação (ADR-186)

`CEO_SOTA_DISABLE=1` força advisory para TODOS os rails de spawn,
incluindo a gramática nova — rota nomeada e TESTADA no mesmo commit
(`test_check_agent_spawn_file_assignment.py::TestRecoveryRoute`). O
flip do enforce (`CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1` por default) e
o `CEO_SPAWN_OVERLAP_GUARD` (AC-2b) são cerimônia FUTURA, gated na
janela advisory (≥30d ou ≥20 sessões) com tabela would-block/TP-FP
anexada — NENHUM flip embarca neste pack (C5 measure-first).

## §4 Consequências

- (+) A claim de CLAUDE.md §4 volta a ser verdadeira (reescrita com
  precisão no closeout: AGENT PROFILE é detector de spawn nomeado,
  não requisito bloqueante).
- (+) O detector de colisão (Rail 3) passa a ver TODOS os spawns
  nomeados (`path_count=0` na omissão) — pré-condição do AC-2b
  satisfeita.
- (+) O rail Workflow deixa de ser fan-out descoberto: os 4 scripts
  shipados validam a gramática reduzida antes de cada `agent()`
  (bloco COMMON byte-idêntico nos 4 — divergência é diff visível).
- (−) Callers ad-hoc quebram se omitirem o bloco APÓS o flip — pago
  com a janela advisory + gerador curado + rota de recuperação.
- (−) **R-SEC4 (residual aceito)**: fence é moldura, não autoridade —
  não reduz a autoridade que um ponteiro hostil DIRIGE (um
  evidence_pointer malicioso ainda leva o refuter a abrir o arquivo
  apontado). Registrado aqui e no ADR-089-AMEND-1.
- (−) O validador pré-despacho vive em cada script (prompt-level,
  ADR-136): um workflow NOVO que esqueça o bloco COMMON nasce
  descoberto — mitigação: o self-check de skills de workflow e a
  revisão de cerimônia; cura estrutural (gate no substrato) fica
  para quando o harness expuser hook de pré-spawn no rail Workflow.
- (−) **R-CAL1 (residual declarado, codex r28 P2):** o emit advisory
  `spawn_file_assignment_recorded` acontece no rail (cedo em decide());
  um spawn nomeado sem FA que TAMBÉM falha um gate posterior
  (prompt-defense/skill) grava um would-block sem despachar — a janela
  advisory pode SOBRE-contar. Direção conservadora por construção
  (atrasa o flip, nunca acelera); a cerimônia do flip (tabela
  would-block/TP-FP) filtra por `veto_triggered` adjacente na mesma
  janela; mover o emit para o allow-path final fica registrado como
  refinamento do flip, não deste pack.
- (−) **R-SEC6 (fronteira declarada, codex r25→r33):** o parser de
  FILE ASSIGNMENT implementa um SUBCONJUNTO DOCUMENTADO de CommonMark
  (headers `##` case-insensitive indent 0-3; linhas de lista `-*+`
  indent 0-3 com whitelist fechada de formas; fences coluna-0 e
  indentados 1-3 mascarados; paths sem whitespace/globs/`$`/controles;
  ≤64). Oito rodadas de rail (r25-r33) provaram que variantes de
  sintaxe CommonMark são um alvo INFINITO para um parser de regex —
  cada regra enumerada gera a próxima variante. A fronteira REAL,
  aceita: (a) prompts canônicos nascem do GERADOR (que emite só o
  subconjunto); (b) linhas de lista não-reconhecidas MACULAM
  fail-closed; (c) variantes de sintaxe além do subconjunto que
  ESCAPEM ao taint são extensão deste residual — a cura estrutural é
  um parser Markdown real (biblioteca), vetado pelo constraint
  stdlib-only; reavaliar SE um incidente real da classe aparecer.
- (−) **R-SEC5 (residual declarado, codex r19):** markdown é FLAT — um
  bloco `## FILE ASSIGNMENT` citado como EXEMPLO não-fenced dentro do
  `## TASK` é estruturalmente idêntico a um bloco apendado por um
  caller legítimo (o fluxo /spawn apenda DEPOIS do TASK por design, o
  que impede restringir por posição). A fronteira real é a convenção
  já respeitada pelo parser: conteúdo em code fences é MASCARADO
  (`_strip_fenced_and_comments`) — exemplos de blocos DEVEM ir em
  fences (regra registrada nos callers). Quem monta o prompt é o
  CEO/gerador (superfície trusted); TASK derivado de conteúdo
  untrusted é coberto pelo PROMPT DEFENSE + fences de ingest.
