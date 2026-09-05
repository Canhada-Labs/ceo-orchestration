---
plan: PLAN-186
round: 4
rounds_synthesized: [round-4]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "NENHUMA mudança no arquivo do plano — os três críticos confirmaram o MODELO (C-K3 seis sítios, C-K4 default oposto, C-K5 CONSUMES:, C9 custo fixo); todos os ajustes são no TEXTO que o pack W5 entrega"
  - "pack W5 — CHANGELOG.md: prosa quebrada (parêntese órfão + frase sem sujeito) que o gate changelog/header é ESTRUTURALMENTE cego a ver; DESIGN §9 item 9 declara CURADO o que os bytes contradizem"
  - "pack W5 — debate/proposal.md: errata do nome de evento `no_spawn_judgment_carve_out` → `spawn_judgment_carve_out` (invertido, curado na r10)"
  - "pack W5 — check-classifier-cases.py: quarta cópia da tabela §2b (.claude/commands/effort.md) entra no oráculo, ou effort.md perde a afirmação de auto-suficiência"
  - "pack W5 — carve-out ganha limite de CARDINALIDADE nos 4 sítios canônicos"
  - "pack W5 — os ~95k ganham a POPULAÇÃO medida (general-purpose, sem skill inline ⇒ PISO para spawn nomeado) nos sítios que os citam"
  - "pack W5 — hook check_anti_ceo_overhead.py: carve-out por PRODUTO + cláusula de routing table; distinção medição/inferência"
  - "pack W5 — arquivo PLAN-186-FOLLOWUP-parallelization-action-register.md criado; materiais de cerimônia construídos (item R4 do CEO)"
synthesized_at: 2026-09-05T02:45:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-186 W5 — consenso do round 4 (texto + reconciliação skill/hook)

Três críticos, três `ADJUST`, **5 itens BLOCKING somados** (Critic-A 2, Critic-B 1,
Critic-C 2; um deles compartilhado). Nenhum pediu `REJECT` e **nenhum contestou o
modelo**: as decisões dos rounds 1-3 (seis sítios do Step 0, default oposto da skill,
`CONSUMES:` na gramática, custo fixo como 3.º critério) sobrevivem intactas. O
`ADJUST` deste round é inteiramente sobre o TEXTO que aterrissa.

Verifiquei em disco, na árvore APLICADA (shadow do builder, `HEAD 2292979` + patch,
28 paths `porcelain`), cada claim antes de promovê-la. Comandos e resultados citados
por `file:line`.

## Consensus findings (2+ agents)

### C1 — BLOCKING — o registro do round cita um nome de evento que a árvore REFUTOU (Critic-A, Critic-C)

`<SP>/debate-w5/round-4/proposal.md:74` diz «(`no_spawn_fixed_cost`,
`no_spawn_judgment_carve_out`)». A skill aplicada usa dois nomes e só o primeiro
bate: `.claude/skills/core/parallelization-by-default/SKILL.md:270` =
`no_spawn_fixed_cost` (correto), `:272` = **`spawn_judgment_carve_out`**, sem `no_`.
A própria skill registra por quê: o primeiro rascunho o nomeava `no_spawn_...` e isso
estava INVERTIDO — o nome descrevia a branch que SEMPRE despacha (rail r10, P1).

**Consequência:** arquivar este round sob `.claude/plans/PLAN-186/debate/round-4/`
põe a decisão e a versão refutada dela na MESMA pasta de plano, e o round-4 é o
material que o AC-7 cita como registro de debate. Errata de uma linha.

### C2 — P2 — o hook é o único dos 7 sítios que abandona o enquadramento por PRODUTO (Critic-A, Critic-C)

Censo meu sobre a árvore aplicada: `PROTOCOL.md:210,251`; `.claude/team.md:484,632,660`;
`.claude/commands/spawn.md:151`; `.claude/skills/core/ceo-orchestration/SKILL.md:494`;
`parallelization-by-default/SKILL.md:45,94,142` — todos dizem «product is INDEPENDENT
JUDGMENT», e os canônicos acrescentam «matching a ROUTING TABLE row … is NOT that
carve-out». O hook (`check_anti_ceo_overhead.py`, `_STEP0_DOCTRINE`) diz apenas
«Check 2 covers DISCRETIONARY spawns only: a mandatory reviewer is out of scope,
never folded in» — sem PRODUTO e sem a cláusula da routing table, que é exatamente
a leitura errada que a r8 (P1) curou nos outros seis. Critic-C acrescenta a segunda
perda no mesmo bloco: «the measured mean over 40 trivial agents» larga a distinção
MEDIÇÃO/INFERÊNCIA que `PROTOCOL.md:236-241` e a skill carregam com cuidado.

**Agravante verificado:** é a superfície de MAIOR leitura em voo — impressa no meio da
sessão, a única que um adopter vê sem abrir um `.md`.

### C3 — P3 — o pack não tem materiais de cerimônia (Critic-B, Critic-C)

`ls <PK>/w5-doctrine/` não lista `materials/`. Já é o item R4 aberto do CEO; os dois
críticos o nomeiam para que a restrição de UM commit fique escrita: o bump 198→201
toca nove sítios em três geradores, e o baseline `EXPECTED_*` tem de ser GERADO
rodando os geradores, nunca listado à mão (lição S328/S329 já em `CLAUDE.md` §5).

## Single-agent insights kept

1. **K1 (Critic-A) — BLOCKING — `CHANGELOG.md` entrega prosa quebrada e o DESIGN
   declara a classe CURADA.** Verificado: o blockquote aplicado lê «… refuses both a
   stale numeral and a rephrased label. Label / v1.3.0: 166 skills, 27 slash commands,
   201 ADRs, 71 `_lib` modules) are reproducible …» — parêntese ÓRFÃO e frase «Label
   v1.3.0: … are reproducible» sem sujeito. Balanço mecânico do bloco: fecha mais do
   que abre (`tr -cd '()'` sobre as linhas 8-20 = `())`). O `(` de «(as of v1.3.0:» foi
   removido pela cura da r9; o `)` sobrevive porque a regra `changelog/header` do
   `verify-counts.sh` EXIGE o rótulo contíguo ao `)` — o gate é verde SOBRE a prosa
   quebrada e **nenhum gate da bateria consegue vê-lo**. E `<PK>/w5-doctrine/DESIGN-w5-doctrine-S344.md:407-408`
   marca o item 9 riscado, «CURADO na r9 (lane B, P1)»: o pack embarca uma afirmação
   FALSA sobre a própria árvore. Já era o item R1 do CEO; aqui fica confirmado que
   sobreviveu à derivação final.
2. **K2 (Critic-B) — BLOCKING — a tabela §2b vive em QUATRO cópias e o oráculo lê
   TRÊS, e a cópia sem oráculo é a ENTREGUE.** Verificado:
   `.claude/plans/PLAN-186/w5/check-classifier-cases.py:113-115` lê exatamente
   `REL_PLAN`, `REL_DOC`, `REL_FIXTURE`; `grep effort.md` sobre o oráculo é VAZIO. O
   patch acrescenta uma reprodução R1-R7 digitada à mão em `.claude/commands/effort.md:102-108`
   sob a frase `:75` «this table is the operable rule and needs no other file». As
   células CONCORDAM hoje (conferi contra `PLAN-186-orchestrator-operating-model.md:106-112`:
   R1 `xhigh`, R2/R3/R4 `high`, R5/R6 `max`, R7 `high`), então ainda não há dois sítios
   discordando — há um duplicado sem mecanismo. **A assimetria é o que torna isso
   bloqueante:** `.claude/commands` É entregue (`scripts/_framework_manifest_set.sh:181`)
   e `docs/task-classifier-2b.md` NÃO é (`grep task-classifier` sobre manifesto +
   `install.sh` + `delivery-routes.tsv` = 0 hits), logo a cópia sob o oráculo é
   framework-only e a cópia SEM oráculo é a autoritativa numa árvore instalada — e o
   desempate do próprio `effort.md:98` («§2b wins») é inutilizável por um adopter que
   não tem nem o plano nem o doc. Classe já paga aqui: «verify-counts não cobre
   ARCHITECTURE/GUIA/FAQ/npm-README ⇒ drift silencioso».
3. **K3 (Critic-C) — BLOCKING — o carve-out não tem limite de CARDINALIDADE.**
   Verificado: `grep -E 'second reviewer|more than one|cardinal|redundan'` sobre os 4
   sítios canônicos = **0 hits**. O texto isenta a CLASSE «julgamento independente», não
   «o revisor EXIGIDO». Três refutadores em paralelo — doutrina desta casa, registrada
   em `CLAUDE.md` §5 (lição S344: «refutação = 3 fornecedores em paralelo») — são
   3 × ~95k ≈ 285k de custo fixo que o Check 2 está PROIBIDO de olhar. O critério vira
   decorativo por multiplicação sem que uma linha do texto seja violada. Cura = uma
   cláusula: a isenção cobre o revisor EXIGIDO; um segundo revisor do MESMO produto
   volta ao Check 2.
4. **K4 (Critic-C) — BLOCKING — a população medida não é a população governada.** O
   número veio de agentes `general-purpose`, `effort: low`, tarefa de 3 comandos Bash
   (`.claude/plans/PLAN-186/w0/concurrency-probe-S339.md` §Método); o Step 0 governa
   spawn NOMEADO, que carrega `AGENT PROFILE` + `SKILL CONTENT` inline + `PROMPT
   DEFENSE` + `FILE ASSIGNMENT` (`CLAUDE.md` §4). É um PISO da classe mais barata
   aplicado a uma classe de prefixo estritamente maior. O viés tem sinal CONHECIDO —
   SUBESTIMA, logo o Check 2 SUB-bloqueia, errando contra a quota, que é a moeda que o
   PLAN-186 escolheu — e **nenhum sítio declara a classe de agente**. A procedência
   («aggregate over n», «fixed-pre-work = INFERENCE») está feita e é boa; falta a
   POPULAÇÃO. Cura = uma cláusula nos sítios que citam os ~95k.
5. **K5 (Critic-C) — P2 — a dívida do evento nasce sem dono e sem instrumento.**
   Verificado por AST: `_KNOWN_ACTIONS` tem **331** entradas e
   `parallelization_recommended` **não é membro** (`.claude/hooks/_lib/audit_emit.py`).
   A nota da skill é honesta ao declarar o evento não-emissível, mas
   `FU-PARALLELIZATION-ACTION-REGISTER` aparece em **exatamente 1** lugar da árvore
   (`parallelization-by-default/SKILL.md:281-290`) e não existe
   `PLAN-186-FOLLOWUP-*` (`ls .claude/plans/ | grep FOLLOWUP` = 4 arquivos, nenhum
   deste). O detector #6 do `reality-ledger.py` é AST sobre call-sites de
   `emit_generic`: vê ação EMITIDA e ausente do registro, nunca ação DECLARADA que
   ninguém emite — **cego a esta classe por construção**. Cura barata: criar o arquivo
   de followup e apontar a nota para ele.
6. **K6 (Critic-A) — P3 — linha em branco espúria em `templates/CLAUDE.md`.**
   Verificado no `git diff`: uma linha vazia adicionada entre o bullet «Owner Routing»
   e `- **3-Strike:**`. É a raiz que o adopter RECEBE. Já é o item 4 do CEO.
7. **K7 (Critic-C) — P3 — o custo recorrente da doutrina no hook não foi orçado.**
   Medido por mim: `_STEP0_DOCTRINE` = **827 caracteres** (~206 tokens), injetado nos
   dois caminhos, contra um teto de volume publicado de ≤50 disparadas/hora
   (`parallelization-by-default/SKILL.md:292-295`) ⇒ ~10k tokens/hora de doutrina
   repetida no assento. Não é caro; é NÃO-MEDIDO, numa wave cuja tese é que custo fixo
   não declarado é o defeito. Uma linha em ADR-198 §Consequences fecha.

## Single-agent insights rejected / deferred

1. **DEFERIDO como residual HERDADO (Critic-A, R-VP4) — `/effort` scope clause.**
   `PROTOCOL.md:441` enumera `low|default|high|max` sem `xhigh`. Verifiquei que o patch
   **não toca** o arquivo nesse ponto: `git diff PROTOCOL.md | grep -c effort` = **0**, e
   `xhigh` já era legal antes do patch (`.claude/commands/effort.md` no HEAD). O drift é
   herdado, não criado pela W5 — mas a W5 aumenta a consequência ao fazer `xhigh` o teto
   de R1 E o default declarado de uma linha irresolúvel (`effort.md:118-119`). Fica
   NOMEADO como residual herdado (não defeito da W5) para a próxima sessão não confundir.
2. **REGISTRADO, não é must-fix (Critic-B, R-DEV2) — margem de 147 bytes no `CLAUDE.md`.**
   Verificado: `HEAD:CLAUDE.md` = 39.859 bytes, aplicado = **39.853** — o patch LIBERA
   6 bytes, não consome. O cap de 40.000 só é conferido pelo governance COMPLETO, nunca
   pelo `--fast` (já em `CLAUDE.md` §5). É restrição do closeout da S345, não da W5.
3. **ACEITO como resultado NEGATIVO a registrar (Critic-B, R-DEV3).** Verifiquei:
   `grep 'CEO_OVERHEAD_ACK=1 to ack'` fora de `.claude/plans/` dá **2** hits, ambos
   dentro do próprio hook — nenhum consumidor externo pina o texto da mensagem, e o
   `reason_len` do `SPEC/v1` pertence a OUTRO emissor. Vai para `EVIDENCE.md` como
   negativo, para o próximo revisor não re-derivar.
4. **ACEITO barato (Critic-C, R-W5-4) — ordem de leitura.** O frontmatter
   machine-readable e o «CEO MUST emit» precedem em ~67 linhas a nota que diz que o
   evento não pode ser emitido hoje. Dois ponteiros de uma linha; sem risco.
5. **NÃO ALTERADO — os pares espelho e as superfícies geradas.** Ambos os críticos que
   os examinaram os acharam byte-idênticos e em sincronia (ADR index 201 = disco em 8
   superfícies, incluindo as 4 que o `verify-counts` não vigia). Não gasto round nisso.

## Plan adjustments (must-fix para o builder da W5)

Nenhum toca o arquivo do plano — o modelo passou. Todos são no pack.

| # | mudança | prioridade |
|---|---|---|
| 1 | `CHANGELOG.md`: reescrever o parágrafo do rótulo com parênteses balanceados e frase com sujeito; **e** corrigir `DESIGN-w5-doctrine-S344.md` §9 item 9, que declara CURADO o que os bytes contradizem (re-derivar §9 dos bytes aplicados) | **BLOCKING** |
| 2 | `debate/proposal.md:74`: `no_spawn_judgment_carve_out` → `spawn_judgment_carve_out` (errata, antes de arquivar o round) | **BLOCKING** |
| 3 | `check-classifier-cases.py`: ler `.claude/commands/effort.md` como QUARTA fonte cell-identical **ou** effort.md perder a auto-suficiência declarada (`:75`) e rotular-se «não conferido por oráculo». Pela derivador; depois re-rodar os 3 geradores + `verify-counts` (effort.md é comando ⇒ move `docs/COMMAND-SKILL-HOOK-MAP.md`) | **BLOCKING** |
| 4 | Cláusula de CARDINALIDADE nos 4 sítios canônicos: a isenção cobre o revisor EXIGIDO; um segundo revisor do MESMO produto volta ao Check 2 | **BLOCKING** |
| 5 | Cláusula de POPULAÇÃO nos sítios que citam os ~95k: medido em `general-purpose` sem skill inline ⇒ PISO para spawn nomeado; viés SUBESTIMA | **BLOCKING** |
| 6 | `check_anti_ceo_overhead.py` `_STEP0_DOCTRINE`: carve-out por PRODUTO + cláusula da routing table + distinção medição/inferência (paridade com os outros 6 sítios) | P2 |
| 7 | Criar `PLAN-186-FOLLOWUP-parallelization-action-register.md` e apontar a nota da skill (`:281-290`) para ele | P2 |
| 8 | `templates/CLAUDE.md`: remover a linha em branco espúria antes de `- **3-Strike:**` | P3 |
| 9 | ADR-198 §Consequences: uma linha com o custo recorrente (827 chars ≈ 206 tokens/disparada, teto ≤50/hr) | P3 |
| 10 | `EVIDENCE.md`: registrar o negativo do R-DEV3 e o residual HERDADO de `PROTOCOL.md:441` (não é defeito da W5) | P3 |
| 11 | Ponteiros de ordem de leitura em `parallelization-by-default/SKILL.md:56` e `:214` | P3 |
| 12 | Construir os materiais de cerimônia (item R4 do CEO): UM commit, `EXPECTED_*` **gerado** pelos geradores — o bump 198→201 toca nove sítios em três geradores | P2 |

## Round verdict

**RUN-ANOTHER-ROUND** — *não* `design-coherent`.

Regra aplicada: risco levantado por 2+ críticos ⇒ o texto MUDA (C1-C3, todos
aplicados); risco de um só crítico ⇒ decisão escrita do sintetizador com verificação
em disco (7 mantidos, 5 rejeitados/deferidos/registrados).

**Por que não PROCEED:** o round termina com **5 itens BLOCKING** vivos, e o rótulo
`design-coherent` só é registrado quando o round ITSELF fecha com zero. Dois deles não
são cosmética: a tabela §2b sem oráculo na cópia ENTREGUE (#3) reabre a classe de drift
silencioso que este repo já pagou, e o carve-out sem cardinalidade (#4) permite tornar
o Check 2 decorativo por multiplicação sem violar uma linha do texto. O #1 é pior por
categoria: o pack embarca uma afirmação FALSA sobre a própria árvore, e o gate é
estruturalmente cego ao defeito — a bateria não pode pegá-lo por nós.

**Por que não ESCALATE-TO-OWNER:** todos os 12 itens são edições de texto ou uma
constante num oráculo que já roda fail-closed; nenhum muda o MODELO (ratificado no
round 3), nenhum precisa de decisão do Owner, e o Owner está AUSENTE (night-run S345).
A wave é livre até a assinatura.

**Critério de parada para o round 5:** revisar o pack REVISADO — inclusive os
materiais de cerimônia, que ainda não existem e portanto não foram revisados por
ninguém. Rodada limpa prova a SUPERFÍCIE revisada, não o entregável; e o derivador
nunca aparece no diff da sombra — a lane do `apply-w5-doctrine.py` é obrigatória.
