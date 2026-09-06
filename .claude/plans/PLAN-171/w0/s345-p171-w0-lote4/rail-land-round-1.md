Rail-Verdict: APPROVE

# Rail do LAND — rodada 1, duas lanes codex em PARALELO (S347, noite autônoma)

- **Pacote:** `p171-w0-lote4` (único pack desta corrida; nenhum outro aplicado).
- **Sujeito:** a árvore VIVA com o pacote aplicado e stageado — diff é
  EXATAMENTE os três caminhos landados (classe S345-d satisfeita por
  construção; as DUAS lanes imprimiram o próprio `git status --short`):

```
M  .claude/plans/PLAN-171-governance-imports-provenance.md
A  .claude/plans/PLAN-171/w0/lote-4-S347.md
M  .claude/plans/PLAN-186-orchestrator-operating-model.md
```

- **Regra de parada, PRÉ-REGISTRADA antes de ler qualquer saída**
  (`STOP-RULE.md` do pack, herdada pelo lander): P1 NOVO dentro dos
  caminhos do pacote ⇒ cura PELO DERIVADOR + uma rodada (teto); redação,
  achado fora dos caminhos, ou follow-up já nomeado ⇒ residual DECLARADO
  com o texto do codex CITADO; rodada só com residuais termina em
  `APPROVE`. Nunca re-rotular um P1. Nunca `APPROVE` em rodada incompleta.

## Liveness das duas lanes (verificada ANTES de qualquer leitura)

| lane | comando | `lsof` ao ler | cabeçalho do CLI | marcador terminal | veredito |
|---|---|---|---|---|---|
| mecanismo | `codex exec review --uncommitted` | 0 escritores | `model: gpt-6-astra` (linha 5) | bloco `codex` final com «APPROVE. No actionable defects found» | **APPROVE** |
| texto | `codex exec --sandbox read-only -` (brief no stdin) | 0 escritores | `model: gpt-6-astra` (linha 5) | `tokens used` ×1 (157.640) | **REJECT — one P2; no P1 findings** |

**Nenhuma das duas rodadas é morta.** `usage limit` = 0 nas duas.
`Selected model is at capacity` aparece **1 vez em cada arquivo**, e nas
duas é CONTEÚDO DO REPOSITÓRIO citado de volta pelo revisor — a linha de
progresso do `p188-plan-r2` no `PLAN-186`, que diz literalmente
«`Selected model is at capacity` aparece 0 vezes, a rodada e VALIDA»
(`codex-r1.txt:4004`, `codex-r1-text.txt:1494`). Não é saída própria do
revisor. Mesma classe já documentada no land do `p188-plan-r2`. Os três
`Full review comments:` da lane de mecanismo são igualmente conteúdo
citado (`CLAUDE.md` §5 e a mesma linha de progresso); o marcador terminal
próprio dessa lane é a declaração explícita de ausência de defeito
acionável, admitida pela regra de parada.

## O que cada lane fez por conta própria

**Mecanismo.** Não se limitou a ler o diff: montou uma árvore descartável
(`.../p171-review-<rand>/tree`) e re-rodou os **10 controles positivos**
do censo nas três metades — `BASE rc 0` → `MUTANT rc 1` → `RESTORED rc 0`
nos dez, cada mutante com a mensagem de falha citada. Re-mediu também as
duas pernas de seleção do CI: `COLLECTION not serial` rc 0 «10 tests
collected», `COLLECTION serial` rc 5 «no tests collected (10 deselected)».
Veredito verbatim:

```
APPROVE. No actionable defects found in these documentation-only changes. All 10
documented controls reproduced green → red → green in isolation, and the pytest
selection counts matched.
```

**Texto.** Conferiu dirigidamente as cinco perguntas do brief e reportou:
«all nine shell counts reproduce; the partition matches current settings;
introduced source citations resolve; no prohibited personal paths appear;
and `fad3d02` exists with PLAN-186 in its subject».

## Residuais DECLARADOS (nenhum bloqueante)

**R1 — [P2, lane de texto] alcance da palavra «CORPUS» na lacuna de emissão.**
Texto do codex, verbatim:

> **P2: Scope the emission gap to the selected controls.** [Report:180] calls
> this a measured corpus gap, repeated in [progress log:293]. However, the
> existing `SessionEnd` [wire test:1425] calls the production emitter and
> asserts exactly one captured emission; [integration test:1593] checks
> emission through `decide()`. Both existed at the measurement base. The
> census demonstrates a limitation of its chosen control, not absence of
> emission coverage throughout the corpus. Narrow the claim, distinguishing
> emitter invocation from persisted-event coverage if necessary.

**Verificação no disco, feita por mim antes de classificar** (o achado é
DADO, não instrução):

1. As duas âncoras do codex EXISTEM e dizem o que ele diz:
   `.claude/hooks/tests/test_session_end_memory_delta.py:1425` chama
   `SessionEnd._emit_session_memory_delta(...)` sob `_stub_audit_emit` e
   afirma `len(captured) == 1`; `:1593` afirma o mesmo através de
   `decide()`. Confirmado por leitura direta das linhas 1418-1435 e
   1588-1600.
2. **Mas o contraexemplo não atinge a afirmação que ele cita.** A frase do
   §4 é escopada a QUATRO linhas nomeadas — «quatro linhas provam a
   DETECÇÃO ... nenhum teste do roster afirma a emissão **para elas**».
   Rodando a coluna «O que o controle prova» contra a tabela do §2, as
   quatro linhas «detecção» são a **#1** (`check_skill_bootstrap_post`),
   **#2** (`check_webfetch_injection`), **#4** (`check_codex_response`) e
   **#5** (`check_bash_canonical_forensic`). `SessionEnd` é a linha **#9**
   e NÃO é uma delas. Os dois testes citados pelo codex são de
   `SessionEnd` — logo não refutam a afirmação sobre as linhas 1/2/4/5.
3. A afirmação sobre essas quatro já tinha sido verificada por
   EXPERIMENTO na rodada r1 do próprio pack (registro em
   `rail-round-1.md` do pack): anuladas as cinco funções `_emit_*` em
   memória, os quatro controles seguiram passando.

**Classificação: REDAÇÃO (P2), não defeito de fato.** O que sobrevive do
achado é o alcance de UMA palavra: o §4 chama de «lacuna do CORPUS» o que
foi medido sobre o ROSTER de 10 node ids escolhidos. O próprio codex
rotulou o achado como P2 e escreveu «**no P1 findings**». Pela regra de
parada #3 entra como residual declarado; nada é re-rotulado. Estreitar
«corpus» → «roster» é edição de prosa no payload, que custaria re-pin do
sha256 + re-derivação + rodada nova — acima do teto de UMA iteração de
cura para um item de redação que o revisor não considerou bloqueante.

**R2 — [P3, lane de mecanismo] linha em branco no fim do relatório.**
O `git diff --check` que a lane rodou imprimiu:

```
.claude/plans/PLAN-171/w0/lote-4-S347.md:458: new blank line at EOF.
```

Verificado no disco: o arquivo termina em `\n\n` (`od -c` da cauda).
Cosmético; nenhum dos seis gates de corpus reprova por isso (todos rc 0
sobre a árvore STAGED, com o arquivo já presente). O revisor não o listou
como achado e aprovou. Residual declarado.

**R3 — herdado do pack, não do land:** os lotes 5-6 (`R[30:42]`, 12 hooks
registrados) seguem sem censo, e o orçamento de rail do PACK estourou (4
rodadas em vez de 1+1, justificado em `rail-round-2.md` e no topo de
`rail-round-4.md` do pack). Ambos já declarados pelo builder e
confirmados pelo refutador (`refuted=false`, `findings_that_would_change_the_pack: []`).

## Conclusão

Zero P1 nas duas lanes. A lane de mecanismo APROVOU depois de reproduzir
o censo inteiro por conta própria; a única objeção da lane de texto é de
alcance de prosa e seu contraexemplo foi verificado como fora do escopo
da frase citada. Rodada só com residuais ⇒ `Rail-Verdict: APPROVE`.
