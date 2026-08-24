# Pair-rail — wave-cli, rodada 7 (S326, 2026-08-24 16:41–16:5xZ)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra com o
pacote curado das rodadas 1–6 (patch re-finalizado, `Patch-sha256 150c6497…`) e os materiais com o
staging exato (patch T). `RAIL_RC=0`.

**Resumo do revisor (verbatim):** *"The patch mishandles documented exact audit-log overrides in
xdist workers and adds a test that fails under valid custom audit-log configuration."*

| # | Sev | Achado | Verificação | Disposição |
|---|---|---|---|---|
| 1 | P1 | Minha cura da r6 ainda exige extensão `.jsonl` no snapshot herdado; o override documentado `CEO_AUDIT_LOG_PATH` aceita qualquer arquivo (`docs/GOVERNANCE.md:175`, ex. `/srv/audit/current.log`) ⇒ o worker rejeita a verdade herdada e re-resolve o DEFAULT. | **CONFIRMADO** (a doc não restringe o nome). | **CURADO r8:** validade = path ABSOLUTO fora de árvore de isolamento — nada sobre o nome. |
| 2 | P2 | O teste unitário `test_live_snapshot_was_captured_before_any_redirect` assume basename `audit-log.jsonl`; sob um `CEO_AUDIT_LOG_PATH` customizado a captura no import guarda ESSE path e o teste falha com isolamento correto. | **CONFIRMADO.** | **CURADO r8:** o teste afirma o contrato (absoluto, fora de isolamento); o teste do basename customizado passa a usar `current.log`. |

Nenhum achado nos scripts de cerimônia nesta rodada (LAND com staging exato, SIGN pré-P0-novo).
Rodada 8 sobre o pacote curado; rodada 3 dos materiais (árvore viva) sobre o conjunto final a commitar.
