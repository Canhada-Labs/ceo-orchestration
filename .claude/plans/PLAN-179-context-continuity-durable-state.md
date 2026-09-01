---
id: PLAN-179
title: Continuidade de contexto — estado durável escrito em fronteira de trabalho, não na morte da sessão
status: done
executing_since: 2026-08-20
completed_at: 2026-08-31
related_commits: [c042f9e, 6f7f20e, 45c75e3, 08e25f4, b07be9b, 826688f]
reviewed_at: 2026-08-18
reviewed_by: "Owner — flip draft→reviewed autorizado na S313 (2026-08-18) após debate L3 round-1 (S312, consensus PROCEED, 3× ADJUST/0 VETO; 9 emendas C1-C9 aplicadas ao §8). GA v1.3.0 saiu 2026-08-17 — o bloqueio do external_wait caiu. Execução W0→W4 em sessão(ões) próprias."
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
estimados, `MEMORY.md` = **4.413**.

> **⚠️ A FAIXA 45–55k ESTÁ REFUTADA (S322, reconciliado na S325).** Ela era
> uma INTERPOLAÇÃO a partir da estimativa chars/4 do documento — omitia
> system prompt, definições de ferramentas e `cache_creation`. O `F` real
> foi MEDIDO na fronteira de uma compactação: **97.292** tokens
> (`TOTAL_IN` 112.638 − `postTokens` 15.346 = `cache_read` 68.980 +
> `cache_creation` 28.310), com controle cold-`F` independente em
> **97.097** (delta 0,20%). E `F` **não é constante**: série cold-`F` de
> n=41 (censura declarada) dá min 84.101 / mediana **98.636** / max
> 138.552, pstdev 16.148 — spread de 51,7% da média, logo reportar só a
> média engana. Instrumento: `PLAN-179/w0/gateboot_repay.py`.

Fixando `F=97k` (mediana medida ≈ 98,6k) e `S=10k`:

| `T` (limiar)            |   η  | Leitura |
|-------------------------|-----:|---------|
| 184k (≈92% de 200k)     |  42% | medíocre |
| 150k (default da API)   |  29% | **thrashing** |
| 120k (topo da faixa CWL)|  11% | **thrashing** |
| 100k                    |  <0  | **impossível** |
| 80k (piso da faixa CWL) |  <0  | **impossível** |
| 60k                     |  <0  | **impossível** |
| 50k (mínimo da API)     |  <0  | **impossível** |

Com o `F` medido, o piso de thrashing **não** é `T ≈ 60k`: é `T ≈ 107k`
(`F+S`), acima de metade da tabela e muito acima do mínimo que a API
permite (`trigger.value = 50000`). É por isso que a continuidade só
funciona em sessões curtas — anti-correlacionada com o próprio caso de uso.

Três conclusões que mudam o desenho:

1. **O piso de thrashing deste framework é `T ≈ 107k`** (`F+S` com o `F`
   MEDIDO; a versão anterior desta linha dizia `T ≈ 60k`, derivado do
   `F = 50k` refutado). O mínimo permitido pela API
   (`trigger.value = 50000`) está **muito** abaixo dele. Este repo
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

- [x] `[P1][US1][.claude/scripts/probes/probe_postcompact_channel.py]`
      — *SUPERSEDIDO pela r1-C3 (ratificação do Owner, 2026-08-31,
      wave-179-close): o Constraint Pinning fez de
      `SessionStart(matcher=compact)` o canal PRIMÁRIO por construção
      (r1-C5: constante de CÓDIGO, nunca lida de disco), exatamente para
      que a governança pós-compactação NÃO dependa do veredito vivo deste
      canal. A sonda segue shipada e executável (operador/local, exige
      compaction paga); o veredito deixou de ser bloqueante.* Texto
      original: sonda viva do canal — `/compact` manual com canário único
      via `additionalContext` em PostCompact; positivo OU negativo era
      entregável.
- [x] `[P1][US1][.claude/scripts/probes/probe_postcompact_channel.py]`
      (landado `c042f9e` — `test_probe_postcompact_channel.py`, 326
      linhas, inclui o controle que falha sem canário)
      Controle positivo obrigatório: a sonda deve FALHAR quando o canário
      não é emitido. Sonda que não falha é sonda morta
      ([[feedback-probe-needs-neutral-user-layer]]).
- [x] `[P2][US2][.claude/hooks/_lib/audit_emit.py]`
      (landado `c042f9e` — `audit-registry.golden.txt:67`)
      Ação nova `context_pressure_observed` (enum fechado + inteiros:
      `used_bucket`, `event_source`, `plan_id`). Sem texto, sem path.
      Mede frequência real de compactação e a pressão em que ocorre.
- [x] `[P1][US2][PLAN-179/w0-measurement.md]` (landado `08e25f4`, 515L)
      **Fixar `F` e `T` empiricamente** — FEITO no AGREGADO, DEGRADADO na
      DECOMPOSIÇÃO; o `[x]` vale só para o agregado e diz isto à letra.
      Medidos (§C do relatório): `F` = **97.097 / 98.636** (n=2,
      2026-08-14 e 2026-08-18), `T` = **998.043** (n=1),
      `F+S` = **112.638** (n=1), `S ≈ 14.600` por SUBTRAÇÃO — não é
      medição —, η no ponto de operação real = **88,7 %**.
      O `F=50k` da tabela de §2.1 está REFUTADO por ≈2,0×; essa tabela
      NÃO foi reescrita in loco e fica superseded por §C/§E do relatório.
      **DEGRADAÇÃO nomeada aqui, não só lá:** a decomposição que este
      checkbox pede — system prompt vs defs de ferramenta vs Gate 1+2 vs
      índice de memória — permanece `estimativa declarada, fonte
      ausente` (§B): o harness não expõe as parcelas. O agregado não
      degrada e lista os seus INPUTS, como a lição exige
      ([[feedback-measurement-must-list-its-inputs]]).
- [x] `[P2][US2][PLAN-179/w0-measurement.md]` — **3 de 3 sub-itens**
      Relatório: N de compactações/semana, distribuição de `plan_id`
      resolvido vs `unknown`, custo de gate-boot re-pago por compactação.
      **FECHADOS** (`08e25f4`): distribuição de `plan_id` = `{'unknown':
      2}` — 100 % das compactações observadas, categórico e não
      estatístico (§D); N = **1** compactação, com a NÃO-DERIVABILIDADE
      da taxa/semana declarada POR ESCRITO no relatório (não há
      denominador de semanas-de-exposição fiável, §D).
      **O TERCEIRO FECHOU na S322, e a evidência que este item declarava
      está REFUTADA (reconciliado na S325).** O custo de gate-boot
      re-pago está MEDIDO (§F.2): **97.292** tokens na fronteira de uma
      compactação real (`TOTAL_IN` 112.638 − `postTokens` 15.346),
      decompostos em `cache_read` 68.980 + `cache_creation` 28.310, com
      controle cold-`F` independente em **97.097** (delta 0,20%). A
      medição de ausência que este `[ ]` citava é FALSA hoje: o grep pelo
      folclore de ordem 44k sobre o relatório dá **7**, não 0 (§F.2/§F.4
      e o AC extra do próprio relatório, que diz **MEDIDO**), e o
      "controle positivo = 2 (L257, L497)" também não reproduz — os
      números de linha citados já não são os sítios. O baseline antigo
      está refutado nos DOIS sentidos.
- [x] `[P1][US2b][.claude/hooks/check_precompact_continuity.py]`
      (landado `c042f9e` — `_progress_guard`, `PROGRESS_FLOOR_ENV` =
      `CEO_CONTEXT_PROGRESS_FLOOR_TOKENS`, wire em `gate()`, ação
      `context_pressure_observed` no SPEC v2.56, 4 testes verdes)
      **OBSERVADOR de pressão** (`research-S309.md §2.3`) — texto
      reescrito para o que REALMENTE shipou: ao cruzar um piso de tokens
      opt-in, EMITE `context_pressure_observed` (enum fechado) e NOTIFICA
      o operador por breadcrumb em stderr. Escopo dito à letra: o hook
      **não calcula η** (`grep -c 'η\|headroom\|112638'` no arquivo =
      **0**) e **não pode HALTAR** — PreCompact não tem canal de deny e
      `gate()` retorna `{}` por contrato (docstring: "no value of the
      return that could stop the compaction"). A redação original dizia
      "HALTAR"; marcar `[x]` com aquele texto embarcaria claim falsa numa
      superfície de governança — daí a reescrita, e daí o item separado
      abaixo para a válvula que ainda não existe.
- [x] `[P1][US2b-valve][.claude/hooks/check_precompact_continuity.py]`
      — *fechado na wave-179-close (ratificação do Owner 2026-08-31:
      «Eta advisory + doutrina»): `_eta_advisory()` calcula η=(T−F−S)/T
      em permille INTEIRO (887‰) das constantes MEDIDAS `F+S=112638` /
      `T=998043` (§C/§E do relatório) e avisa o operador a cada
      compactação; (i) «canal capaz de NEGAR» fica documentado como
      LIMITE DO SUBSTRATO (guia §6 — a mesma rota honesta do US9c), não
      como feature faltante.*
      **VÁLVULA — o delta que falta** (item novo, S316). O que separa o
      observador acima da válvula que o Owner pediu, nomeado:
      (i) **canal capaz de NEGAR** — PreCompact não tem; exige outra
      superfície (um gate que decide ANTES da fronteira) ou um
      kill-switch de operador. Nenhum valor de retorno de `gate()` para
      a compactação;
      (ii) **η calculado, não um limiar de tokens** — `η = (T − F − S)/T`
      com `F+S = 112.638` e `T = 998.043` MEDIDOS (§C/§E do relatório);
      hoje nenhum dos três entra no hook;
      (iii) a precondição "requer o `F` medido" está **SATISFEITA**
      (§C): o que falta é (i) e (ii), não mais medição.

**AC de saída W0 (reconciliado S316; fechado 2026-08-31):**
(a) o veredito do canal está escrito e é falsificável — **SUPERSEDIDO
pela r1-C3 (ratificação do Owner, 2026-08-31, wave-179-close)**: o canal
PRIMÁRIO de governança pós-compactação é `SessionStart(matcher=compact)`
com constante de CÓDIGO (r1-C5), por desenho independente do veredito de
`additionalContext`; a sonda (`c042f9e`) permanece disponível como
medição opcional, não bloqueante;
(b) a taxa de `plan_id=unknown` está medida, não estimada — **MEDIDA E
VAZIA**: `{'unknown': 2}`, N = 1, sem taxa derivável, e a
não-derivabilidade está declarada por escrito (§D do relatório);
(c) `F` e `T` têm valores medidos e a tabela η de §2.1 é reescrita com
eles ou explicitamente confirmada — **FEITO, com degradação nomeada**:
reescrita em `w0-measurement.md` §E (`F` = 97.097/98.636,
`T` = 998.043, `F+S` = 112.638, η = 88,7 %); a tabela de §2.1 DESTE
plano NÃO foi reescrita in loco e fica marcada como estimativa
REFUTADA (`F=50k`, ≈2,0× abaixo do medido), superseded por §C/§E; a
DECOMPOSIÇÃO de `F` segue `estimativa declarada, fonte ausente` (§B).
O AC de saída **FECHOU na cerimônia wave-179close** (conclusão
reescrita no rail r25 — um `done` com criterio aberto é claim falsa):
o item (a) foi SUPERSEDIDO pela emenda r1-C3 da própria cerimônia
(registro `s335-ceremony-179close/rail-round-1.md`), e o sub-item do
custo de gate-boot re-pago foi MEDIDO na S322 — `F` = 97.292 tokens na
fronteira de uma compactação real, com controle cold-F independente em
97.097 (delta 0,20%; instrumento `PLAN-179/w0/gateboot_repay.py`; série
cold-F n=41 em `w0-measurement.md` §E). As duas evidências viajam com o
`done` desta wave.

### W1 — Curar o snapshot vazio (o bug real)

- [x] `[P1][US3][.claude/hooks/_lib/scratchpad_lib.py]` (landado `c042f9e`)
      Escopo de fallback por **sessão** quando `resolve_plan_id` levanta
      `PlanIdDerivationError`. A escrita de continuidade NUNCA é pulada:
      sem plano resolvido, escreve sob escopo de sessão. Mantida a
      proibição M2 de derivar plano de env var (agent-spoofable).
      **[Emenda r1-C1]** O escopo de sessão usa `store_name` PRÓPRIO +
      `scope_kind` no blob (nunca sobrecarrega o campo `plan_id` — o
      invariante plan-isolation do store fica intacto); forma validada
      `session-<uuid>`; `session_id` vem SOMENTE do hook input — se o
      derivador cair no env (`CLAUDE_SESSION_ID`), o fallback é RECUSADO.
      **[Emenda r1-C2]** `set` com `ttl_seconds` explícito + item de GC de
      ARQUIVO (`.sqlite`/`.lock` órfãos) com teto, dimensionado pelo N de
      compactações/semana medido em W0.
- [x] `[P1][US3][.claude/hooks/check_precompact_continuity.py]` (landado `c042f9e`)
      `snapshot_outcome` ganha o valor `written_session_scope`. O enum
      permanece fechado; `scratchpad_unavailable` passa a significar
      falha real de I/O, não ausência de plano.
- [x] `[P1][US3][.claude/hooks/check_postcompact_reinject.py]` (landado `c042f9e`)
      Leitura do escopo de sessão quando não há escopo de plano.
- [x] `[P1][US4][.claude/adr/ADR-153-compaction-continuity.md]` (landado `c042f9e`, sentinel W179-approved.md.asc)
      Emenda ADR-153-AMEND-1 registrando: (a) o fires-proof PENDING-LIVE
      foi satisfeito e o resultado foi NEGATIVO; (b) o residual #3 era o
      caminho dominante; (c) a cura por escopo de sessão. **Path
      canônico — exige cerimônia GPG.**
- [x] `[P1][US5][.claude/hooks/tests/test_check_compaction_continuity.py]` (landado `c042f9e`, +565 linhas)
      Controle positivo replicando E1: sessão sem `plan_transition` ⇒
      snapshot ESCRITO. O teste deve falhar contra o código de hoje.
      **[Emenda r1-C7]** Path corrigido para o arquivo REAL da família; e
      `test_no_plan_transition_degrades_to_unavailable` (:273-281) — o teste
      que hoje AFIRMA o bug — é EDITADO nesta AC para assertar o novo
      comportamento (nunca apagado: é a prova regressiva de que o bug
      existiu).

#### W1-b — Constraint Pinning (§2.2 — prioridade igual à cura do snapshot)

Ponteiro não é restrição. A mitigação medida contra Governance Decay é
quarentenar as regras da compressão com perda.

- [x] `[P1][US5b][.claude/hooks/check_postcompact_reinject.py]` (landado `c042f9e` — inclui check_compact_pinning.py + wiring settings)
      Separar **PONTEIRO** (onde olhar — estado de trabalho) de
      **RESTRIÇÃO FIXADA** (a regra em si — o conjunto mínimo de invariantes
      de governança). Ponteiros seguem bounded/sanitizados.
      **[Emenda r1-C5]** As restrições fixadas são **CONSTANTE DE CÓDIGO em
      `.claude/hooks/_lib/`** (superfície já canonical-guarded) — NUNCA
      lidas de um `.md` em runtime; é isso que torna a frase "não derivado
      de disco" verdadeira e a imunidade ao Compaction-Eviction real por
      construção. Mudança do conjunto = cerimônia GPG.
      **[Emenda r1-C3]** Canal PRIMÁRIO do pinning =
      `SessionStart(matcher=compact)` (precedente positivo local:
      `turbo_sessionstart.py` + wiring `"matcher": ""`); o PostCompact é
      REFORÇO — W1-b deixa de ser refém do veredito de W0-1. Payload
      estruturado (nunca texto livre); orçamentos SEPARADOS para restrição
      e ponteiro, restrições emitidas PRIMEIRO (o cap de 9 nunca trunca
      governança); mudança de semântica do `pointer_count` ⇒ bump de SPEC.
- [x] `[P1][US5c][.claude/plans/PLAN-179/pinned-constraints.md]` (landado `c042f9e` — `_lib/pinned_constraints.py` + doc derivada)
      Documentação DERIVADA da constante de código (teste asserta
      `set(md) == set(código)`). Conjunto mínimo: vetos ADR-052; disciplina
      de sentinel canônico ADR-031; "não commitar sem autorização do Owner";
      fail-closed em input / fail-open em infra. **Fechado e pequeno** — um
      conjunto grande re-cria o problema de piso (§2.1). Critério de corte
      (OQ-2 respondida): só invariantes cuja violação é irreversível.
- [x] `[P1][US5d][.claude/hooks/tests/test_check_compaction_continuity.py]` (landado `c042f9e`)
      **[Emenda r1-C7]** Controle adversarial reescrito como propriedade
      ARQUITETURAL testável: as restrições fixadas chegam por canal que
      **NUNCA participa do bloco enviado ao sumarizador** (assert: o payload
      pinned não está no material compactável), independente de transcript
      hostil no resto do contexto — o sumarizador não é mockável, e "o
      modelo não se deixa enganar" não é claim testável. Estende o arquivo
      REAL da família (dual-loader `_pick()` + `_AuditEmitSlotGuard`), não
      cria arquivo novo sem decisão nomeada.

**AC de saída W1:** (a) um autocompact numa sessão sem `plan_transition`
produz `snapshot_found=true` e `pointer_count>1`; (b) o conjunto fixado
sobrevive a uma compactação adversarial no controle de US5d.

### Registro de execução — flip para executing e reconciliação de checkboxes (S316, 2026-08-20)

Flip `reviewed → executing` autorizado pelo Owner em chat (S316). Os
checkboxes de W1 (5) e W1-b (3) + dois de W0 (controle da sonda; ação
`context_pressure_observed`) foram marcados com evidência do pack
`c042f9e` + fix-forwards `6f7f20e`/`45c75e3` (CI 5/5 verde em
`45c75e3`). **Correção S316 — claim falsa MORTA.** A redação anterior desta nota
afirmava que `PLAN-179/w0-measurement.md` "não existe". É FALSO e era
falso quando foi escrito: o arquivo é RASTREADO (`git ls-files` = hit),
tem **515 linhas** (`wc -l`) e landou em `08e25f4` (2026-08-18
15:44:52 -0300) — **DOIS DIAS ANTES** de a nota entrar em `18de98e`
(2026-08-20 14:38:42 -0300). `F` e `T` estão MEDIDOS lá, não pendentes.

**Reconciliação r25 (um `done` não carrega "permanece aberto"):**
(i) o veredito VIVO do canal (US1 #1) foi SUPERSEDIDO pela emenda r1-C3
da cerimônia wave-179close — a sonda segue shipada e rodá-la é ação de
OPERADOR pós-land (uma compaction paga), fora do AC do plano;
(ii) o custo de gate-boot re-pago foi MEDIDO na S322 (97.292 na
fronteira real / cold-F 97.097, delta 0,20% — instrumento
`PLAN-179/w0/gateboot_repay.py`); (iii) a VÁLVULA do US2b entregou
NESTA wave como `_eta_advisory` (η=887‰ das constantes medidas;
«negar» documentado como limite de substrato — PreCompact não tem canal
de deny). Nada do W0 segue aberto. W2/W4
**LANDADAS em `b07be9b` (S329 U0, 2026-08-26, pack `staged-w24` — sentinel
`W179-W24-approved.md` assinado pelo Owner às 14:14; LAND V1–V6 verdes)**.

### Registro de execução — reconciliação pós-pack-D (S334, 2026-08-31)

Reconciliação das checkboxes de W2/W4 contra o land REAL de `b07be9b`
(verificado por recon read-only S334: `git show --stat b07be9b` + Scope
do sentinel `W179-W24-approved.md.asc`): US6 ×2, US9 (→ADR-195), US13,
US14, US15c marcadas `[x]` com evidência inline; US9c fechada pelo
veredito já escrito em `floor-reduction.md` §6. **US7 e US8 seguem
`[ ]`** — fora do Scope assinado do pack (US8 tem spec pronta em
`staged-w24/SESSIONEND-NOTE.md`); ambas são cerimônia futura de hook
canônico. Residuais do pack D (3, declarados no sentinel) anotados nos
próprios itens — wave própria com debate, não linha de cerimônia.

### Registro de execução — fechamento do plano (S335, 2026-08-31, wave-179-close)

Ratificação do Owner (AskUserQuestion, fim da S334; verbatim no runbook
`PLAN-179/NEXT-S335-RUNBOOK.md`): «Fechar tudo» — pack US7+US8, AC(a) do
W0 supersedido pela r1-C3, válvula US2b = «Eta advisory + doutrina».
Este registro viaja NO patch assinado (o `done` do frontmatter só é
verdade no land — por isso ambos viajam juntos):

- **US7** — `_ledger_index()` no blob (plan por PATHS do último commit;
  NUNCA `resolve_plan_id` — r1-C6, teste AST escopado) + pointer
  ESTRUTURAL no reinjector (path + short-sha; títulos só no scratchpad,
  doutrina R5 P1-1).
- **US8** — implementado DA spec assinada (`staged-w24/SESSIONEND-NOTE.md`):
  stat-only, âncora chain→none (state_file APOSENTADA no rail r5) com terminal honesto,
  `session_memory_delta_observed` (SPEC v2.60), linha do operador,
  kill-switch 3-estados (rota gate-side RETIRADA no rail r14: inerte
  para a heurística e bypass do ADR-158).
- **US2b-valve** — `_eta_advisory()`: η em permille inteiro (887‰) das
  constantes MEDIDAS; «negar» documentado como limite de substrato
  (guia §6).
- **US1 (veredito vivo)** — supersedido pela r1-C3 (ver checkbox).
- `related_commits` lista os commits históricos do plano; o commit do
  land desta cerimônia completa a lista por definição (não é conhecível
  antes de existir).

### W2 — Ledger de trabalho contínuo (a mudança de doutrina)

Move a escrita de evento terminal para **fronteira de unidade de
execução**. Forma adotada do padrão multissessão da Anthropic
(`research-S309.md §2`), montada sobre o que o repo já tem: ACs de plano
+ git + audit log.

- [x] `[P1][US6][.claude/plans/PLAN-NNN/LEDGER.md]` — *reconciliado na S334: landado em `b07be9b` (pack `staged-w24`, sentinel `W179-W24-approved.md.asc`); o contrato vive no template/validador do `check_ledger_checkpoint.py` (1296L).*
      Contrato do ledger por plano: unidade corrente, ACs com estado
      verificado, último commit, decisões tomadas, bloqueios abertos.
      Uma seção por unidade; identificadores verbatim (paths absolutos,
      SHAs, PLAN-/ADR-ids) — nunca paráfrase.
- [x] `[P1][US6][.claude/hooks/check_ledger_checkpoint.py]` — *reconciliado na S334: landado em `b07be9b`; gatilho por PATHS do commit (teste AST garante ausência de `resolve_plan_id`), ADVISORY, `ledger_checkpoint_skipped` com enum fechado.*
      Hook novo: em fronteira de unidade, verifica que o ledger foi
      atualizado no mesmo commit. **ADVISORY primeiro** — janela
      measure-first, como o `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED` (ADR-191).
      Enforce é cerimônia futura com tabela would-block/TP-FP.
      **[Emenda r1-C6]** O gatilho deriva o escopo dos **PATHS do commit**
      (`.claude/plans/PLAN-NNN/**` ou path listado em AC `[P?][USn][path]`)
      — NUNCA de `resolve_plan_id` (senão W2 re-herda a causa-raiz E2).
      Commit fora de escopo ⇒ evento `ledger_checkpoint_skipped` com razão
      em enum fechado (omissão visível, cobre hotfix/exploratória — OQ-3).
      A tabela TP/FP da janela reporta também a taxa de commits NÃO
      observados (Owner commita com `!` fora do hook — universo censurado
      declarado). **[Emendas r1-A1/A3/B6]** Critério de MORTE: taxa de
      checkpoint omitido > X% ao fim da janela ⇒ o ledger é REMOVIDO, não
      mantido como dívida. Teto de tamanho do LEDGER.md (≤2k tokens,
      seções antigas arquivadas — senão W2 adiciona ao piso F o que W3
      remove). Conteúdo = SÓ identificadores verbatim (paths, SHAs, ids) —
      nunca corpo/excerto de transcript (repo público; check-contamination
      cobre o path novo). "ACs com estado verificado" ganha VERIFICADOR
      nomeado por entrada (comando + exit code), porque entrada errada é
      pior que ausente (o modelo escreve o checkpoint já degradado).
- [x] `[P1][US7][.claude/hooks/check_precompact_continuity.py]`
      — *fechado na wave-179-close (S335): `_ledger_index()` no blob do
      snapshot — plan derivado dos PATHS do último commit (tie-break
      determinístico espelhado de `derive_scope`; NUNCA
      `resolve_plan_id`, emenda r1-C6, com teste AST escopado à função),
      apontando `PLAN-NNN/LEDGER.md` + seções (≤5, clampadas, SÓ no
      scratchpad) + last-commit; o reinjector renderiza o pointer
      ESTRUTURAL (path + short-sha — títulos são CONTEÚDO e não entram
      no instruction stream, doutrina R5 P1-1).*
      *(nota S334, histórica: não tinha entrado no pack `b07be9b`.)*
      PreCompact passa a apontar para o ledger; o snapshot vira o
      **índice** do ledger, não a cópia do estado.
- [x] `[P2][US8][.claude/hooks/SessionEnd.py]`
      — *fechado na wave-179-close (S335): implementado A PARTIR da spec
      assinada (`staged-w24/SESSIONEND-NOTE.md`) — rail stat-only com
      âncora chain→none (state_file APOSENTADA no rail r5), ação
      `session_memory_delta_observed` (SPEC v2.60; emitter tipado +
      allowlist dedicada deny-by-default), linha de ratificação do
      operador (a OMISSÃO vira visível: `memory delta ABSENT`),
      kill-switch 3-estados `CEO_SESSION_MEMORY_DELTA` (a entrada
      gate-side no `harness-noop-allowlist.txt` foi RETIRADA no rail
      r14 — inerte para a heurística constant-emitter e bypass de
      substring do ADR-158); suíte própria em
      `test_session_end_memory_delta.py`.*
      *(nota S334, histórica: spec pronta, aguardava cerimônia.)*
      SessionEnd deixa de só verificar: emite o delta candidato de
      memória (contagem + paths, nunca corpo) para o operador ratificar.
      Escrita de memória continua sendo decisão do modelo/Owner — o hook
      torna a OMISSÃO visível, não escreve por conta própria.
- [x] `[P1][US9][.claude/adr/ADR-193-work-boundary-persistence.md]` — *reconciliado na S334: landado em `b07be9b` como **ADR-195** (renumerado — 193/194 tomados por outros planos), com SPEC v2.59 e as 3 ações de audit.*
      ADR novo: "escrita em fronteira de trabalho". Registra a doutrina,
      o porquê (E1–E3) e a fronteira honesta. **Canônico — cerimônia.**

**AC de saída W2:** matar uma sessão no meio de uma unidade e abrir uma
nova recupera o estado a partir do ledger, sem arqueologia de git.
Ensaio obrigatório em clone, não no repo vivo
([[project-s301-rc3-nogo-cures-overnight]]).
> ✅ **EVIDENCIADO na S334** — ensaio executado em clone descartável, dois
> processos (morte real entre eles), recuperação COMPLETA rc=0 com
> verifier negativo batendo. Registro completo:
> `PLAN-179/w2-recovery-rehearsal-S334.md`.

### W3 — Baixar o piso, melhorar a compactação, fechar as sondas órfãs

> §2.1 estabelece que **a alavanca é `F`, não `T`**. Esta wave é onde o
> piso desce.

- [x] `[P1][US9b][PLAN-179/floor-reduction.md]` — *reconciliado na S325: §3.1 reescrita contra o `F` MEDIDO, com o hit NOMEADO (a coluna dizia "`F` medido hoje (45,3k)" e o "medido" era o erro — era estimativa chars/4 do documento-só). A conclusão inverteu: a faixa 80k-120k não é operável e o piso está em `T ≈ 107k`.*
      Plano de redução de `F` a partir do ranking já produzido por
      `context-budget.py`: `ceo-orchestration/SKILL.md` (735L, ~15.768 tok,
      economia ~15.618 por ativação via `references/*.md` + ponteiro loader)
      e `team.md` (832L, ~11.917 tok). Alvo: `F` de ~50k para ~20k.
      **Dono do trabalho de poda é o PLAN-175** (skills-pruning-discovery) —
      este item DEFINE o alvo e o critério de aceite, não re-executa a poda.
      Reestruturar o core skill exige cerimônia/debate próprios.
- [x] `[P2][US9c][PLAN-179/floor-reduction.md]` — *reconciliado na S334: veredito escrito em `floor-reduction.md` §6 — NÃO-ADOTAR como implementação (o substrato não expõe o controle; DAG sem eviction seria implementar em falso), ADOTAR como doutrina de uso. Exatamente o entregável ADOTAR/NÃO-ADOTAR com razão que o item pede.*
      Avaliar **eviction estruturada** (`research-S309.md §2.4`) como
      alternativa à sumarização: DAG de episódios exploratory/action,
      remoção primeiro do que persiste no ambiente. Registrar como
      ADOTAR / NÃO-ADOTAR com razão — o substrato hoje não expõe esse
      controle, então provavelmente é doutrina de uso, não implementação.
      Ganho colateral relevante: prefixo de cache estável (23% de custo).

- [x] `[P2][US10][templates/compaction.md]` — *fechado na S334 por
      DOUTRINA-DE-USO declarada com razão (rota prevista pelo próprio
      item): consumidor = OPERADOR via `/compact <instruções>` em sessão
      longa prestes a compactar; a rota API `instructions` foi REJEITADA
      porque substitui integralmente o prompt padrão (omissão = perda de
      recall, `research-S309.md §1`); a metade mecânica da continuidade
      não depende deste template (pinned constraints têm canal próprio,
      W1-b). Doutrina registrada NO PRÓPRIO template (cabeçalho "DELIVERY
      CHANNEL — USE DOCTRINE").*
      Ligar o template de 9 seções (PLAN-133 D4) como instrução real de
      compactação, em vez de template que ninguém alimenta. Avaliar as
      duas rotas: `/compact <instruções>` no CLI e o parâmetro
      `instructions` do `compact_20260112` na API (`research-S309.md §1`)
      — atenção: `instructions` **substitui integralmente** o prompt
      padrão, então omissão é perda de recall.
- [x] `[P2][US11][.claude/scripts/context-budget.py]`
      Decidir o destino de D1/D2/D5: consumir ou remover. Sonda órfã que
      permanece é dívida que parece cobertura. Se consumir, o consumidor
      é nomeado aqui; se remover, sai com o teste.
      **FECHADO (reconciliado na S325, contra execução real).**
      `python3 .claude/scripts/context-budget.py --probe-status` sai **0**
      e emite as TRÊS entradas com veredito e consumidor NOMEADO, que é o
      que o item exigia: D1 `keep_exported_policy` (consumidor = um HOST
      LOOP ausente, que é dono do próprio context-management),
      D5 `keep_exported_policy` (o MESMO host loop ausente),
      D2 `remove_pending_test_codeletion` — sem consumidor e **nenhum
      construível aqui** (stdlib-only, no-network), com o escopo de
      remoção enumerado. Cada entrada carrega `consumer`,
      `why_not_removed` e `removal_scope`, logo a declaração é legível por
      máquina e não prosa. Nenhuma edição no script foi necessária.
- [x] `[P3][US12][docs/CONTEXT-CONTINUITY-GUIDE.md]` — *reconciliado na S325: a faixa interpolada 45–55k e a tabela derivada dela foram substituídas pelo `F` MEDIDO (97.292; série n=41 com mediana 98.636 e spread de 51,7%), e o guia agora diz ao adopter que o piso de thrashing é `T ≈ 107k`, acima do mínimo da API.*
      Guia do adopter: o que sobrevive a uma compactação, o que não, e
      qual é o piso de working-set. Sem promessa que o código não cumpre
      ([[feedback-verify-counts-real-path-is-local]]).

### W4 — Governança da superfície de estado durável

Fecha os primitivos ausentes apontados pelo survey de segurança de
memória (`research-S309.md §3`): *write-gate validation* e
*post-deletion verification* não existem em nenhuma arquitetura revisada.

- [x] `[P1][US13][.claude/hooks/_lib/ledger_provenance.py]` — *reconciliado na S334: landado em `b07be9b` (1125L; tags de proveniência por entrada). Residual declarado no sentinel: `admit_entry` sem call-site de produção — wave própria com debate.*
      Tag de proveniência por entrada do ledger: `owner-instruction` |
      `ceo-derived` | `agent-returned` | `external-tool`. Entrada de
      origem externa nunca é relida como instrução.
- [x] `[P2][US14][.claude/hooks/check_ledger_checkpoint.py]` — *reconciliado na S334: landado em `b07be9b`; write-gate fail-CLOSED (`ledger_provenance.py:50`), default `would_reject` sob janela measure-first (`CEO_LEDGER_WRITE_GATE_ENFORCE`). Residual bind-vs-measure declarado no sentinel.*
      Write-gate: entrada de ledger passa pelo scanner de
      harness-mimicry antes de persistir (mesma rota do Step-4 do
      `/ceo-boot`). Hit ⇒ entrada DESCARTADA, nunca redigida.
- [x] `[P2][US15][docs/threat-model.md]` — *retargetado por §8.7; o arquivo citado não existe no disco. Satisfeito por `docs/threat-model.md:2253-2262` (tabela dos seis eixos). Reconciliado na S325.*
      Modelo de ameaça do ledger nos seis eixos do survey Always-On
      (autoridade, escopo, mutabilidade, proveniência, recuperabilidade,
      acionabilidade). Registrar em `THREAT-MODEL-WORKSHEET.md §2`.
- [x] `[P1][US15b][docs/threat-model.md]` — *retargetado por §8.7 (o WORKSHEET citado NÃO existe no disco; o único worksheet presente é o template genérico da skill security-and-auth, que não é o alvo). **LANDADO:** `docs/threat-model.md:2264-2384`, §"Named scenarios" 1 (`T-compaction-eviction`) e 2 (`T-experience-grafting`), cada um com Vector / Evidence / Mitigations / Residual risk / Test, e com a adjudicação do gate A6 que este item pedia — ele verifica a INTEGRIDADE dos bytes aprovados, nunca a VERDADE da claim aprovada, e `_recency_decay` surfaceia PREFERENCIALMENTE a lição grafted. Verificado na S325 por grep independente; escrever entrada nova DUPLICARIA :2266 e :2315.*
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
- [x] `[P2][US15c][.claude/hooks/_lib/ledger_provenance.py]` — *reconciliado na S334: landado em `b07be9b` (`ledger_provenance.py:908+`). Residual declarado: deleção staged do `LEDGER.md` ainda conta como `ledger_updated` (3 saídas mapeadas em `s328-ceremony-D/rail-round-1.md` §P2-1; mexe em enum fechado do SPEC — wave própria).*
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
  gate-boot é re-pago em toda compactação e só cai atacando a superfície
  Gate-1 — execução no PLAN-175; aqui só o alvo. **O número MEDIDO é
  97.292 tokens** (S322, fronteira de compactação real; controle cold-`F`
  97.097; série n=41 com mediana 98.636 e spread de 51,7%) — o `~44.786`
  que esta linha citava era folclore de ordem 44k e está **REFUTADO nos
  dois sentidos** (reconciliado na S325).
- **O ganho de η depende de um plano que não é este.** §2.1 mostra que a
  alavanca é `F`, e `F` desce no PLAN-175. Se a poda não acontecer, W0–W4
  entregam continuidade e governança preservada, mas a eficiência de
  ciclo fica **abaixo** da faixa 40–60% que esta linha estimava: com o `F`
  medido, η é 42% em `T=184k` e cai a 29% em `T=150k` (§2.1 reconciliada).
  Dependência declarada, não escondida — e agora dimensionada.
- **~~A tabela η de §2.1 é estimativa até W0.~~ MEDIDA na S322, reconciliada na S325** — a tabela agora usa o `F` observado (97.292; mediana da série 98.636), não a heurística. O parágrafo abaixo descreve o método ANTIGO e fica como registro histórico. Usava a heurística chars/4 do
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

---

## 8. Emendas do debate round-1 (S312, 2026-08-17 — consensus PROCEED)

> Fonte: `.claude/plans/PLAN-179/debate/round-1/consensus.md` (3× ADJUST,
> 9 consensos C1-C9 + achados single-critic mantidos). As emendas C1-C3 e
> C5-C7 já estão INLINE nas waves acima (marcadores `[Emenda r1-*]`).
> As demais são VINCULANTES para a execução:

- **8.1 (C4) `context_pressure_observed`:** int com unidade no nome (nunca
  float sob HMAC), **edge-triggered** (emite só na transição de bucket —
  histerese, não sampling; responde OQ-4 sem destruir a série), branch
  `_scrub_` dedicada + allowlist própria + par de testes
  not-in-passthrough/registered + bump de SPEC. Sem essas ACs o "enum
  fechado" é alegação.
- **8.2 (C8) Escopo real da cerimônia (§7 corrigido):** o sentinel cobre
  TODOS os paths tocados — `scratchpad_lib.py`,
  `check_precompact_continuity.py`, `check_postcompact_reinject.py`,
  `check_ledger_checkpoint.py` (novo + registro em `settings.json`),
  `ledger_provenance.py`, `audit_emit.py`, bump de `SPEC/**` — não só os
  2 ADRs. Números de ADR alocados NO MOMENTO da escrita (191/192 já
  tomados; nada de reservar 193 no draft). **DOIS ADRs, UMA cerimônia**;
  ordem obrigatória: ADR-153-AMEND-1 primeiro (fecha o registro
  falsificado), o ADR de doutrina depois.
- **8.3 (C9) Claim "secrets-redacted" é hoje FALSA no caminho usado:** o
  snapshot grava bytes e `redact_secrets` só cobre str. Corrigir a redação
  (redigir antes do encode OU gravar str) + `SPEC/v1/audit-log.schema.md`
  §snapshot + docstrings do hook NA MESMA cerimônia de W1.
- **8.4 (B) Write-gate W4 fail-CLOSED:** distinguir "escaneado limpo" de
  "não consegui escanear" — o segundo é HIT (CLAUDE.md §4). Descarte
  VISÍVEL (evento + marcador "entrada rejeitada, família=X" no ledger) e
  ESCOPADO por proveniência: só `agent-returned`/`external-tool` passam
  pelo scanner; `owner-instruction`/`ceo-derived` nunca. FPR do catálogo
  medida em janela advisory antes de enforcement (o catálogo atual
  sobre-dispara em texto legítimo do próprio repo).
- **8.5 (A-U2) ADR de doutrina nasce com matriz de 2+ opções** (exigência
  da skill): ledger-superfície-nova VS ledger como PROJEÇÃO do scratchpad
  VS ledger DERIVADO do audit-log (este último elimina a escrita
  discricionária — a causa do E3). A escolha é da matriz, não do hábito.
  Reversibilidade declarada por wave (W2 é *Embedded* — exige exit
  strategy escrita).
- **8.6 (C-R5/R6, A-M6) W0 endurecida:** a sonda de canal é
  **operator/local-only** (nunca CI), idempotente (execuções contadas para
  não contaminar a medição de US2), e carrega **DOIS canários numa única
  compactação paga** (PostCompact + SessionStart-compact — um experimento,
  três desfechos). A metade de `F` que `context-budget.py` não mede
  (system prompt + tool defs) tem fonte NOMEADA (usage da API em chamada
  real); sem fonte, a AC degrada explicitamente para "estimativa
  declarada".
- **8.7 (B-P2-8) US15/US15b retargetadas para `docs/threat-model.md`**
  (o WORKSHEET citado não existe no disco) + AC de closeout re-rodando
  `check-threat-model-freshness.py` (2 ADRs novos ⇒ flip para stale é
  CERTO sem revisão).
- **8.8 (B-Nice, decisão adiada REGISTRADA):** desacoplar ou não o pinning
  do kill-switch `CEO_COMPACTION_CONTINUITY=0` — decidir em W1-b; se
  permanecer acoplado, o desarme emite evento.
