# Pair-rail round 1 — PLAN-179 pack W0/W1/W1-b · 2026-08-19

**Veredito: REJECT** (9 achados: 1×P1, 7×P2, 1×P3). Verbatim em `VERDICT.txt`.

## Como foi rodado

- Revisor: Codex CLI 0.147.0, `codex exec review --uncommitted`.
- O pack está commitado, então o diff foi materializado num clone
  (`git clone --local`) com os 31 arquivos aplicados como mudança
  NÃO-COMMITADA, honrando o `PACKMAP.txt`. Diff revisado: 26 arquivos,
  +2339/−205. Os packs `staged-*` ficaram intocados no clone — apagá-los
  gerava 36k deleções e afogava a revisão em ruído (primeira tentativa).
- Drift de substrato encontrado no caminho: no 0.147.0 o `--uncommitted`
  **não aceita mais prompt posicional** (`error: the argument '--uncommitted'
  cannot be used with '[PROMPT]'`). A memória do repo registra
  `codex exec review --uncommitted` na 0.144.6 com prompt — mudou.

## Por que este round existe

O `PLAN-179:509` exige pair-rail em W1/W2/W4, e eu não o tinha rodado: o pack
inteiro fora escrito, integrado e testado por agentes Claude. O hook de Stop
avisou (`RISKY DIFF ... get a cross-model review`), e o Owner mandou fazer o
certo antes de landar. **A auto-verificação tinha passado**: simulação de land
8/8, suíte completa 7088/0, teste de integração com dentes. Os 9 achados
abaixo sobreviveram a tudo isso — é a razão de o rail existir.

## Os achados, por classe

| # | sev | classe | essência |
|---|---|---|---|
| 1 | P1 | **buraco de adopter** | `upgrade.sh` nunca adiciona o hook novo: instalação NOVA recebe (template curado), UPGRADE não. Mesma classe que a suíte pegou uma camada acima. |
| 2 | P2 | estado global | histerese de pressão é por PROJETO, não por sessão: duas sessões se suprimem/re-armam mutuamente e a série fica inatribuível. |
| 3 | P2 | **instrumento sem chamador** | `gc_orphan_session_stores()` não tem chamador de produção — arquivos `.sqlite`/WAL/SHM acumulam sem limite, e o ADR já afirmava que o GC shipava. |
| 4 | P2 | contrato violado | `event_source` não-hashável levanta `TypeError` antes do fail-open — quebra o contrato "emit_generic nunca levanta". |
| 5 | P2 | gate do próprio repo | 11 violações `env-write` + 1 `bare-testcase` no teste novo: ele reprova o `check-test-env-hygiene.py`. |
| 6 | P2 | doc mente | `CONTEXT-CONTINUITY-GUIDE.md` diz "staged, não instalado, não rodando" e descreve um guard que HALTA a compactação — o oposto do que ship. |
| 7 | P2 | SPEC stale | a linha v2.56 ainda declara `constraint_count` ausente e o produtor chamando um símbolo inexistente — coisas que este mesmo patch curou. |
| 8 | P3 | claim proibida | descrever o kill-switch como decisão de "throughput" implica ganho de velocidade; o repo não faz claim de velocidade em lugar nenhum. |

Três deles (1, 3, 4) são a **classe dominante do repo**: instrumento que parece
ligado e não pode disparar. Dois (6, 7) são a classe irmã: contrato publicado
que envelheceu no mesmo commit que o tornou falso.

## Estado

Curas despachadas em `wf_422cca37-f1d`. Round 2 do rail roda depois delas.
