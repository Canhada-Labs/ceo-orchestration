---
id: PLAN-178
title: Method currency — auditoria MAST-14 + injeção inter-agente, adoção de substrato 2026, e regras derivadas da pesquisa S305
status: executing
reviewed_at: 2026-08-13
reviewed_by: "Owner — ratificação via AskUserQuestion (S305): 'Ratificar reviewed (Recomendado)'. W0 executa em seguida (read-only); W1+ exige /debate start PLAN-178."
executing_since: 2026-08-13
created: 2026-08-13
owner: CEO
depends_on: []
budget_tokens: 150-300k (W0 60-100k; W1 50-120k; W2 20-40k; W3 20-40k)
budget_sessions: 2-3
context_risk: low
external_wait: "nenhum — Owner autorizou execução pré-rc.4 (S305). Nenhuma wave toca superfície canônica sem cerimônia própria."
tags: [research, governance-audit, substrate, security, seed]
---

# PLAN-178 — Method currency: fechar os gaps que a pesquisa S305 achou

> **SEMENTE (S305, 2026-08-13).** Duas rodadas de pesquisa
> academia-vs-framework (gauntlet-loop S304 + varredura completa S305).
> Autoridade das referências: `PLAN-178/research-S305.md` (fonte
> ÚNICA; planos apontam, nunca duplicam números — lição 3× "cura no
> corpo ≠ referências"). Conclusão central: o framework já implementa
> a versão forte da maioria das famílias (cross-vendor > fresh-context;
> MEA ≈ Plan→Execute→Verify); os gaps reais são QUATRO e cabem aqui.
> Dono único: itens que fundamentam planos existentes (E6/cascata →
> 172; context-reframe → 175; T/P → 176) moram NAQUELES planos — este
> plano NÃO os re-executa.

## Context

- A classe de falha dominante da literatura (MAST: spec-ambiguity +
  coordenação = 79%) é exatamente a que nossos gates atacam — mas
  nunca mapeamos formalmente check-a-check contra os 14 modos.
- A literatura de segurança inter-agente documenta o confused deputy
  entre agentes (injeção via par "confiável" com taxa de sucesso muito
  superior à direta). Nossos scanners (injection_patterns, shards
  ADR-141 como DADO) cobrem parte; a classe "trust propagation entre
  spawns" não tem auditoria dedicada.
- O substrato Claude Code 2026 (versão que o Owner instalou) traz
  features que o framework usa parcialmente (Workflow em 4 skills) ou
  ignora (cost-attribution nativa, scoped permissions, nested
  subagents, dreaming). Substrate-watch vigia DRIFT, não ADOÇÃO.
- Da análise gauntlet (S304): 2 regras extraíveis com respaldo
  empírico ainda vivem só em memória, não em protocolo.

## Waves

### W0 — Auditoria MAST-14 + injeção inter-agente (L2, read-only, 1 sessão)

Mapear os 14 modos de falha MAST + as classes de injeção inter-agente
(confused deputy, trust-authorization mismatch, contágio via shared
memory) contra nossos controles, com evidência arquivo:linha para cada
célula (coberto / parcial / gap). Formato: shards ADR-141; agentes não
escrevem arquivo (confinamento ADR-136-AMEND-1); relatório é retorno.

- Saída: `PLAN-178/mast-coverage-table.md` (escrito pelo CEO a partir
  dos shards) — tabela 14+N linhas × {controle, evidência, status}.
- Cada GAP acionável vira item L2/L3 com dono proposto (aqui ou em
  plano existente — sem double-booking).
- **Positive control da auditoria:** injetar 1 modo sabidamente
  coberto (ex.: spawn sem FILE ASSIGNMENT ⇒ check_agent_spawn bloqueia
  — live-fire, não fixture) e 1 sabidamente NÃO coberto (esperado:
  gap) — auditoria que dá "tudo verde" sem controle é instrumento com
  pergunta envelhecida.
- Kill: se a tabela der 100% coberto SEM nenhum gap, parar e
  desconfiar do instrumento (lição feedback-instrument-green).

### W1 — Adoção de substrato 2026 (L2 por item; qualquer wiring novo em settings = L3)

Triage das features novas, cada uma com PROBE live-fire primeiro
(disciplina W4.1.0/W4.2.0 do PLAN-169 — evidência antes de doc):

1. **Workflow para fan-outs recorrentes [L2] (emendado r1 — A2/A7):**
   piloto = **re-auditoria MAST recorrente** (read-only por natureza;
   transforma `mast-coverage-table.md` de foto em instrumento). O
   re-pass de release está DESCARTADO como piloto (não usa Task tool —
   é bash+codex subprocess — e é o maior blast radius do repo).
   **Desfecho do gate JÁ CONHECIDO** (probe live-fire `wf_d7af49d9`:
   `blocked=false` — o rail Workflow NÃO passa pelo
   `check_agent_spawn`; consistente com a evidência preliminar
   PLAN-169:470-476). **Ramo vermelho (escrito):** (a) migração de
   qualquer fan-out que ESCREVA fica PROIBIDA até existir gate no
   rail; (b) o piloto read-only prossegue COM validador de
   conformidade PRÉ-despacho no próprio script de workflow (função
   chamada antes de cada `agent()` — implementável hoje, sem depender
   do harness); (c) o gap está registrado no adendo S305-b da tabela
   W0 com dono = Lote B. Reenquadramento (r1): o probe não autoriza
   migração — ele AUDITOU 4 skills shipadas que já rodam do outro
   lado da fronteira.
2. **Cost-attribution nativa [L2] (emendado pós-codex; probe S305
   POSITIVO):** fonte nativa CONFIRMADA em disco — fingerprint:
   `subagents/agent-a<name>-<hash>.jsonl` (blocos `usage` por turno:
   input/cache_creation/cache_read) + `.meta.json`
   ({model, name, spawnDepth, taskKind}). `agent-budget` estende o
   precedente do próprio Step 3b (O3): as duas fontes impressas lado
   a lado com breakdown POR SPAWN e por categoria (Task vs Workflow);
   janela por N≥50 eventos cobrindo os DOIS caminhos; switch só por
   divergência máxima POR CATEGORIA (ver AC-3). Nunca substituição
   silenciosa.
3. **Scoped permissions em spawns [L3 — toca settings] (emendado r1 —
   A3):** defesa em profundidade SOB os hooks, nunca substituto
   (precedente em casa: settings.json:757 documenta managed-policy
   quebrada ⇒ enforcement de modelo DESLIGA — fail-open no harness).
   **Probe de 5 casos com controle negativo nomeado, ANTES de
   desenho:** (i) positivo: scope `Edit(A)` nega `Edit(B)`; (ii) fuga
   por Bash (`python3 -c`, `tee`, `>`) — se passar, o scope é
   tool-scoped e NÃO fecha INJ-4 (lição S290: deny por ferramenta é
   teatro); (iii) hooks fora do caminho — medir o que o NATIVO bloqueia
   sozinho; (iv) managed-policy inválida — o scope sobrevive?; (v)
   auto-declaração — o agente amplia o próprio scope? **Reversibilidade
   por item (template = W1.2):** fingerprint do probe (versão+shape),
   rota de fallback, entrada no substrate-watch. Fronteira: decidir na
   abertura do Lote B se este item é absorvido pelo W4-C/169 (dono das
   4 superfícies de settings) ou nasce aqui. Cerimônia própria
   obrigatória (settings é canônico).
4. **Nested subagents + agent teams: ESTUDO apenas [L2 read-only].**
   Teams full-mesh fica FORA (MAST: coordenação é onde quebra; lição
   S284 clobber). Saída = memo go/no-go com condições.

### W2 — Regras derivadas da pesquisa (L2, docs de protocolo; advisory até ratificação)

1. **Critic fresco por retry** nos re-passes internos Claude-side
   (retargetado r1 — A6): a regra landa em `DEBATE-SCHEMA.md` +
   `.claude/commands/debate.md` por PR normal (não existe template
   vivo `run-*-review.sh`; as cópias em PLAN-166/ são evidência
   imutável). Se ratificada como linha de `PROTOCOL.md`, essa linha
   entra no Lote B (PROTOCOL.md é canônico). Conteúdo: o agente que
   criticou o draft N não re-julga o N+1 (Codex já é fresco por
   processo; a regra fecha o lado Claude), SEM contradizer a
   continuidade r1→r2 do debate (que é sobre rounds de crítica, não
   sobre re-julgar a própria rejeição).
2. **Barra-por-exemplar para superfícies de prosa** (README,
   announcement kit): o revisor compara contra 1 exemplar real
   nomeado, às cegas, em vez de rubrica abstrata.
3. **Registro de fronteira:** doutrina verificador-primeiro
   (candidatos paralelos > rodadas seriais) fica REGISTRADA como
   motivação do gate barato §2/PLAN-172 — execução mora lá; teto de
   rodadas já é mecanismo no tiering §4/PLAN-172. Este plano não
   duplica.

### W-C — Lote de curas do W0 (estrutura fixada pelo debate r1 — A4/A5/A9)

**Lote A — PR normal, sem cerimônia (superfícies não-canônicas):**
- C3 lint de vacuidade em `ceo-boot.py` checks: DUAS pernas — R1 lint
  "discrimina ≥2 status" (protótipo v1 validado: 8 candidatos) com
  waiver `# CEO-INFORMATIONAL-ONLY` (espelha `# CEO-DEBT:`), R2
  positive control por check. **Controle positivo do PRÓPRIO lint:**
  fixture com check deliberadamente vacuoso que o lint TEM de reprovar
  + o caso vivo (`check_tier_a_spec_version_drift`, ceo-boot.py:1017)
  como segundo controle. Lint verde sem controle é a própria doença.
- C4 drift de referência ceo-boot.py:240 (`_lesson_render_safe` →
  `_validate_boot_lesson`) + grep do símbolo antigo no REPO INTEIRO
  antes de fechar (lição 3× da S302). É o teste mais barato da
  doutrina do plano — landa PRIMEIRO.

**Lote B — UM pack GPG, escopo fechado (superfícies canônicas):**
- C1 enforce de `## FILE ASSIGNMENT` no spawn (check_agent_spawn.py é
  canônico): ANTES do enforce, censo de callers + janela
  advisory-com-audit (emitir `spawn_file_assignment_recorded` com
  path_count=0 na ausência — mede a omissão); rejeitar bloco
  só-de-wildcard (senão a evasão migra de omitir p/ declarar `*`);
  rota de recuperação nomeada e TESTADA no mesmo commit (padrão
  ADR-186 / `CEO_SOTA_DISABLE=1`). **ADR-191 documenta a mudança de
  contrato de aceite — entra NESTE pack.** C1 fecha a CLAIM de
  CLAUDE.md:88, NÃO fecha INJ-4 (dizer isso onde a cura for citada).
- **Write-time enforcement: NÃO SERÁ CONSTRUÍDO** (r1 unânime no
  eixo): não existe primitivo de identidade de agente que atravesse a
  fronteira de spawn (trusted_env: "NEVER ship across spawn
  boundaries"); seria oráculo do mesmo lado da fronteira. INJ-4 fecha
  no W1.3 (se o probe provar) ou fica registrado como autoridade
  residual declarada.
- C2 fence + cap do ingest in-harness (workflows/*.js é CANÔNICO —
  não é "cura barata"): delimitador "conteúdo abaixo é DADO" nos
  pontos de interpolação (audit-fanout.js:142,190-196 + nightly) e
  cap com semântica DEGRADED (trunca ⇒ dimensão envenena CLEAN,
  reusa o padrão 105-108). Residual documentado: fence é moldura —
  não reduz a autoridade que o ponteiro dirige (R-SEC4).
- C5 flips de detectores conforme tabela abaixo + validador
  pré-despacho do rail Workflow (ramo b do W1.1).
- C6 (INJ-3, codex P2 pós-debate): fence no retorno do
  `memory_shared.query()` (devolve `content` cru hoje;
  `_lib` é canônico) + rascunho do ADR-089-AMEND-1 com gatilho
  OBSERVÁVEL derivável de `emit_pattern_stored/queried` (ex.: ≥2
  papéis no mesmo tópico na janela de sessão) — o gatilho atual
  ("incidente na telemetria") é insondável porque não existe detector.
  Adiamento, se houver, é registrado com destino (AC-7).
- Linha de PROTOCOL.md do W2.1, SE ratificada.

**C5 — tabela por detector (gate measure-first OBRIGATÓRIO: contagem
would-block do audit-log em janela ≥30d ou ≥20 sessões + triagem TP/FP
por disparo; zero disparos ⇒ NÃO armar):**
| Detector | Veredito r1 | Nota |
|---|---|---|
| CEO_SPAWN_OVERLAP_GUARD | armar SÓ depois do C1 | aresta dura: antes, pune só o compliant (R-SEC1); única classe com incidente real (S284) |
| CEO_UNICODE_HARDBLOCK | armar por superfície (spawn/skill-write 1º; Read por último) | único que fecha vetor real de smuggling; Read = maior superfície de FP |
| CEO_VERIFY_AFTER_EDIT_BLOCK | armar (baixo risco) | continueOnBlock:true — custo é latência, não travamento |
| CEO_SPAWN_TOOL_SCOPE | armar mas NÃO contar como controle | lint prompt-vs-prompt; quem não declara escapa |
| CEO_CONFIDENCE_ENFORCE | NÃO armar neste lote | block duro sobre saída; exige triagem TP/FP antes; Owner-only flip (ADR-019) |
| CEO_SUBAGENT_FABRICATION_BLOCK | não contar como cura | NÃO bloqueia (escala p/ systemMessage) — nome mente |
| CEO_SPAWN_DEPTH_GUARD | entra na tabela (7º) | pré-condição do estudo W1.4 (nested) |

### W3 — Estudo dreaming/curadoria de memória (L2 read-only, 1 sessão)

Avaliar a curadoria de memória agendada do substrato ("dreaming")
contra o gated-learning loop do PLAN-154 (default-OFF por design):
sobreposição, fronteira de confiança (memória é superfície de injeção
— render como DADO, nunca instrução), e se ativação parcial do
PLAN-154 (CEO_LEARNING_BOOT_LESSONS=1) é melhor que adotar o nativo.
Saída = memo com recomendação; qualquer ativação é decisão do Owner.

### Registro de execução — Lote B autorado e landado (S307, 2026-08-14)

> **Decisões ⚖️ ratificadas pelo Owner (S307, AskUserQuestion):**
> (1) truncamento de ingest envenena CLEAN **por dimensão** (reusa o
> padrão finder-degradado); (2) gramática **REDUZIDA** para agentes de
> workflow (PROMPT DEFENSE ≥6 + FILE ASSIGNMENT explícito + marcador
> de HARD RULES; AGENT PROFILE/SKILL dispensados); (3) fix do
> `check_budget` (cap INERTE: allow-precoce com ≥2 planos ativos)
> **entra neste pack** (tie-break determinístico executing>reviewed>
> draft, depois maior NNN; breadcrumb nomeia a seleção).
>
> **Conteúdo do pack:** C1 (gramática `NONE-READ-ONLY` + advisory-first
> `path_count=0` + rota de recuperação testada + gerador emite o bloco
> SEMPRE com `--files=`), C2 (fenceUntrusted + cap 24000 em
> audit-fanout/nightly-hygiene + recon do eval; council já conforme),
> validador pré-despacho nos 4 workflows (bloco COMMON byte-idêntico,
> provado por teste node), C6 (fence no `query()` + teste em
> `_lib/tests/` canonical-guarded), ADR-191 + ADR-089-AMEND-1 ACCEPTED,
> check_budget curado com 3 testes convertidos do skip antigo + 3
> novos de tie-break. Derivadas: env-inventory regen (496 vars — cura
> 28 drifts pré-existentes de commits anteriores + 1 novo), contagens
> ADR 190→192 em 9 superfícies (verify-counts exit 0 verdadeiro).
> **NENHUM flip C5 neste pack** (measure-first: janela advisory conta
> `spawn_file_assignment_recorded` com `path_count=0`).
>
> **Pendências que este registro NÃO fecha:** positive controls
> live-fire pós-land (AC-6/C1: spawn sem FA emite path_count=0 no
> audit real; C2: fence visível num run real; C6: query() devolve
> fenced) e a reescrita PRECISA de CLAUDE.md §4 no closeout.

### Registro de execução — fechamento parcial (S314, 2026-08-19)

O plano estava `executing` com o corpo parado desde `2fa18f8` (08-16)
enquanto o trabalho já tinha landado. Este registro fecha o que tem
evidência no disco e nomeia dono+gatilho do que segue aberto:

**Fechados nesta entrada (evidência path:line/sha):**
- **AC-1** — tabela em `PLAN-178/mast-coverage-table.md` (6 coberto /
  10 parcial / 4 gap) com controle positivo E gap-conhecido presentes;
  adendo S305-b. Não é tudo-verde ⇒ instrumento crível.
- **AC-2** — probe `wf_d7af49d9` ⇒ `blocked=false` registrado (gap
  vivo, adendo S305-b); ramo vermelho em vigor (fan-out que ESCREVE
  não migrou); validador pré-despacho nos 4 workflows shipados
  (bloco COMMON, provado em `wf_f2707efc`).
- **AC-2b** — par ordenado respeitado: C1-spawn landou em `2fa18f8` e
  `CEO_SPAWN_OVERLAP_GUARD` segue NÃO armado (nenhuma referência viva
  em settings; janela advisory correndo via
  `spawn_file_assignment_recorded`, wired em `check_agent_spawn.py`).
- **AC-4** — W2 inteiro nos docs de protocolo: crítico fresco em
  `DEBATE-SCHEMA.md:73` (W2.1) e barra-por-exemplar marcada ADVISORY
  em `DEBATE-SCHEMA.md:81-83` (W2.2). Diff mínimo, aguarda
  ratificação do Owner como o AC pede.
- **AC-5** — memos entregues com go/no-go explícito:
  `PLAN-178/w14-nested-teams-memo.md` (W1.4) e
  `PLAN-178/w3-dreaming-memo.md` (W3); `w12-native-cost-probe.md`
  cobre o W1.2.

**Abertos com dono e gatilho (nada é dropado em silêncio):**
- **AC-6 [P0]** — os 3 positive controls live-fire pós-land (C1
  path_count=0 no audit REAL; C2 fence visível num run real; C6
  query() fenced) + tabela C5 would-block por detector. Dono: sessão
  (são runs, não assinaturas). Gatilho: próxima sessão com janela de
  spawns reais. Enquanto aberto, `executing → done` está bloqueado.
- **AC-3 [P1]** — agent-budget com as DUAS fontes por spawn/categoria;
  exige janela N≥50 cobrindo os dois caminhos. Dono: sessão; gatilho:
  acúmulo da janela (não dias corridos).
- **AC-2c [P1]** — fingerprint+fallback+substrate-watch por item W1
  adotado: pendente até prova (template = W1.2).
- **W1.3 (scoped permissions, L3)** — **correção de fronteira:** o
  guard-rail mandava decidir absorção vs pack próprio NA ABERTURA do
  Lote B; o Lote B abriu (`4940fc7`) e landou (`2fa18f8`) sem essa
  decisão registrada, e o escopo do W4-C/169 não lista scoped
  permissions. Registrado AGORA como pendência com destino nomeado:
  a decisão (absorver no W4-C/169 ou pack próprio) entra na abertura
  do W4-C — quem abrir o W4-C herda este item explicitamente. Toca
  `settings.json` ⇒ cerimônia GPG do Owner no ato.

## Acceptance criteria

- [x] AC-1 [P0] (fechado S314 — ver Registro de fechamento parcial)
      Tabela MAST+injeção completa com evidência
      arquivo:linha por célula E os 2 positive controls executados
      (1 coberto live-fire, 1 gap esperado). Tudo-verde-sem-gap ⇒
      FALHA do AC (instrumento suspeito).
- [x] AC-2 [P0] (emendado r1; fechado S314) Positive control do rail Workflow
      EXECUTADO: `wf_d7af49d9` ⇒ `blocked=false` (gap vivo, adendo
      S305-b). Ramo vermelho em vigor: fan-out que ESCREVE não migra;
      piloto read-only (re-auditoria MAST) só com validador
      pré-despacho no script; gap com dono no Lote B.
- [x] AC-2b [P0] (fechado S314) Aresta de dependência: `CEO_SPAWN_OVERLAP_GUARD` NÃO
      é armado antes do C1-spawn landado (par ordenado, não lista).
- [ ] AC-2c [P1] Cada item W1 adotado carrega fingerprint do probe +
      fallback + entrada substrate-watch (template = W1.2).
- [ ] AC-3 [P1] (emendado pós-codex) agent-budget imprime as DUAS
      fontes (nativa + audit-log) com breakdown POR SPAWN e por
      categoria (Task vs Workflow); janela fecha com N≥50 eventos
      COBRINDO os dois caminhos (não dias corridos); switch de fonte
      só com divergência MÁXIMA por categoria ≤10% — agregado não
      basta (erros compensatórios passam no agregado; opts.model é
      INERTE no Workflow, as economics diferem por caminho).
- [x] AC-4 [P1] (fechado S314) Regras W2 landadas nos docs de protocolo com diff
      mínimo e marcadas ADVISORY até ratificação do Owner.
- [x] AC-5 [P2] (fechado S314) Memos W1.4 e W3 entregues com recomendação explícita
      go/no-go + condições.
- [ ] AC-6 [P0] (codex r1-pós-debate, P1) **Ledger de curas W-C — cada
      disposição FECHA com evidência própria:** C1 = hook bloqueia
      spawn sem FILE ASSIGNMENT (positive control live-fire) + rota de
      recuperação testada no mesmo commit + reescrita PRECISA de
      CLAUDE.md:88 no closeout (as 3 seções nomeadas com seu status
      real — verificada contra o hook, não contra a intenção); C2 =
      fence visível nos 3 consumidores + teste de que shard truncado
      envenena CLEAN; C3 = lint landado com fixture-reprovada + caso
      vivo curado (branch red real em spec_version_drift) + waivers
      justificados; C4 = símbolo morto zerado no repo (grep limpo);
      C5 = tabela de disposição com contagem would-block por detector
      (armado, não-armado ou adiado — TODOS com razão registrada).
      Nenhum AC deste plano fecha "vacuamente": disposição sem
      evidência = plano aberto.
- [x] AC-7 [P1] (codex P2) C6/INJ-3: ADR-089-AMEND-1 rascunhado com
      gatilho OBSERVÁVEL (derivável de emit_pattern_stored/queried) +
      fence no retorno do query() incluído no Lote B (memory_shared.py
      é _lib canônico). Se o Owner adiar, o adiamento é registrado com
      destino — nunca dropado em silêncio.

## Guard-rails

- Read-only por padrão; NENHUMA superfície canônica muda sem cerimônia
  própria (Lote B é o pack único; W1.3 é L3 explícito).
- Referências/números de literatura só em `research-S305.md` — corpo
  de plano e docs públicos não herdam números (doutrina §3/PLAN-172).
- Sem double-booking: cascata→172/176, context-reframe→175,
  best-of-N-gate→172 §2, fleet-currency→176. Este plano só cruza
  referências.
- **Fronteira 178↔169 W4/W4-C, item a item (emenda r1 — A1):** probes
  de rail Workflow → PLAN-169 W0.0/W4.2.0 é DONO (o 178 CONSOME o
  resultado; o probe `wf_d7af49d9` é evidência compartilhada, não
  re-execução); settings nas 4 superfícies (dogfood/adopter/template/
  install) → padrão do W4-C/169; W1.3 decide absorção vs pack próprio
  NA ABERTURA do Lote B; W1.2/W1.4/piloto-MAST → 178. **Tensão de
  direção declarada:** `disableWorkflows` fail-closed como default de
  ADOPTER (169) coexiste com aprofundamento de Workflow no DOGFOOD
  supervisionado (178) — não são contraditórios, são camadas.
- **Distinção dogfood vs adopter em TODO item do W1** (r1): mudança
  que propaga a adopter passa por `templates/settings/*` (canônico E
  produto); mudança dogfood-only fica no arquivo vivo — nomear qual é
  qual em cada AC.
- **Freeze (análise mecânica, substitui "Owner relaxou" — A8):**
  `OWNER-GA-CUT.sh` compara o delta `rc..HEAD` contra conjunto
  fechado; a rota legal deste plano é SEQUÊNCIA: os arquivos do 178
  landam ANTES do corte da rc.4 (ficam DENTRO da tag) e o
  `OWNER-GA-CUT-rc4.sh` retargetado (W2/PLAN-177) computa o delta a
  partir da rc.4. Invariante: **NADA landa em main entre a tag rc.4 e
  o GA.**
- Toda env nova em `env-inventory.json` no mesmo commit (R-SEC12) —
  ciente (r1) de que o check hoje é `::warning`; escalar para
  bloqueante-escopado-no-diff é decisão da abertura do Lote B.

## Debate

L3 pelo conjunto (W1.3 toca settings; Lote B toca hooks/workflows/
settings canônicos): `/debate start PLAN-178` obrigatório antes do W1.
W0 pode executar direto (read-only + shards). **Executado 2026-08-13:
round 1 com 3 críticos (3× ADJUST) ⇒ consensus PROCEED com A1-A9
aplicadas; o piloto W1.1 é a RE-AUDITORIA MAST (read-only), NÃO o
caminho de release — a referência anterior a "spawn de release" está
superada pelo consenso (ver round-1/consensus.md).**
