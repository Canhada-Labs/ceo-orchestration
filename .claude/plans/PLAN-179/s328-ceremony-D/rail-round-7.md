# Pair-rail — PACOTE D, rodada 7 (pós-abort do land V4a, S329)

**Instrumento:** `codex exec review --commit 41fe0c9` (codex-cli 0.147.0),
sobre o commit que cura o flake de ORDEM em
`staged-w24/.claude/hooks/tests/test_ledger_provenance.py` + o MANIFEST
re-montado. Artefato bruto: `<scratchpad>/rail-testfix.txt` (14.040 bytes,
`rc=0`); última mensagem em `<scratchpad>/rail-testfix-last.txt`.

**Achados: 0.** Sem bloco `Full review comments:` (rodada limpa — o codex
desta versão não imprime `VERDICT:`).

Rail-Verdict: APPROVE

> Sumário do revisor, verbatim: "The live lookup mirrors the production
> call-time import and eliminates the stale-module patch target. The manifest
> hash matches the modified test, and the assembled regression scenario
> passes all 96 tests."

## Por que houve uma rodada 7

O 1º land real de D (26/08, 12:52 → 13:19) abortou em **V4a** com 4 falhas em
`TestDiscardIsVisible` — os mesmos testes verdes no `--dry-run` 30 min antes
e no G4 (arquivo sozinho). Não é carga: é **ordem de execução** sob `-n auto`.

Mecanismo, reproduzido de forma determinística em clone com o pack aplicado:

| Controle | Antes da cura | Depois da cura |
|---|---|---|
| poluidor sintético (`sys.modules.pop` + `delattr` + re-import de `_lib.audit_emit`) + a classe, mesmo processo | **4 failed**, 5 passed | 9 passed |
| poluidor REAL da suíte (`test_check_agent_spawn.py::TestPLAN078Wave1ModelRoutingAdvisory`, re-cria o módulo no `tearDown`) + a classe / o arquivo | **4 failed**, 30 passed | 96 passed |
| arquivo sozinho (controle negativo) | 8/8 · 70/70 | 70/70 |
| os 8 testes do pack no clone | — | 316 passed |

O teste fazia `mock.patch.object(audit_emit, …)` no objeto de módulo importado
no topo do arquivo; `ledger_provenance._emit_rejection` resolve
`from _lib import audit_emit` **na chamada**. Vinte e três arquivos da suíte
fazem `sys.modules.pop`/rebind de `_lib.audit_emit` — quando um cai no mesmo
worker antes, o nome do teste fica STALE e o patch nunca chega ao gate
(`len(calls) == 0`; canal `typed` em vez de `unavailable`: exatamente as 4
asserções que caíram). Hazard já documentado em
`test_tool_lifecycle_observe.py`; mesma cura — helper `_live_audit_emit()`
com a MESMA semântica `IMPORT_FROM` do gate, patch NELE (9 sítios).

Censo nos outros 7 testes do pack: zero sítios do padrão (o único
`patch.object(audit_emit, …)` em `test_audit_emit_api_contract.py` patcha e
chama o MESMO objeto). `BASELINE.sha256` inalterado (o teste é destino NOVO);
`MANIFEST.sha256` com 1 hash novo. O sentinel é re-assinado pelo Owner no
próximo `OWNER-S328-MORNING.sh --from D` (o SIGN regenera do draft).

**Residual fora do pack (encaminhar, não bloqueia):** a classe "patch em
objeto de módulo stale de `_lib.audit_emit`" tem 22 arquivos na suíte VIVA
com `patch.object(audit_emit…)` e 5 com string-target
`mock.patch("_lib.audit_emit.…")`; cada um só é frágil se o código sob teste
resolver o emissor na chamada. Censo mecânico é trabalho de wave própria
(mesma disciplina do M4: enumerar, classificar, provar com controle).
