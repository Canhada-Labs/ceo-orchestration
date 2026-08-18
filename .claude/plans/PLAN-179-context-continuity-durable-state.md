---
id: PLAN-179
title: Continuidade de contexto — estado durável escrito em fronteira de trabalho, não na morte da sessão
status: draft
created: 2026-08-16
owner: CEO
depends_on: []
budget_tokens: 180-340k (W0 30-60k; W1 40-70k; W2 60-110k; W3 30-60k; W4 20-40k)
budget_sessions: 3-4
context_risk: high
external_wait: "BLOQUEADO até GA v1.3.0. Freeze rota-SEQUÊNCIA (S304): nada landa entre a tag rc.4 e o GA. Autorado 2026-08-16 com a evidência fresca; execução só após GA + hold 24h."
tags: [context-management, durable-state, memory, compaction, governance, substrate]
---

# PLAN-179 — Continuidade de contexto: estado durável escrito em fronteira de trabalho

> **SEMENTE (S309, 2026-08-16).** Investigação disparada por um
> autocompact real na madrugada de 16/08 que consumiu a sessão
> `1916b9c8` (transcript 14,4 MB). Referências externas (substrato +
> academia): `PLAN-179/research-S309.md` — fonte ÚNICA; este plano
> aponta, nunca duplica números.
>
> **Achado central:** o repo não tem um problema de *memória*. Tem um
> problema de **momento da escrita**. Todo estado durável é escrito em
> eventos terminais (`Stop`, closeout, `PreCompact`) — exatamente os
> eventos que uma sessão morrendo por contexto não alcança, ou alcança
> degradada.

---

## 1. Evidência (medida, não inferida)

### E1 — O ADR-153 disparou vazio no evento para o qual foi construído

O autocompact de 2026-08-16T09:34Z emitiu os dois eventos previstos.
Ambos registram falha, verbatim do `audit-log.jsonl`:

```
action=compaction_continuity_snapshot  trigger=auto  plan_id=unknown
    chain_length=11179  snapshot_outcome=scratchpad_unavailable
action=compaction_context_reinjected   plan_id=unknown
    snapshot_found=false  snapshot_age_s=0  pointer_count=1
```

O snapshot **nunca foi escrito**. O PostCompact reinjetou 1 ponteiro —
o lembrete genérico de Gate-1 — e zero estado de governança.

O ADR-153 declarava o *fires-proof* como `PENDING-LIVE` (residual risk
§1) porque forçar autocompact é pago. **Esse fires-proof agora existe e
é negativo:** os eventos disparam, o mecanismo não entrega. O ADR provou
a MECÂNICA e nunca provou o VALOR — a classe dominante do repo
([[feedback-instrument-green-with-stale-question]]).

### E2 — A causa-raiz é estrutural, não uma borda

`scratchpad_lib.resolve_plan_id()` (`.claude/hooks/_lib/scratchpad_lib.py:103`)
exige um evento `plan_transition` **com `session_id` casando o da sessão
corrente**. Um `plan_transition` só é emitido quando um plano muda de
status. Uma sessão que trabalha num plano já `executing` nunca emite um.

Censo no log: **2 eventos `plan_transition` em 12.515 linhas**, ambos de
2026-08-13, de outra sessão — descartados pelo filtro de `session_id`.

Portanto a continuidade só funciona em sessões que por acaso viram o
status de um plano — que são as **curtas**. O mecanismo está
**anti-correlacionado com o próprio caso de uso**. O ADR-153 lista isso
como "residual risk #3, fail-open by design"; a medição mostra que não é
o caminho raro, é o **caminho padrão**.

### E3 — Nada escreve memória; a memória velha é o sintoma

`.claude/hooks/SessionEnd.py` apenas **verifica** que o diretório de
memória é gravável (`_memory_dir_state`). Não escreve nada. A
persistência é inteiramente discricionária do modelo, num closeout que
uma sessão morta por contexto nunca alcança.

Prova observável: no momento desta investigação o `MEMORY.md` afirmava
"S308: Lote B autorado, pausado pré-r15", enquanto o disco tinha 3
commits adiante, um re-pass t9 NO-GO e as curas já autoradas. A memória
não drifta por bug — **drifta porque ninguém a escreve**.

### E4 — Política de contexto construída e nunca ligada

`.claude/scripts/context-budget.py` expõe `--compact-decision` (D1),
`--summarize-decision` (D2), `--middle-out-decision` (D5). Grep no repo:
aparecem **só no próprio script e em `tests/test_context_budget.py`**.
Nenhum hook, comando, runbook ou CI consome. Sondas órfãs.

### E5 — Suspeita NÃO confirmada (vira item de W0)

`check_postcompact_reinject.py:236-238` emite
`hookSpecificOutput.additionalContext` no evento **PostCompact**. A doc
de hooks não lista `additionalContext` entre os canais suportados desse
evento (lista `systemMessage`/`terminalSequence`), e afirma
explicitamente que em `SessionStart` ele NÃO é suportado.

**Mas** o `turbo_sessionstart.py` deste repo usa `additionalContext` em
SessionStart e **funciona** (a linha `⚡ turbo:` chega ao modelo). Logo a
doc está imprecisa OU os eventos diferem. **Não sabemos.** Doutrina 3:
resolve-se com sonda viva, não com leitura de doc. É o item W0-1.

> Padrão a nomear: o ADR-153 sondou se os **eventos disparam**. Nunca
> sondou se o **canal de saída é consumido**. Sonda de evento ≠ sonda de
> canal.

---

## 2. Problema

**Escrita em evento terminal.** As três superfícies duráveis do
framework (scratchpad de continuidade, memória nativa, índice
`MEMORY.md`) são escritas em `PreCompact` / `Stop` / closeout manual.
Uma sessão longa o bastante para compactar é precisamente a que:

1. não chega ao closeout (o Owner interrompe, ou o contexto acaba);
2. chega ao `PreCompact` com o resolvedor de plano já inutilizável;
3. depende do modelo pós-compactação lembrar de reconstruir estado que
   ninguém persistiu.

**Consequência medida:** trabalho real (curas t7/t8/t9 do PLAN-177) foi
executado em três sessões cuja memória nunca foi atualizada, obrigando a
próxima sessão a redescobrir o estado por arqueologia de git + leitura
de evidência quarentenada.

### 2.1 O segundo problema: compactar cedo demais é thrashing

Levantado pelo Owner na S309. Compactação **não é grátis**: ela reseta o
contexto para um **piso fixo** que o framework re-paga inteiro.

Seja `F` o piso re-pago (Gate 1+2 + índice de memória + system prompt +
definições de ferramenta), `S` o tamanho do sumário e `T` o limiar de
compactação. O trabalho produtivo por ciclo é `T − F − S`, e a eficiência
do ciclo é:

```
η = (T − F − S) / T
```

Medição local (`research-S309.md §3`): Gate 1+2 = **40.116** tokens
estimados, `MEMORY.md` = **4.413**. Com system prompt + ferramentas, `F`
cai na faixa **45–55k**. Fixando `F=50k` e `S=10k`:

| `T` (limiar)            |   η  | Leitura |
|-------------------------|-----:|---------|
| 184k (≈92% de 200k)     |  67% | saudável |
| 150k (default da API)   |  60% | saudável |
| 120k (topo da faixa CWL)|  42% | medíocre |
| 100k                    |  40% | medíocre |
| 80k (piso da faixa CWL) |  25% | **thrashing** |
| 60k                     |   0% | **loop: nunca progride** |
| 50k (mínimo da API)     |  <0  | **impossível** |

Três conclusões que mudam o desenho:

1. **O piso de thrashing deste framework é `T ≈ 60k`.** O mínimo permitido
   pela API (`trigger.value = 50000`) está **abaixo** dele. Este repo
   estruturalmente não pode usar compactação agressiva.
2. **A faixa ótima medida na literatura (80k–120k, `research-S309.md
   §2.4`) rende aqui apenas η de 25–42%** — não porque a faixa esteja
   errada, mas porque `F` é pesado demais para ela.
3. **A alavanca é `F`, não `T`.** Com `F=20k` (progressive disclosure do
   core skill + `team.md`, economia estimada ~30k), a mesma faixa 80–120k
   passa a render **62–75%**. Mexer no limiar sem baixar o piso apenas
   escolhe onde na curva ruim ficar.

Corolário de custo já conhecido pelo repo: a chamada de sumarização
**reseta o prefixo de KV cache** (`research-S309.md §2.4` — 23% de
diferença de custo). O `CLAUDE.md §0` já trata estabilidade de cache como
doutrina; compactação é a violação mais cara dela, e é involuntária.

E o risco que fecha o argumento: a literatura mede que compactação
agressiva **quadruplica os turnos** (4,0 → 14,0) para economizar 14% de
tokens, porque o agente relê o que foi descartado. Thrashing não é
hipótese — é o resultado medido de comprimir cedo demais.

### 2.2 O terceiro problema: a compactação apaga a governança

`research-S309.md §2.2` (arXiv 2606.22528) mede exatamente o risco que
este framework existe para evitar:

- restrições de governança **visíveis**: 0% de violação;
- as mesmas restrições **após compactação**: **30% em média, até 59%**;
- quando a restrição **sobrevive** ao sumário: 0%. Quando é **omitida**: 38%.

E existe um vetor adversarial nomeado — **Compaction-Eviction Attack** —
em que conteúdo hostil já presente no contexto enviesa o sumarizador a
excluir políticas legítimas. **Derrotou todos os modelos avaliados.**

Isto reenquadra o ADR-153. A doutrina pointers-only está correta quanto a
**não injetar corpo de arquivo**, mas um ponteiro **não é** uma restrição
preservada: o `pointer_count=1` observado em E1 é um lembrete para reler
o Gate-1, não a regra em si. A mitigação medida é **Constraint Pinning** —
quarentenar as regras de governança da compressão com perda, o que
restaurou a violação a 0%.

Para este repo, a leitura é direta: **as regras de governança precisam ser
o último item elegível a sair do contexto, não o primeiro.**

---

## 3. Não-objetivos (escopo fechado)

- **NÃO** substituir a compactação do harness por implementação própria.
- **NÃO** adotar store vetorial, RAG ou embedding. O repo é stdlib-only
  (`SBOM.md`); a recuperação aqui é por ponteiro e path, não por
  similaridade.
- **NÃO** reabrir a doutrina pointers-only do ADR-153 §Decision-2.
  Injetar corpo de arquivo em `additionalContext` continua proibido.
- **NÃO** adotar Agent Teams nem alterar a topologia flat de spawn
  (`team.md` §Spawn-depth doctrine).
- **NÃO** tocar superfície canônica sem cerimônia própria.

---

## 4. Ondas

> Gate global: nenhuma wave executa antes do GA v1.3.0 + hold 24h.
> W1+ exige `/debate start PLAN-179` (L3+: toca rail de hooks,
> superfície de audit e canal de injeção).

### W0 — Sonda e medição (pré-requisito de tudo)

Barata, read-only, responde as perguntas que dimensionam W1–W4. Nenhuma
wave posterior desenha em cima de premissa não medida
([[feedback-branch-local-patching-induces-regressions]]).

- [ ] `[P1][US1][.claude/scripts/probes/probe_postcompact_channel.py]`
      Sonda viva do canal: `/compact` manual com um canário único
      injetado via `additionalContext` em PostCompact; assertar se o
      token aparece no contexto pós-compactação. Resultado positivo OU
      negativo é entregável — negativo redireciona W1 para o canal
      `SessionStart(matcher=compact)` com stdout puro.
- [ ] `[P1][US1][.claude/scripts/probes/probe_postcompact_channel.py]`
      Controle positivo obrigatório: a sonda deve FALHAR quando o canário
      não é emitido. Sonda que não falha é sonda morta
      ([[feedback-probe-needs-neutral-user-layer]]).
- [ ] `[P2][US2][.claude/hooks/_lib/audit_emit.py]`
      Ação nova `context_pressure_observed` (enum fechado + inteiros:
      `used_bucket`, `event_source`, `plan_id`). Sem texto, sem path.
      Mede frequência real de compactação e a pressão em que ocorre.
- [ ] `[P1][US2][PLAN-179/w0-measurement.md]`
      **Fixar `F` e `T` empiricamente** — a tabela de η em §2.1 usa
      `F=50k` estimado por heurística chars/4. Medir o piso REAL
      (system prompt + defs de ferramenta + Gate 1+2 + índice de memória)
      e o limiar REAL de auto-compact do harness. Sem esses dois números
      a curva η é ilustrativa, não decisória
      ([[feedback-measurement-must-list-its-inputs]]).
- [ ] `[P2][US2][PLAN-179/w0-measurement.md]`
      Relatório: N de compactações/semana, distribuição de `plan_id`
      resolvido vs `unknown`, custo de gate-boot re-pago por compactação
      (baseline documentado: ~44.786 tokens).
- [ ] `[P1][US2b][.claude/hooks/check_precompact_continuity.py]`
      **Progress guard** (`research-S309.md §2.3`): se uma compactação
      não liberar headroom suficiente — `η` abaixo de um piso nomeado —
      HALTAR a tentativa automática e notificar o operador em vez de
      compactar de novo. É a válvula contra o loop que o Owner apontou.
      Requer o `F` medido acima; até lá o piso não tem valor honesto.

**AC de saída W0:** (a) o veredito do canal está escrito e é falsificável;
(b) a taxa de `plan_id=unknown` está medida, não estimada; (c) `F` e `T`
têm valores medidos e a tabela η de §2.1 é reescrita com eles ou
explicitamente confirmada.

### W1 — Curar o snapshot vazio (o bug real)

- [ ] `[P1][US3][.claude/hooks/_lib/scratchpad_lib.py]`
      Escopo de fallback por **sessão** quando `resolve_plan_id` levanta
      `PlanIdDerivationError`. A escrita de continuidade NUNCA é pulada:
      sem plano resolvido, escreve sob escopo de sessão. Mantida a
      proibição M2 de derivar plano de env var (agent-spoofable).
- [ ] `[P1][US3][.claude/hooks/check_precompact_continuity.py]`
      `snapshot_outcome` ganha o valor `written_session_scope`. O enum
      permanece fechado; `scratchpad_unavailable` passa a significar
      falha real de I/O, não ausência de plano.
- [ ] `[P1][US3][.claude/hooks/check_postcompact_reinject.py]`
      Leitura do escopo de sessão quando não há escopo de plano.
- [ ] `[P1][US4][.claude/adr/ADR-153-compaction-continuity.md]`
      Emenda ADR-153-AMEND-1 registrando: (a) o fires-proof PENDING-LIVE
      foi satisfeito e o resultado foi NEGATIVO; (b) o residual #3 era o
      caminho dominante; (c) a cura por escopo de sessão. **Path
      canônico — exige cerimônia GPG.**
- [ ] `[P1][US5][.claude/hooks/tests/test_precompact_continuity.py]`
      Controle positivo replicando E1: sessão sem `plan_transition` ⇒
      snapshot ESCRITO. O teste deve falhar contra o código de hoje.

#### W1-b — Constraint Pinning (§2.2 — prioridade igual à cura do snapshot)

Ponteiro não é restrição. A mitigação medida contra Governance Decay é
quarentenar as regras da compressão com perda.

- [ ] `[P1][US5b][.claude/hooks/check_postcompact_reinject.py]`
      Separar **PONTEIRO** (onde olhar — estado de trabalho) de
      **RESTRIÇÃO FIXADA** (a regra em si — o conjunto mínimo de invariantes
      de governança). Ponteiros seguem bounded/sanitizados; restrições
      fixadas são um conjunto FECHADO e versionado, definido no repo, não
      derivado de disco em tempo de execução — o que as torna imunes ao
      Compaction-Eviction Attack por construção.
- [ ] `[P1][US5c][.claude/plans/PLAN-179/pinned-constraints.md]`
      Definir o conjunto mínimo fixado. Candidatos: vetos ADR-052; disciplina
      de sentinel canônico ADR-031; "não commitar sem autorização do Owner";
      fail-closed em input / fail-open em infra. **Fechado e pequeno** — um
      conjunto grande re-cria o problema de piso (§2.1).
- [ ] `[P1][US5d][.claude/hooks/tests/test_postcompact_reinject.py]`
      Controle adversarial: transcript contendo texto que instrui o
      sumarizador a omitir políticas ⇒ as restrições fixadas ainda aparecem
      pós-compactação. Sem esse controle, o pinning é alegação.

**AC de saída W1:** (a) um autocompact numa sessão sem `plan_transition`
produz `snapshot_found=true` e `pointer_count>1`; (b) o conjunto fixado
sobrevive a uma compactação adversarial no controle de US5d.

### W2 — Ledger de trabalho contínuo (a mudança de doutrina)

Move a escrita de evento terminal para **fronteira de unidade de
execução**. Forma adotada do padrão multissessão da Anthropic
(`research-S309.md §2`), montada sobre o que o repo já tem: ACs de plano
+ git + audit log.

- [ ] `[P1][US6][.claude/plans/PLAN-NNN/LEDGER.md]`
      Contrato do ledger por plano: unidade corrente, ACs com estado
      verificado, último commit, decisões tomadas, bloqueios abertos.
      Uma seção por unidade; identificadores verbatim (paths absolutos,
      SHAs, PLAN-/ADR-ids) — nunca paráfrase.
- [ ] `[P1][US6][.claude/hooks/check_ledger_checkpoint.py]`
      Hook novo: em fronteira de unidade (commit tocando um path do plano
      ativo), verifica que o ledger foi atualizado no mesmo commit.
      **ADVISORY primeiro** — janela measure-first, como o
      `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED` (ADR-191). Enforce é cerimônia
      futura com tabela would-block/TP-FP.
- [ ] `[P1][US7][.claude/hooks/check_precompact_continuity.py]`
      PreCompact passa a apontar para o ledger; o snapshot vira o
      **índice** do ledger, não a cópia do estado.
- [ ] `[P2][US8][.claude/hooks/SessionEnd.py]`
      SessionEnd deixa de só verificar: emite o delta candidato de
      memória (contagem + paths, nunca corpo) para o operador ratificar.
      Escrita de memória continua sendo decisão do modelo/Owner — o hook
      torna a OMISSÃO visível, não escreve por conta própria.
- [ ] `[P1][US9][.claude/adr/ADR-193-work-boundary-persistence.md]`
      ADR novo: "escrita em fronteira de trabalho". Registra a doutrina,
      o porquê (E1–E3) e a fronteira honesta. **Canônico — cerimônia.**

**AC de saída W2:** matar uma sessão no meio de uma unidade e abrir uma
nova recupera o estado a partir do ledger, sem arqueologia de git.
Ensaio obrigatório em clone, não no repo vivo
([[project-s301-rc3-nogo-cures-overnight]]).

### W3 — Baixar o piso, melhorar a compactação, fechar as sondas órfãs

> §2.1 estabelece que **a alavanca é `F`, não `T`**. Esta wave é onde o
> piso desce.

- [ ] `[P1][US9b][PLAN-179/floor-reduction.md]`
      Plano de redução de `F` a partir do ranking já produzido por
      `context-budget.py`: `ceo-orchestration/SKILL.md` (735L, ~15.768 tok,
      economia ~15.618 por ativação via `references/*.md` + ponteiro loader)
      e `team.md` (832L, ~11.917 tok). Alvo: `F` de ~50k para ~20k.
      **Dono do trabalho de poda é o PLAN-175** (skills-pruning-discovery) —
      este item DEFINE o alvo e o critério de aceite, não re-executa a poda.
      Reestruturar o core skill exige cerimônia/debate próprios.
- [ ] `[P2][US9c][PLAN-179/floor-reduction.md]`
      Avaliar **eviction estruturada** (`research-S309.md §2.4`) como
      alternativa à sumarização: DAG de episódios exploratory/action,
      remoção primeiro do que persiste no ambiente. Registrar como
      ADOTAR / NÃO-ADOTAR com razão — o substrato hoje não expõe esse
      controle, então provavelmente é doutrina de uso, não implementação.
      Ganho colateral relevante: prefixo de cache estável (23% de custo).

- [ ] `[P2][US10][templates/compaction.md]`
      Ligar o template de 9 seções (PLAN-133 D4) como instrução real de
      compactação, em vez de template que ninguém alimenta. Avaliar as
      duas rotas: `/compact <instruções>` no CLI e o parâmetro
      `instructions` do `compact_20260112` na API (`research-S309.md §1`)
      — atenção: `instructions` **substitui integralmente** o prompt
      padrão, então omissão é perda de recall.
- [ ] `[P2][US11][.claude/scripts/context-budget.py]`
      Decidir o destino de D1/D2/D5: consumir ou remover. Sonda órfã que
      permanece é dívida que parece cobertura. Se consumir, o consumidor
      é nomeado aqui; se remover, sai com o teste.
- [ ] `[P3][US12][docs/CONTEXT-CONTINUITY-GUIDE.md]`
      Guia do adopter: o que sobrevive a uma compactação, o que não, e
      qual é o piso de working-set. Sem promessa que o código não cumpre
      ([[feedback-verify-counts-real-path-is-local]]).

### W4 — Governança da superfície de estado durável

Fecha os primitivos ausentes apontados pelo survey de segurança de
memória (`research-S309.md §3`): *write-gate validation* e
*post-deletion verification* não existem em nenhuma arquitetura revisada.

- [ ] `[P1][US13][.claude/hooks/_lib/ledger_provenance.py]`
      Tag de proveniência por entrada do ledger: `owner-instruction` |
      `ceo-derived` | `agent-returned` | `external-tool`. Entrada de
      origem externa nunca é relida como instrução.
- [ ] `[P2][US14][.claude/hooks/check_ledger_checkpoint.py]`
      Write-gate: entrada de ledger passa pelo scanner de
      harness-mimicry antes de persistir (mesma rota do Step-4 do
      `/ceo-boot`). Hit ⇒ entrada DESCARTADA, nunca redigida.
- [ ] `[P2][US15][PLAN-179/threat-model.md]`
      Modelo de ameaça do ledger nos seis eixos do survey Always-On
      (autoridade, escopo, mutabilidade, proveniência, recuperabilidade,
      acionabilidade). Registrar em `THREAT-MODEL-WORKSHEET.md §2`.
- [ ] `[P1][US15b][THREAT-MODEL-WORKSHEET.md]`
      Registrar duas classes NOVAS de `research-S309.md §2.2` e §2.5:
      (a) **Compaction-Eviction Attack** — conteúdo hostil no transcript
      enviesa o sumarizador a descartar políticas; derrotou todos os
      modelos avaliados; contramedida é o pinning de W1-b, não um scanner;
      (b) **experience grafting / erosão progressiva** — lições falsas
      destiladas de interações, sem evento único detectável. A segunda
      atinge o rail de lições JÁ EXISTENTE (`CEO_LEARNING_BOOT_LESSONS`),
      que hoje renderiza lições aprovadas no boot: avaliar se o gate A6
      (`sha256(trigger + advisory_text)` verificado contra a cadeia HMAC)
      cobre erosão progressiva ou só adulteração pontual.
- [ ] `[P2][US15c][.claude/hooks/_lib/ledger_provenance.py]`
      *Post-deletion verification* (primitivo ausente em toda arquitetura
      revisada, `research-S309.md §2.5`): remoção de entrada do ledger é
      verificada, não presumida — e a sumarização do ledger é auditada
      separadamente do armazenamento bruto, porque compressão AMPLIFICA
      veneno.

---

## 5. Fronteiras honestas

- **W0-1 pode invalidar o desenho de W1.** Se o canal `additionalContext`
  do PostCompact for inerte, a reinjeção migra para
  `SessionStart(matcher=compact)` com stdout puro. Por isso W0 é gate, não
  formalidade.
- **O ledger é mais uma superfície a manter.** Se ninguém escrever, ele
  degrada exatamente como a memória degradou (E3). Mitigação é o hook
  advisory de W2 tornando a omissão VISÍVEL — não é garantia.
- **Advisory não é enforcement.** W2 nasce advisory por escolha. O flip
  para enforce é cerimônia futura com evidência, não item desta wave.
- **Este plano não elimina compactação.** Reduz o custo dela. O piso de
  gate-boot (~44.786 tokens) é re-pago em toda compactação e só cai
  atacando a superfície Gate-1 — execução no PLAN-175; aqui só o alvo.
- **O ganho de η depende de um plano que não é este.** §2.1 mostra que a
  alavanca é `F`, e `F` desce no PLAN-175. Se a poda não acontecer, W0–W4
  entregam continuidade e governança preservada, mas a eficiência de
  ciclo continua na faixa 40–60%. Dependência declarada, não escondida.
- **A tabela η de §2.1 é estimativa até W0.** Usa a heurística chars/4 do
  `context-budget.py`, explicitamente não o tokenizer da Anthropic, e um
  `F=50k` interpolado. A forma da curva e o piso de thrashing (`T ≈ F+S`)
  são robustos; os valores absolutos não são, até US2 medi-los.
- **Constraint Pinning é mitigação medida em outro setup.** Os números de
  §2.2 (0% → 30%/59%) vêm do paper, não deste framework. W1-b importa o
  MECANISMO; o controle adversarial de US5d é o que gera evidência local.
- **`context_risk: high` é autoconsciente.** Um plano sobre continuidade
  de contexto executado numa sessão que compacta é o seu próprio teste.
  W2 deve ser executada com o ledger já ativo, dogfood explícito.

## 6. Kill switches

- `CEO_COMPACTION_CONTINUITY=0` — desliga o par ADR-153 (existente).
- `CEO_LEDGER_CHECKPOINT=0` — desliga o hook de fronteira (W2).
- `CEO_SOTA_DISABLE=1` — precedência mestre, força tudo advisory.

## 7. Governança

- **Nível:** L3+ (rail de hooks + superfície de audit + canal de
  injeção + 2 paths canônicos).
- **Debate:** `/debate start PLAN-179 "<proposta>"` obrigatório antes de
  W1. W0 é read-only e dispensa.
- **Pair-rail:** obrigatório em W1, W2 e W4 (hooks + canônico).
- **Cerimônia GPG:** ADR-153-AMEND-1 (W1) e ADR-193 (W2).
- **Contagens derivadas:** hooks novos movem os gates de contagem do
  `CLAUDE.md` — regenerar superfícies e rodar
  `.claude/scripts/local/verify-counts.sh` no closeout, tolerance=0.
