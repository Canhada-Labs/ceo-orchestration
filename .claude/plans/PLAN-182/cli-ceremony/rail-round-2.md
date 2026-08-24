# Pair-rail — wave-cli, rodada 2 (S326, 2026-08-24 15:30–15:39Z)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra com o
pacote já curado da rodada 1. `RAIL_RC=0`.

**Resumo do revisor (verbatim):** *"The patch introduces a deterministic failure in its new snapshot
test, leaks collection-isolation directories at shutdown, and regresses explicit restore destinations.
It also claims a signed canonical-edit ceremony that is absent from the tree."*

| # | Sev | Achado | Verificação contra o código | Disposição |
|---|---|---|---|---|
| 1 | P1 | Snapshot herdado REJEITADO (dentro de árvore de isolamento) é re-resolvido por `_resolve_live_log_path_snapshot()`, que honra o MESMO `CEO_AUDIT_LOG_DIR` redirecionado ⇒ devolve o path rejeitado. O teste `test_stale_inherited_snapshot_inside_an_isolation_tree_is_ignored` falha deterministicamente. | **CONFIRMADO — e o teste passou aqui por VACUIDADE:** no macOS `mkdtemp` vive em `/var/folders/...` e o resolvedor devolve `/private/var/...` (`.resolve()`), então `assertNotEqual` compara grafias, não paths. No Linux (CI) falharia. Lição já na memória: asserção de path compara `realpath` dos DOIS lados. | **CURADO r3:** rejeitado ⇒ resolver com os anchors (`CEO_AUDIT_LOG_DIR`, `CEO_PROJECT_STATE_DIR`) temporariamente removidos (fallback por HOME); se o candidato ainda não for bem-formado ⇒ `None` (WS-D1 falha para "sem quarentena", como documentado). Teste compara `realpath`. |
| 2 | P1 | O tree revisado não contém `wave-cli-approved.md` nem o `.asc`, mas o PLAN-182 já diz "ENTREGUE na S326 (cerimônia ...)". Edições em `.claude/hooks/**` e `.claude/governance/**` exigem sentinel assinado (AGENTS.md:84-91). | **CONFIRMADO no que é auditável a partir do sombra:** o sentinel-draft e os scripts vivem na ÁRVORE VIVA (não no clone) e a assinatura só nasce no `OWNER-S326-SIGN.sh`; o land (`OWNER-S326-LAND.sh`) verifica G1 (assinatura + rail de signer), G2 (`Patch-sha256`), G3 (`Anchor-SHA == HEAD`), G4 (`touched − scope = ∅`). Mas a frase do plano afirma o RESULTADO antes do ato. | **CURADO r3 (redação):** o bloco passa a dizer "landado pelo `OWNER-S326-LAND.sh` sob `wave-cli-approved.md` (+ `.asc` commitado com o land)" — verdadeiro exatamente no commit em que a frase entra na árvore. Sentinel + `.asc` são commitados ANTES/JUNTO do land por construção (o SIGN exige árvore limpa). |
| 3 | P2 | `atexit` é LIFO: `_resolve_live_log_path_snapshot()` importa `audit_emit`, que registra o drain do spool ANTES do meu `rmtree` ⇒ o rmtree roda primeiro e o drain recria o dir ⇒ vaza um `ceo-collect-isolation-*` por processo. | **CONFIRMADO por medição** (contagem de dirs em `$TMPDIR` antes/depois de um `--collect-only`). Minha premissa ("o drain registra no primeiro emit") estava errada. | **CURADO r3:** criar a árvore e registrar o `rmtree` ANTES de tocar em `audit_emit`; LIFO então roda o drain primeiro e o rmtree por último. Teste: collect-only sob HOME descartável não deixa `ceo-collect-isolation-*` novo. |
| 4 | P2 | `ceo-restore.sh --dest X` (ou `CEO_AUDIT_LOG_DIR`) fora de um projeto, sem `--project-slug`, chama `_resolve_rp --slug` cedo e morre por não achar `.claude/` — embora esses ramos nem usem o slug. | **CONFIRMADO.** | **CURADO r3:** slug resolvido só no ramo que precisa dele; destino explícito é honrado sem descoberta de projeto. |

Nenhum pushback de mérito; o #2 é pushback parcial de FORMA (o material assinado existe fora do que o
sombra mostra), aceito na redação. Rodada 3 sobre o pacote curado.
